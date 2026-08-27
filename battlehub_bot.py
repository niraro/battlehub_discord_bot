import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from unix_timestamp import get_discord_timestamp
from embed import create_embed, create_embed_with_footer
from battlehub_bot_ui import EventSelectView, MonthSelectView
import bot_db as bot_db
import command_helpers as helper
from battlehub_commands import BUILTIN_COMMANDS
import os

# Load the token from the .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
dev_guild_id_raw = int(os.getenv("DEV_GUILD_ID"))
DEV_GUILD_ID = int(dev_guild_id_raw) if dev_guild_id_raw else None

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
    if DEV_GUILD_ID:
        guild = discord.Object(id = DEV_GUILD_ID)
        bot.tree.copy_global_to(guild = guild)
        await bot.tree.sync(guild = guild)
        print(f"Guild-synced commands to {DEV_GUILD_ID}")
    else:
        print("Dev_GUILD_ID not set -- Skipping guild-scoped sync")

@bot.command()
@commands.is_owner()
async def sync(ctx):
    synced = await bot.tree.sync()
    await ctx.send(f"Synced {len(synced)} command(s) globally. May take up to 1h to sync everywhere")

# Logs which command gets used, by which user, and in which channel
@bot.before_invoke
async def before_command_use(ctx):
    await helper.log_command_usage(ctx, LOG_CHANNEL_ID, create_embed)

########################## Bot Commands ##############################

# Uses !post for command -- Bot takes input message, posts it, and removes original command
@bot.hybrid_command(description = "Announcement/news posts")  
#@commands.has_any_role("Announcer", "Admin")
async def post(ctx, *, message: str):
    embed = create_embed_with_footer(title = "📢 Announcement", description = message)
    await ctx.send(embed = embed, content = "")
    await ctx.message.delete() if ctx.interaction is None else None
    
# Uses !timeconvert for command -- Converts given date and time to Discord-formatted unix timestamp
@bot.hybrid_command(description = "Converts date and time to Discord-formatted unix timestamp")  
#@commands.has_any_role("Announcer", "Admin")
async def timeconvert(ctx, date: str, time: str, timezone: str):
    try:
        unix_time, discord_format = get_discord_timestamp(f"{date} {time}", timezone)
        embed = create_embed(
            title = "🕐 Timestamp Converter",
            description = f"<t:{unix_time}:F> converted to Discord format: `{discord_format}`\n" 
        )
        await ctx.send(embed = embed, ephemeral = True)
    except Exception as e:
        error_embed = create_embed(
            title = "⚠️ Conversion Failed",
            description = f"Could not convert. Make sure the date format is `<DD-MM-YYYY>` `<HH:MM>` `<Timezone>`\n\nError: {e}",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = error_embed, ephemeral = True)

