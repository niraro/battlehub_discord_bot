import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from unix_timestamp import get_discord_timestamp
from embed import create_embed, create_embed_with_footer
from battlehub_bot_ui import EventSelectView, MonthSelectView
import bot_db
from command_helpers import _build_availability_breakdown, _set_availability, looks_like_shifted_args, DATE_REGEX, TIME_REGEX
from battlehub_commands import BUILTIN_COMMANDS
import os

# Load the token from the .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Database Initialisation
bot_db.init_db()

# Intents tell discord what info the bot is allowed to receive
intents = discord.Intents.default()
# Needed to read message text
intents.message_content = True
intents.members = True
intents.presences = True 

#Adding prefix to trigger bot (e.g. !news)
bot = commands.Bot(command_prefix="!", intents=intents)

# Tells user that bot is online
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} - bot is online!")

########################## Bot Commands ##############################

# Uses !post for command -- Bot takes input message, posts it, and removes original command
@bot.command()  
#@commands.has_any_role("Announcer", "Admin")
async def post(ctx, *, message):
    embed = create_embed_with_footer(title = "📢   Announcement", description = message)
    await ctx.send(embed = embed, content = "")
    await ctx.message.delete()
    
# Uses !timeconvert for command -- Converts given date into Discord-formatted unix timestamp
@bot.command()  
#@commands.has_any_role("Announcer", "Admin")
async def timeconvert(ctx, date_str, time_str, tz_name):
    try:
        unix_time, discord_format = get_discord_timestamp(f"{date_str} {time_str}", tz_name)
        embed = create_embed(
            title = "🕐 Timestamp Converter",
            description = f"<t:{unix_time}:F> converted to Discord format: `{discord_format}`\n" 
        )
        await ctx.send(embed = embed)
    except Exception as e:
        error_embed = create_embed(
            title = "⚠️ Conversion Failed",
            description = f"Could not convert. Make sure the date format is `<DD-MM-YYYY>` `<HH:MM>` `<Timezone>`\n\nError: {e}",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = error_embed)

