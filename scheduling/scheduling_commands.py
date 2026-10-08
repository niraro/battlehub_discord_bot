import discord
import time
from discord.ext import commands
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from common.bot_launch import bot
from common.error_handlers import handle_error
from common.embed import create_embed
from database.scheduling_db import get_schedule_by_event, get_availability_by_user, delete_schedule_by_event, set_broadcast_settings
from database.events_db import  get_events_by_date_range, get_all_events
from events.event_helpers import get_event_from_list
from scheduling.scheduling_config import SETTINGS_KEYS
from scheduling.scheduling_helpers import _build_availability_breakdown, load_settings, get_zone, parse_time, format_settings, describe_entry
from scheduling.scheduling_views import ScheduleModal, OpenScheduleModalView
from events.event_views import EventSelectView

    
async def _schedule_message_exists(guild, channel_id, message_id):
    channel = guild.get_channel_or_thread(int(channel_id))
    if channel is None:
        return False
    try:
        await channel.fetch_message(int(message_id))
        return True
    except discord.NotFound:
        return False
    except discord.HTTPException:
        return True
    
    
@bot.hybrid_command(description = "Post a staff sign-up message for an event")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def buildschedule(ctx, *, event: str):
    guild_id = str(ctx.guild.id)
    event_row = get_event_from_list(event, guild_id)
    if not event_row:
        embed = create_embed(
            title = "⚠️ Event Not Found",
            description = "Make sure the name of event is spelt correctly (check typos, etc)",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return

    existing = get_schedule_by_event(event_row[0], guild_id)
    if existing:
        channel_id, message_id = existing
        if await _schedule_message_exists(ctx.guild, channel_id, message_id):
            embed = create_embed(
                title = "⚠️ Schedule Already Exists",
                description = f"**{event_row[1]}** already has a sign-up post at: https://discord.com/channels/{guild_id}/{channel_id}/{message_id}",
                colour = discord.Colour.red()
            )
            await ctx.send(embed = embed, ephemeral = True)
            return
        delete_schedule_by_event(event_row[0], guild_id)
        
    settings = load_settings(guild_id)
    if ctx.interaction is not None:
        await ctx.interaction.response.send_modal(ScheduleModal(event_row, settings))
    else:
        embed = create_embed(
            title = f"📝 Schedule - {event_row[1]}",
            description = "Click the button below to enter the Call Time, Broadcast Start, Sign-up Deadline and Timezone"
        )
        await ctx.send(embed = embed, view = OpenScheduleModalView(ctx.author.id, event_row, settings))
        
@buildschedule.autocomplete("event")
async def schedule_event_autocomplete(interaction: discord.Interaction, current: str):
    cutoff = int(time.time()) - 86400
    events = [e for e in get_all_events(str(interaction.guild_id)) if e[2] >= cutoff and current.lower() in e[1].lower()]
    return [
        discord.app_commands.Choice(
            name = f"{name} ({datetime.fromtimestamp(ts, ZoneInfo('UTC')):%d-%m-%Y})"[:100],
            value = name[:100]
        )
        for eid, name, ts, added_by in events[:25]
    ]

@buildschedule.error
async def schedule_error(ctx, error):
    await handle_error(ctx, error, "Make sure to include the name of the event")
    
    
@bot.hybrid_command(description = "Adjust 'default' settings for future event schedule builds")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def schedulesettings(ctx, call_time: str = None, broadcast_start: str = None, signup_hours: int = None, timezone: str = None, channel: discord.TextChannel = None, ping_role: discord.Role = None, calendar_url: str = None):
    guild_id = str(ctx.guild.id)
    settings = load_settings(guild_id)

    if all(v is None for v in (call_time, broadcast_start, signup_hours, timezone, channel, ping_role, calendar_url)):
        embed = create_embed(
            title = "⚙️ Schedule Settings",
            description = format_settings(settings),
        )
        await ctx.send(embed = embed, ephemeral = True)
        return

    try:
        if call_time is not None:
            settings["call_time"] = parse_time(call_time)
        if broadcast_start is not None:
            settings["broadcast_start"] = parse_time(broadcast_start)
    except ValueError:
        embed = create_embed(
            title = "⚠️ Invalid Time",
            description = "Make sure the time follows `<HH:MM>` (E.g. `09:00`)",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    if timezone is not None:
        if get_zone(timezone) is None:
            embed = create_embed(
                title = "⚠️ Invalid Timezone",
                description = "Make sure the timezone entered follows the IANA Timezone name (E.g. \"Ameica/Toronto\", \"Europe/Berlin\")",
                colour = discord.Colour.red()
            )
            await ctx.send(embed = embed, ephemeral = True)
            return
        settings["timezone"] = timezone.strip()
    
    if signup_hours is not None:
        if not 0 <= signup_hours <= 720:
            embed = create_embed(
                title = "⚠️ Invalid Deadline",
                description = "The sign-up deadline must be between 0 and 720 hours before the call time",
                colour = discord.Colour.red()
            )
            await ctx.send(embed = embed, ephemeral = True)
            return
        settings["sign_up_deadline"] = signup_hours
        
    if calendar_url is not None:
        if not calendar_url.startswith(("http://", "https://")):
            embed = create_embed(
                title = "⚠️ Invalid Link",
                description = "The calendar link must start with `http://` or `https://`",
                colour = discord.Colour.red()
            )
            await ctx.send(embed = embed, ephemeral = True)
            return
        settings["calendar_url"] = calendar_url.strip()
        
    if channel is not None:
        settings["schedule_channel_id"] = str(channel.id)
    if ping_role is not None:
        settings["ping_role_id"] = str(ping_role.id)
        
    set_broadcast_settings(guild_id, *(settings[k] for k in SETTINGS_KEYS))
    embed = create_embed(
        title = "✅ Schedule Settings Saved", description = format_settings(settings)
    )
    await ctx.send(embed = embed, ephemeral = True)

@schedulesettings.error
async def schedulesettings_error(ctx, error):
    await handle_error(ctx, error, "Check the options you entered and try again")
    

# Uses command !checkavail -- Check user availability for a specific role, or availability of all users on a specific date
@bot.hybrid_command(description = "Check availability(ies) of a specified user")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def checkavail(ctx, *, member: discord.Member):
    entries = get_availability_by_user(str(member.id), str(ctx.guild.id))
    if not entries:
        embed = create_embed(
            title = f"📋 {member.display_name}'s Availability",
            description = "No current availability"
        )
    else:
        lines = [describe_entry(name, role, status, note) for name, ts, role, status, note in entries]
        embed = create_embed(
            title = f"📋 {member.display_name}'s Availability",
            description = "\n".join(lines)
        )
    await ctx.send(embed = embed, ephemeral = True)
    
@checkavail.error
async def checkavail_error(ctx, error):
    await handle_error(ctx, error, "Don't forget to add the user's name, or ID")
    
    
# Uses command !eventavail -- Displays availability of users for specific roles on a given event
@bot.hybrid_command(description = "Shows staff availability for specified event")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def eventavail(ctx, *, event: str):
    event_row = get_event_from_list(event, str(ctx.guild.id))
    if not event_row:
        embed = create_embed(
            title = "⚠️ Event Not Found",
            description = f"No event with the name **{event}**",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    embed = await _build_availability_breakdown(ctx, event_row, str(ctx.guild.id))
    await ctx.send(embed = embed)
    
@eventavail.error
async def eventavail_error(ctx, error):
    await handle_error(ctx, error, "Make sure to include the `Event Name`")
    
    
# Uses command !dateavail -- Allows user to see availabilities of others for an event on a given date    
@bot.hybrid_command(description = "Show availabilities of a chosen date for upcoming event(s)")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def dateavail(ctx, date: str, timezone: str):
    tz = get_zone(timezone)
    if tz is None:
       embed = create_embed(
           title = "⚠️ Invalid Timezone",
           description = "Make sure the timezone entered follows the IANA Timezone name (E.g. \"America/Toronto\", \"Europe/Berlin\")",
           colour = discord.Colour.red()
       )
       await ctx.send(embed = embed, ephemeral = True)
       return
    try:
        day_start = datetime.strptime(date, "%d-%m-%Y").replace(tzinfo = tz)
    except ValueError:
        embed = create_embed(
            title = "⚠️ Invalid Date",
            description = "Make sure the date entered follow the `DD-MM-YYYY` format",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    day_end = day_start + timedelta(days = 1) - timedelta(seconds = 1)
    events = get_events_by_date_range(int(day_start.timestamp()), int(day_end.timestamp()), str(ctx.guild.id))
    
    if not events:
        emebed = create_embed(
            title = "📅 No Events Found",
            description = f"No events schedule on `{date}`",
        )
        await ctx.send(embed = embed)
        return
    if len(events) == 1:
        embed = await _build_availability_breakdown(ctx, events[0], str(ctx.guild.id))
        await ctx.send(embed = embed)
        return
    
    # If multiple events found, give dropdown selection
    view = EventSelectView(events, str(ctx.guild.id))
    embed = create_embed(
        title = "📅 Multiple Events Found",
        description = "Select the event below to view who's available"
    )
    await ctx.send(embed = embed, view = view)
    
@dateavail.error
async def dateavail_error(ctx, error):
    await handle_error(ctx, error, "Make sure the format is `<DD-MM-YYYY> <Timezone>`")
    