# Uses !addevent for command -- Adds new event to the list, which can be then viewed by anyone
@bot.hybrid_command(description = "Adds a new event to the list of upcoming events")
#@commands.has_any_role("Announcer", "Admin")
async def addevent(ctx, name: str, date: str, time: str, *, timezone: str):
    if not helper.DATE_REGEX.match(date) and helper.looks_like_shifted_args(time, timezone):
        embed = create_embed(
            title = "⚠️ Missing Quotes?",
            description = "Please ensure the event name is wrapped in double quotes if its name contains more than one word, following the `<\"Event Name\">` `<DD-MM-YYY>` `<HH:MM>` `<Timezone>` format",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    unix_time, discord_time = get_discord_timestamp(f"{date} {time}", timezone)    
    bot_db.add_event(name, unix_time, str(ctx.author), str(ctx.guild.id))
    embed = create_embed(
        title = "✅ Event Added", 
        description = f"**{name}** on {discord_time} has been added as an upcoming event"
    )
    await ctx.send(embed = embed)
    await ctx.message.delete() if ctx.interaction is None else None

# Uses !remove_event for command -- Removes the event from the list (deletes it from the database)
@bot.hybrid_command(description = "Removes an event from the list of upcoming events")
#@commands.has_any_role("Announcer", "Admin")
async def remove_event(ctx, name: str):
    event = bot_db.get_event_from_list(name, str(ctx.guild.id))
    if not event:
        embed = create_embed(
            title = "⚠️ Event Not Found", 
            description = "Please make sure the name of the event is correct",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    bot_db.remove_event(event[1], str(ctx.guild.id))
    embed = create_embed(
        title = "🗑️ Event Removed", 
        description = f"Event **{event[1]}** has been removed from the list", 
        colour = discord.Colour.red()
    )
    await ctx.send(embed = embed)
    if ctx.interaction is None:
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
@bot.hybrid_command(description = "Add availability for a role for an event")
async def addavail(ctx, event_name: str, role: str, status: str, *, note: str = None):
    await helper._set_availability(ctx, event_name, role, status, note)

# Uses command !adjustavail -- User adjusts availability of chosen event
@bot.hybrid_command(description = "Adjust availability of a role for an event")
async def adjustavail(ctx, event_name: str, role: str, status: str, *, note: str = None):
    await helper._set_availability(ctx, event_name, role, status, note)

# Uses command !removeavail -- User removes availability for chosen event
@bot.hybrid_command(description = "Remove avaialability for one or more roles for an event")
async def removeavail(ctx, event_name: str, *, role: str = None):
    event = bot_db.get_event_from_list(event_name, str(ctx.guild.id))
    if not event:
        embed = create_embed(
            title = "⚠️ Event Not Found",
            description = "Make sure name of event is spelt correctly (check typos, etc)",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
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
            await ctx.send(embed = embed, ephemeral = True)
            return
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
                description = f"`{role_display}` not found for **{event[1]}**",
                colour = discord.Colour.red()
            )
            await ctx.send(embed = embed, ephemeral = True)
            return
    await ctx.send(embed = embed)
    if ctx.interaction is None:
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
    embed = await helper._build_availability_breakdown(ctx, event, str(ctx.guild.id))
    await ctx.send(embed = embed)

# Uses command !checkdate -- Allows user to see availabilities of others for an event on a given date    
@bot.hybrid_command(description = "Show availabilities of a chosen date for upcoming event(s)")
async def checkdate(ctx, date: str, timezone: str):
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
    events = bot_db.get_events_by_date_range(start_ts, end_ts, str(ctx.guild.id))
    
    if not events:
        embed = create_embed(
            title = "📅 No Events Found",
            description = f"No events scheduled on `{date}`"
        )
        await ctx.send(embed = embed)
        return
    
    if len(events) == 1:
        embed = await helper._build_availability_breakdown(ctx, events[0], str(ctx.guild.id))
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
@bot.hybrid_command(description = "Check event(s) for the chosen month")
async def checkcalendar(ctx, timezone: str):
    view = MonthSelectView(timezone, str(ctx.guild.id))
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
        lines = [f"**`!{name}`** -> {note}" for name, note in custom_command]
    embed = create_embed(
        title = "📖 Command List",
        description = "\n".join(lines)
    )
    await ctx.send(embed = embed)
        
############################# Error Checks for Commands #########################################

@post.error
async def post_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        #await ctx.send("No permission to send", delete_after = 5)
        await ctx.message.delete()
        
@timeconvert.error
async def timeconvert_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure the format is `<DD-MM-YYYY> <HH:MM> <Timezone>`",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        
@addevent.error
async def addevent_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
        
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
    
@remove_event.error
async def remove_event_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
                title = "⚠️ Missing Info",
                description = "Make sure to enter the name of the event you want to remove",
                colour = discord.Colour.red()
            )
        await ctx.send(embed = embed, ephemeral = True)
    
@checkdate.error  
async def checkdate_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    if isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure the format is `<DD-MM-YYYY> <Timezone>`",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        
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
        return
    elif isinstance(original, (ZoneInfoNotFoundError, IsADirectoryError)):
        embed = create_embed(
            title = "⚠️ Invalid Timezone",
            description = "Make sure the timezone entered follows the IANA Timezone name (E.g. \"America/Edmonton\")",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)
        
        
bot.run(TOKEN)