# Uses !addevent for command -- Adds new event to the list, which can be then viewed by anyone
@bot.command()
#@commands.has_any_role("Announcer", "Admin")
async def addevent(ctx, name, date_str, time_str, *, tz_name):
    if not DATE_REGEX.match(date_str) and looks_like_shifted_args(time_str, tz_name):
        embed = create_embed(
            title = "⚠️ Missing Quotes?",
            description = "Please ensure the event name is wrapped in double quotes if its name contains more than one word, following the `<\"Event Name\">` `<DD-MM-YYY>` `<HH:MM>` `<Timezone>` format",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        return
    
    unix_time, discord_time = get_discord_timestamp(f"{date_str} {time_str}", tz_name)    
    bot_db.add_event(name, unix_time, str(ctx.author), str(ctx.guild.id))
    embed = create_embed(
        title = "✅ Event Added", 
        description = f"**{name}** on {discord_time} has been added as an upcoming event"
    )
    await ctx.send(embed = embed)
    await ctx.message.delete()

# Uses !remove_event for command -- Removes the event from the list (deletes it from the database)
@bot.command()
#@commands.has_any_role("Announcer", "Admin")
async def remove_event(ctx, name):
    event = bot_db.get_event_from_list(name, str(ctx.guild.id))
    if not event:
        embed = create_embed(title = "⚠️ Event Not Found", description = f"Please make sure the name of the event is correct")
    else:
        bot_db.remove_event(event[1], str(ctx.guild.id))
        embed = create_embed(
            title = "🗑️ Event Removed", 
            description = f"Event **{event[1]}** has been removed from the list", 
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed)
    await ctx.message.delete()

# Uses !showevents -- Shows all upcoming events (name, date, and time)
@bot.command()
async def showevents(ctx):
    events = bot_db.get_all_events(str(ctx.guild.id))
    if not events:
        embed = create_embed(title = "📅 Upcoming Events", description = f"No events scheduled yet")
    else:
        lines = [f"#{position} {name} - <t:{ts}:F>" for position, (eid, name, ts, added_by) in enumerate(events, start = 1)]
        embed = create_embed(title = "📅 Upcoming Events", description = "\n".join(lines))
    await ctx.send(embed = embed)

# Uses command !addavail -- User adds availability to their chosen event
@bot.command()
async def addavail(ctx, event_name, role, status, *, note = None):
    await _set_availability(ctx, event_name, role, status, note)

# Uses command !adjustavail -- User adjusts availability of chosen event
@bot.command()
async def adjustavail(ctx, event_name, role, status, *, note = None):
    await _set_availability(ctx, event_name, role, status, note)

# Uses command !removeavail -- User removes availability for chosen event
@bot.command()
async def removeavail(ctx, event_name, *, role = None):
    event = bot_db.get_event_from_list(event_name, str(ctx.guild.id))
    if not event:
        embed = create_embed(
            title = "⚠️ Event Not Found",
            description = "Make sure name of event is spelt correctly (check typos, etc)",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        return
    if role is None:
        deleted = bot_db.remove_all_availability_for_event(event[0], str(ctx.author.id), str(ctx.guild.id))
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
    else:        
        role_obj = discord.utils.find(lambda r: r.name.lower() == role.lower(), ctx.guild.roles)
        role_display = role_obj.name if role_obj else role
        deleted = bot_db.remove_availability(event[0], str(ctx.author.id), role_display, str(ctx.guild.id))
        if deleted:
            embed = create_embed(
            title = "🗑️ Availability Removed",
            description = f"Removed availability as `{role_display}` for **{event[1]}**"
            )
        else:
            embed = create_embed(
                title = "⚠️ No Entry Found",
                description = f"{role_display} not found for {event[1]}",
                colour = discord.Colour.red()
            )
    await ctx.send(embed = embed)
    await ctx.message.delete()

# Uses command !checkavail -- Check user availability for a specific role, or availability of all users on a specific date
@bot.command()
async def checkavail(ctx, *, target: str):
    member = None
    if target.startswith("<@") and target.endswith(">"):
        user_id = target.strip("<@!>")
        member = ctx.guild.get_member(int(user_id))
    else:
        member = discord.utils.find(lambda m: m.name.lower() == target.lower() or m.display_name.lower() == target.lower(), ctx.guild.members)
    if not member:
        embed = create_embed(
            title = "⚠️ User Not Found",
            description = f"Could not find {target}",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        return

    entries = bot_db.get_availability_by_user(str(member.id), str(ctx.guild.id))
    if not entries:
        embed = create_embed(
            title = f"📋 {member.display_name}'s Availability",
            description = "No current availability"
        )
    else:
        lines = [f"{name} ({role}) - {status}" + (f" _({note})_" if note else "") for name, ts, role, status, note in entries]
        embed = create_embed(
            title = f"📋 {member.display_name}'s Availability",
            description = "\n".join(lines)
        )
    await ctx.send(embed = embed)
 
# Uses command !checkevent -- Displays availability of users for specific roles on a given event
@bot.command()
async def checkevent(ctx, event_name):
    event = bot_db.get_event_from_list(event_name, str(ctx.guild.id))
    if not event:
        embed = create_embed(
            title = "⚠️ Event Not Found",
            description = f"No event with the name **{event_name}**",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        return
    embed = await _build_availability_breakdown(ctx, event, str(ctx.guild.id))
    await ctx.send(embed = embed)

# Uses command !checkdate -- Allows user to see availabilities of others for an event on a given date    
@bot.command()
async def checkdate(ctx, date_str, tz_name):
    try:
        day_start = datetime.strptime(date_str, "%d-%m-%Y").replace(tzinfo = ZoneInfo(tz_name))
    except ValueError:
        embed = create_embed(
            title = "⚠️ Invalid Date",
            description = "Make sure the date you entered follows `DD-MM-YYYY`",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        return
    except Exception as e:
        embed = create_embed(
            title = "⚠️ Invalid Timezone",
            description = f"Could not find timezone. Check for any typos\n\nError: {e}",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        return
    
    day_end = day_start + timedelta(days = 1) - timedelta(seconds = 1)
    start_ts = int(day_start.timestamp())
    end_ts = int(day_end.timestamp())
    events = bot_db.get_events_by_date_range(start_ts, end_ts, str(ctx.guild.id))
    
    if not events:
        embed = create_embed(
            title = "📅 No Events Found",
            description = f"No events scheduled on `{date_str}`"
        )
        await ctx.send(embed = embed)
        return
    
    if len(events) == 1:
        embed = await _build_availability_breakdown(ctx, events[0], str(ctx.guild.id))
        await ctx.send(embed = embed)
        return
    
    # Multiple events on a given date, using dropdown
    view = EventSelectView(events, str(ctx.guild.id))
    embed = create_embed(
        title = "📅 Multiple Events Found",
        description = "Select the event below to view who's available"
    )
    await ctx.send(embed = embed, view = view)

# Uses command !checkcalendar -- Allows user to check events for chosen month    
@bot.command()
async def checkcalendar(ctx, tz_name):
    view = MonthSelectView(tz_name, str(ctx.guild.id))
    embed = create_embed(
        title = "📅 Calendar",
        description = "Select a month to view its events"
    )
    await ctx.send(embed = embed, view = view)

# Uses command !addcommand -- Allows user to add a command to the list !bhcommands
@bot.command()
#@commands.has_any_role("Announcer", "Admin")
async def addcommand (ctx, name, *, note):
    bot_db.add_command(name, note, str(ctx.guild.id))
    embed = create_embed(
        title = "✅ Command Added",
        description = f"Command `!{name}` has been added to the list"
    )
    await ctx.send(embed = embed)
    await ctx.message.delete()
    
# Uses command !removecommand -- Allows user to remove a command from the list !bhcommands
@bot.command()
#@commands.has_any_role("Announcer", "Admin")
async def removecommand(ctx, *, name):
    deleted = bot_db.remove_command(name, str(ctx.guild.id))
    if deleted:
        embed = create_embed(
            title = "🗑️ Command Removed",
            description = f"Command `!{name}` has been removed from the list"
        )
    else:
        embed = create_embed(
            title = "⚠️ Command Not Found",
            description = f"Command `!{name}` does not exist in the list",
            colour = discord.Colour.red() 
        )
    await ctx.send(embed = embed)
    await ctx.message.delete()

# Uses command !bhcommands -- Allows user to view the bot's command list
@bot.command()
#@commands.has_any_role("Announcer", "Admin")
async def bhcommands(ctx):
    lines = [f"`!{name}` -> {note}\n" for name, note in BUILTIN_COMMANDS]
    
    custom_command = bot_db.get_all_commands(str(ctx.guild.id))
    if not custom_command:
        embed = create_embed(
            title = "📖 Command List",
            description = "No commands currently in the list"
        )
    else:
<<<<<<< HEAD
        lines = [f"**`!{name}`** -> {note}" for name, note in custom_command]
=======
        lines = [f"`!{name}` -> {note}" for name, note in custom_command]
>>>>>>> 74cea8e6f4004ed64fe124655743d7a441ee1110
    embed = create_embed(
        title = "📖 Command List",
        description = "\n".join(lines)
    )
    await ctx.send(embed = embed)
        
############################# Error Checks for Commands #########################################

@post.error
# Checks for missing roles for !post
async def post_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        #await ctx.send("No permission to send", delete_after = 5)
        await ctx.message.delete()
        
@timeconvert.error
async def timeconvert_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure the format is `<\"Event Name\"> <DD-MM-YYYY> <HH:MM> <Timezone>`",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        
@addevent.error
async def addevent_error(ctx, error):
    original = getattr(error, "original", error)
    if isinstance(error, commands.MissingRequiredArgument):
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
            description = f"Make sure the date and time format follows `<DD-MM-YYYY>` `<HH:MM>`",
            colour = discord.Colour.red()
        )
    elif isinstance(original, (ZoneInfoNotFoundError, IsADirectoryError)):
        embed = create_embed(
            title = "⚠️ Invalid Timezone",
            description = "Make sure the timezone entered follows the IANA Timezone name (E.g. \"American/Edmonton\")",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: {original}",
            colour = discord.Colour.red()
        )       
    await ctx.send(embed = embed)
    
@checkdate.error  
async def checkdate_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure the format is `<DD-MM-YYYY> <Timezone>`",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        
@checkcalendar.error
async def checkcalendar_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure to include `<Timezone>`",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        
        
bot.run(TOKEN)
