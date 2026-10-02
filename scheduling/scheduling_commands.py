import discord
from discord.ext import commands
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from common.bot_launch import bot
from common.embed import create_embed
from database.scheduling_db import remove_availability, get_availability_by_user, remove_all_availability_for_event
from database.events_db import get_event_from_list, get_events_by_date_range
from scheduling.scheduling_helpers import _set_availability, _build_availability_breakdown
from events.event_views import EventSelectView


# Uses command !addavail -- User adds availability to their chosen event
@bot.hybrid_command(description = "Add availability for a role for an event")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def addavail(ctx, event: str, role: str, status: str, *, note: str = None):
    await _set_availability(ctx, event, role, status, note)
    
@addavail.error
async def addavail_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return    
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
                title = "⚠️ Missing Info",
                description = "Make sure to include the `Event Name`, you `Role`, and your `Status` for the role to add yourself",
                colour = discord.Colour.red()
            )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )   
    await ctx.send(embed = embed, ephemeral = True)


# Uses command !adjustavail -- User adjusts availability of chosen event
@bot.hybrid_command(description = "Adjust availability of a role for an event")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def adjustavail(ctx, event: str, role: str, status: str, *, note: str = None):
    await _set_availability(ctx, event, role, status, note)
    
@adjustavail.error
async def adjustavail_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return    
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
                title = "⚠️ Missing Info",
                description = "Make sure to include the `Event Name`, you `Role`, and your `Status` for the role to make adjustments",
                colour = discord.Colour.red()
            )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )   
    await ctx.send(embed = embed, ephemeral = True)    
    

# Uses command !removeavail -- User removes availability for chosen event
@bot.hybrid_command(description = "Remove avaialability for one or more roles for an event")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def removeavail(ctx, event: str, *, role: str = None):
    event = get_event_from_list(event, str(ctx.guild.id))
    if not event:
        embed = create_embed(
            title = "⚠️ Event Not Found",
            description = "Make sure name of event is spelt correctly (check typos, etc)",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    if role is None:
        deleted = remove_all_availability_for_event(event[0], str(ctx.author.id), str(ctx.guild.id))
        if deleted:
            embed = create_embed(
                title = "🗑️ Availability Removed",
                description = f"Removed availability for **{event[1]}**"
            )
        else:
            embed = create_embed(
                title = "⚠️ No Availability Found",
                description = f"No availability has been logged for **{event[1]}**",
                colour = discord.Colour.red()
             )
            await ctx.send(embed = embed, ephemeral = True)
            return
    else:        
        role_obj = discord.utils.find(lambda r: r.name.lower() == role.lower(), ctx.guild.roles)
        role_display = role_obj.name if role_obj else role
        deleted = remove_availability(event[0], str(ctx.author.id), role_display, str(ctx.guild.id))
        if deleted:
            embed = create_embed(
            title = "🗑️ Availability Removed",
            description = f"Removed availability as `{role_display}` for **{event[1]}**"
            )
        else:
            embed = create_embed(
                title = "⚠️ No Entry Found",
                description = f"`{role_display}` not found for **{event[1]}**",
                colour = discord.Colour.red()
            )
            await ctx.send(embed = embed, ephemeral = True)
            return
    await ctx.send(embed = embed, ephemeral = True)
    if ctx.interaction is None:
        await ctx.message.delete()
        
@removeavail.error
async def removeavail_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return    
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure to include the `Event Name`to remove your availability for specified event, or the `Event Name` and `Role` to remove your availability for a specific role",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )   
    await ctx.send(embed = embed, ephemeral = True)       
        

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
        lines = [f"**{name}** ({role}) - {status}" + (f" _({note})_" if note else "") for name, ts, role, status, note in entries]
        embed = create_embed(
            title = f"📋 {member.display_name}'s Availability",
            description = "\n".join(lines)
        )
    await ctx.send(embed = embed, ephemeral = True)
    
@checkavail.error
async def checkavail_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return   
    elif isinstance(original, commands.MemberNotFound):
        embed = create_embed(
            title = "⚠️ User Not Found",
            description = f"Couldn't find `{original.argument}`. Try adding an '@' in front of their name, or use their user ID",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Don't forget to add the user's name, or ID",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)    
 
 
# Uses command !eventavail -- Displays availability of users for specific roles on a given event
@bot.hybrid_command(description = "Shows staff availability for specified event")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def eventavail(ctx, event: str):
    event = get_event_from_list(event, str(ctx.guild.id))
    if not event:
        embed = create_embed(
            title = "⚠️ Event Not Found",
            description = f"No event with the name **{event}**",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    embed = await _build_availability_breakdown(ctx, event, str(ctx.guild.id))
    await ctx.send(embed = embed, ephemeral = True)

@eventavail.error
async def eventavail_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return    
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
                title = "⚠️ Missing Info",
                description = "Make sure include the `Event Name`",
                colour = discord.Colour.red()
            )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )   
    await ctx.send(embed = embed, ephemeral = True) 


# Uses command !dateavail -- Allows user to see availabilities of others for an event on a given date    
@bot.hybrid_command(description = "Show availabilities of a chosen date for upcoming event(s)")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def dateavail(ctx, date: str, timezone: str):
    try:
        day_start = datetime.strptime(date, "%d-%m-%Y").replace(tzinfo = ZoneInfo(timezone))
    except ValueError:
        embed = create_embed(
            title = "⚠️ Invalid Date",
            description = "Make sure the date you entered follows `DD-MM-YYYY`",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    except Exception as e:
        embed = create_embed(
            title = "⚠️ Invalid Timezone",
            description = f"Could not find timezone. Check for any typos\n\nError: {e}",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    day_end = day_start + timedelta(days = 1) - timedelta(seconds = 1)
    start_ts = int(day_start.timestamp())
    end_ts = int(day_end.timestamp())
    events = get_events_by_date_range(start_ts, end_ts, str(ctx.guild.id))
    
    if not events:
        embed = create_embed(
            title = "📅 No Events Found",
            description = f"No events scheduled on `{date}`"
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    if len(events) == 1:
        embed = await _build_availability_breakdown(ctx, events[0], str(ctx.guild.id))
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    # Multiple events on a given date, using dropdown
    view = EventSelectView(events, str(ctx.guild.id))
    embed = create_embed(
        title = "📅 Multiple Events Found",
        description = "Select the event below to view who's available"
    )
    await ctx.send(embed = embed, view = view, ephemeral = True)

@dateavail.error  
async def checkdate_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return      
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure the format is `<DD-MM-YYYY> <Timezone>`",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)