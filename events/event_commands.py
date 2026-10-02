import discord
from discord.ext import commands
from zoneinfo import ZoneInfoNotFoundError
from common.bot_launch import bot
from common.unix_timestamp import get_discord_timestamp
from common.embed import create_embed
from database.events_db import add_event, event_remove, get_event_from_list, get_all_events
from events.event_helpers import looks_like_shifted_args, DATE_REGEX
from events.event_views import MonthSelectView

# Uses !addevent for command -- Adds new event to the list, which can be then viewed by anyone
@bot.hybrid_command(description = "Adds a new event to the list of upcoming events")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def addevent(ctx, name: str, date: str, time: str, *, timezone: str):
    if not DATE_REGEX.match(date) and looks_like_shifted_args(time, timezone):
        embed = create_embed(
            title = "⚠️ Missing Quotes?",
            description = "Please ensure the event name is wrapped in double quotes if its name contains more than one word, following the `<\"Event Name\">` `<DD-MM-YYY>` `<HH:MM>` `<Timezone>` format",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    unix_time, discord_time = get_discord_timestamp(f"{date} {time}", timezone)    
    add_event(name, unix_time, str(ctx.author), str(ctx.guild.id))
    embed = create_embed(
        title = "✅ Event Added", 
        description = f"**{name}** on {discord_time} has been added as an upcoming event"
    )
    await ctx.send(embed = embed, ephemeral = True)

@addevent.error
async def addevent_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
        
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure to include the name, date, time, and timezone of the event",
            colour = discord.Colour.red()
        )
    elif isinstance(error, commands.ExpectedClosingQuoteError):
        embed = create_embed(
            title = "⚠️ Missing Double Quote",
            description = "Make sure to add double quotes around the event name (E.g. \"Event Name\")",
            colour = discord.Colour.red()
        )
    elif isinstance(original, ValueError):
        embed = create_embed(
            title = "⚠️ Invalid Date/Time",
            description = f"Make sure the date and time format follows `<DD-MM-YYYY> <HH:MM>`",
            colour = discord.Colour.red()
        )
    elif isinstance(original, (ZoneInfoNotFoundError, IsADirectoryError)):
        embed = create_embed(
            title = "⚠️ Invalid Timezone",
            description = "Make sure the timezone entered follows the IANA Timezone name (E.g. \"America/Edmonton\")",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: {type(original).__name__}: {original}",
            colour = discord.Colour.red()
        )       
    await ctx.send(embed = embed, ephemeral = True)


# Uses !remove_event for command -- Removes the event from the list (deletes it from the database)
@bot.hybrid_command(description = "Removes an event from the list of upcoming events")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def remove_event(ctx, name: str):
    event = get_event_from_list(name, str(ctx.guild.id))
    if not event:
        embed = create_embed(
            title = "⚠️ Event Not Found", 
            description = "Please make sure the name of the event is correct",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    event_remove(event[1], str(ctx.guild.id))
    embed = create_embed(
        title = "🗑️ Event Removed", 
        description = f"Event **{event[1]}** has been removed from the list", 
        colour = discord.Colour.red()
    )
    await ctx.send(embed = embed, ephemeral = True)

@remove_event.error
async def remove_event_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return    
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
                title = "⚠️ Missing Info",
                description = "Make sure to enter the name of the event you want to remove",
                colour = discord.Colour.red()
            ) 
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)


# Uses !showevents -- Shows all upcoming events (name, date, and time)
@bot.hybrid_command(description = "Shows all upcoming events")
async def showevents(ctx):
    events = get_all_events(str(ctx.guild.id))
    if not events:
        embed = create_embed(title = "📅 Upcoming Events", description = f"No events scheduled yet")
    else:
        lines = [f"#{position} {name} - <t:{ts}:F>" for position, (eid, name, ts, added_by) in enumerate(events, start = 1)]
        embed = create_embed(title = "📅 Upcoming Events", description = "\n".join(lines))
    await ctx.send(embed = embed, ephemeral = True)

@showevents.error
async def showevents_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original

    embed = create_embed(
        title = "⚠️ Something Went Wrong",
        description = f"Unexpected Error: `{type(original).__name__}:` {original}",
         colour = discord.Colour.red()
    )
    await ctx.send(embed = embed, ephemeral = True)

    
# Uses command !checkcalendar -- Allows user to check events for chosen month    
@bot.hybrid_command(description = "Check event(s) for the chosen month")
async def checkcalendar(ctx, timezone: str):
    view = MonthSelectView(timezone, str(ctx.guild.id))
    embed = create_embed(
        title = "📅 Calendar",
        description = "Select a month to view its events"
    )
    await ctx.send(embed = embed, view = view, ephemeral = True)

@checkcalendar.error
async def checkcalendar_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
        
    if isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Timezone",
            description = "Make sure to include an IANA Timezone",
            colour = discord.Colour.red()
        )
    elif isinstance(original, (ZoneInfoNotFoundError, IsADirectoryError)):
        embed = create_embed(
            title = "⚠️ Invalid Timezone",
            description = "Make sure the timezone entered follows the IANA Timezone name (E.g. \"America/Edmonton\")",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)   