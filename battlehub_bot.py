import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import battlehub_bot_ui as bh_ui
from unix_timestamp import get_discord_timestamp
from embed import create_embed, create_embed_with_footer
import bot_db as bot_db
import command_helpers as helper
from battlehub_commands import BUILTIN_COMMANDS
import log_docs as logs
import reaction_roles as react

# Load the token from the .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
#LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
dev_guild_id_raw = os.getenv("DEV_GUILD_ID")
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
bot = commands.Bot(command_prefix = "!", intents = intents)

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
        
    if not check_stale_tickets.is_running():
        check_stale_tickets.start()

# !sync -- Syncs commands from dev testing to VPS version
@bot.command()
@commands.is_owner()
async def sync(ctx):
    synced = await bot.tree.sync()
    await ctx.send(f"Synced {len(synced)} command(s) globally. May take up to 1h to sync globally")

# !clear_guild_sync -- Clears duplicate commands  
@bot.command()
@commands.is_owner()
async def clear_guild_sync(ctx):
    bot.tree.clear_commands(guild = ctx.guild)
    await bot.tree.sync(guild = ctx.guild)
    await ctx.send("Guild-specific command duplicates cleared")

# Logs which command gets used, by which user, and in which channel
@bot.before_invoke
async def before_command_use(ctx):
    await logs.log_command_usage(ctx, create_embed)

# Listens to messages and flags as necessary
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # DM ticket listener
    if isinstance(message.channel, discord.DMChannel):
        await handle_ticket_dm(bot, message)
        return
    
    # Honeypot listener
    triggered = await helper.check_honeypot(bot, message)
    if triggered:
        return
    
    # Message Flag listener
    await logs.scan_message_for_flags(bot, message)
    
    # Allows commands with prefix to work
    await bot.process_commands(message)

############################### Ticket Event(s) & Commands #######################################

async def handle_ticket_dm(message):
    user = message.author
    mutual_servers = [g for g in bot.guilds if g.get_member(user.id) is not None]
    
    if not mutual_servers:
        await user.send("Cannot open ticket as we have no mutual server(s)")
        return
    if len(mutual_servers) == 1:
        await helper.route_ticket_message(bot, message, mutual_servers[0])
        return
    
    # If multiple servers detected
    view = bh_ui.ServerSelectView(mutual_servers, message)
    await user.send("Which server is this ticket for?", view = view)
    
@bot.hybrid_command(description = "Reply to the user in the ticket thread")
#@commands.has_any_role("Announcer", "Admin")
async def reply(ctx, *, message: str):
    if not isinstance(ctx.channel, discord.Thread):
        embed = create_embed(
            title = "⚠️ Wrong Channel",
            description = "This command only works in a ticket thread",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    ticket = bot_db.get_ticket_by_thread(str(ctx.channel.id))
    if ticket is None:
        embed = create_embed(
            title = "⚠️ Invalid Ticket",
            description = "This thread is not linked to an open ticket",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    ticket_id, discord_id, status = ticket
    if status != "open":
        embed = create_embed(
            title = "⚠️ Ticket Closed",
            description = "This ticket is already closed",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    user = bot.get_user(int(discord_id))
    if user is None:
        embed = create_embed(
            title = "⚠️ User Not Found",
            description = "Could not find user of this ticket",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    dm_embed = create_embed(
        title = "💬 Staff",
        description = message
    )
    try:
        await user.send(embed = dm_embed)
    except discord.Forbidden:
        embed = create_embed(
            title = "⚠️ Message Not Delivered",
            description = "Could not send reply. User either has DMs disabled or has blocked the bot",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    bot_db.update_ticket_activity(str(ctx.channel.id), int(time.time()))
    confirm_embed = create_embed(
        title = "✅ Reply Sent",
        description = message
    )
    await ctx.send(embed = confirm_embed)
    
@bot.hybrid_command(description = "Closes ticket")
#@commands.has_any_role("Announcer", "Admin")
async def closeticket(ctx):
    if not isinstance(ctx.channel, discord.Thread):
        embed = create_embed(
            title = "⚠️ Wrong Channel",
            description = "This command only works in a ticket thread",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return     

    ticket = bot_db.get_ticket_by_thread(str(ctx.channel.id))
    if ticket is None:
        embed = create_embed(
            title = "⚠️ Invalid Ticket",
            description = "This thread is not linked to an open ticket",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    ticket_id, discord_id, status = ticket
    if status != "open":
        embed = create_embed(
            title = "⚠️ Ticket Closed",
            description = "This ticket is already closed",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    bot_db.close_ticket(ticket_id)
    await helper.update_ticket_board(bot, str(ctx.guild.id))
    user = bot.get_user(int(discord_id))
    if user is not None:
        close_embed = create_embed(
            title = "🔒 Ticket Closed",
            description = "Ticket has been closed by staff. DM again to open a new ticket",
            colour = discord.Colour.red()
        )
        try:
            await user.send(embed = close_embed)
        except discord.Forbidden:
            pass # Closes ticket even if user has closed DMs
    confirm_embed = create_embed(
            title = "🔒 Ticket Closed",
            description = "Ticket has been closed and archived",
            colour = discord.Colour.red()
    )
    await ctx.send(embed = confirm_embed)
    await ctx.channel.edit(archived = True, locked = True)
    
TICKET_INACTIVITY_SECONDS = 120 # Temporarily 2 minute for testing

@tasks.loop(minutes = 1) # Temporarily set to check every minute
async def check_stale_tickets():
    cutoff = int(time.time()) - TICKET_INACTIVITY_SECONDS
    stale_tickets = bot_db.get_stale_tickets(cutoff)
    
    for ticket_id, guild_id, discord_id, thread_id, ticket_number in stale_tickets:
        bot_db.close_ticket(ticket_id)
        await helper.update_ticket_board(bot, guild_id)
        thread = bot.get_channel(int(thread_id))
        if thread is not None:
            embed = create_embed(
                title = "🔒 Ticket Auto-Closed",
                description = f"Ticket #{ticket_number} has automatically closed after 72 hours of inactivity"
            )
            await thread.send(embed = embed)
            try:
                await thread.edit(archived = True, locked = True)
            except discord.HTTPException:
                pass
            
        user = bot.get_user(int(discord_id))
        if user is not None:
            close_embed = create_embed(
                title = "🔒 Ticket Closed",
                description = f"Your current ticket: Ticket #{ticket_number} was automatically closed due to inactivity. DM again to open a new ticket"
            )
            try:
                await user.send(embed = close_embed)
            except discord.Forbidden:
                pass

@check_stale_tickets.before_loop
async def before_check_stale_tickets():
    await bot.wait_until_ready()
        
############################### General Commands #####################################

# Uses !post for command -- Bot takes input message, posts it, and removes original command
@bot.hybrid_command(description = "Announcement/news posts")  
#@commands.has_any_role("Announcer", "Admin")
async def post(ctx, *, message: str):
    embed = create_embed_with_footer(
        title = "📢 Announcement", 
        description = message
    )
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
@bot.hybrid_command(description = "Shows all upcoming events")
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
async def addavail(ctx, event: str, role: str, status: str, *, note: str = None):
    await helper._set_availability(ctx, event, role, status, note)

# Uses command !adjustavail -- User adjusts availability of chosen event
@bot.hybrid_command(description = "Adjust availability of a role for an event")
async def adjustavail(ctx, event: str, role: str, status: str, *, note: str = None):
    await helper._set_availability(ctx, event, role, status, note)

# Uses command !removeavail -- User removes availability for chosen event
@bot.hybrid_command(description = "Remove avaialability for one or more roles for an event")
async def removeavail(ctx, event: str, *, role: str = None):
    event = bot_db.get_event_from_list(event, str(ctx.guild.id))
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
@bot.hybrid_command(description = "Check availability(ies) of a specified user")
async def checkavail(ctx, *, member: discord.Member):
    entries = bot_db.get_availability_by_user(str(member.id), str(ctx.guild.id))
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
    await ctx.send(embed = embed)
 
# Uses command !checkevent -- Displays availability of users for specific roles on a given event
@bot.hybrid_command(description = "Shows availability for specified event")
async def checkevent(ctx, event):
    event = bot_db.get_event_from_list(event, str(ctx.guild.id))
    if not event:
        embed = create_embed(
            title = "⚠️ Event Not Found",
            description = f"No event with the name **{event}**",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
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
    view = bh_ui.EventSelectView(events, str(ctx.guild.id))
    embed = create_embed(
        title = "📅 Multiple Events Found",
        description = "Select the event below to view who's available"
    )
    await ctx.send(embed = embed, view = view)

# Uses command !checkcalendar -- Allows user to check events for chosen month    
@bot.hybrid_command(description = "Check event(s) for the chosen month")
async def checkcalendar(ctx, timezone: str):
    view = bh_ui.MonthSelectView(timezone, str(ctx.guild.id))
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
    lines = [f"`{name}` -> {note}\n" for name, note in BUILTIN_COMMANDS]
    
    custom_command = bot_db.get_all_commands(str(ctx.guild.id))
    if not custom_command:
        embed = create_embed(
            title = "📖 Command List",
            description = "No commands currently in the list"
        )
    else:
        lines = [f"**`{name}`** -> {note}" for name, note in custom_command]
    embed = create_embed(
        title = "📖 Command List",
        description = "\n".join(lines)
    )
    await ctx.send(embed = embed)

@bot.hybrid_command(description = "Set a custom welcome message for new players in a chosen channel")
#@commands.has_any_role("Admin", "Mod")
async def setwelcomemessage(ctx, channel: discord.TextChannel, *, message: str):
    bot_db.set_welcome(str(ctx.guild.id), str(channel.id), message)
    embed = create_embed(
        title = "✅ Welcome Message Set",
        description = f"New members will now be greeted in {channel.mention}"
    )
    await ctx.send(embed = embed, ephemeral = True)

################################ Moderation Tools ##################################
    
@bot.hybrid_command(description = "Sets channel for support tickets")
#@commands.has_any_role("Announcer", "Admin")
async def setticketschannel(ctx, channel: discord.TextChannel):
    bot_db.set_tickets_channel(str(ctx.guild.id), str(channel.id))
    embed = create_embed(
        title = "✅ Tickets Channel Set",
        description = f"New tickets will now appear in {channel.mention}"
    )
    await ctx.send(embed = embed)
    
@bot.hybrid_command(description = "Set channel for chosen log(s)")
#@commands.has_any_role("Announcer", "Admin")
@app_commands.choices(log = logs.LOG_TYPES)
async def setlogs(ctx, log: str, channel: discord.TextChannel):
    valid_types = [c.value for c in logs.LOG_TYPES]
    if log not in valid_types:
        embed = create_embed(
            title = "⚠️ Invalid Log Type",
            description = f"Log does not exist. Make sure to chose one of: \n{', '.join(valid_types)}",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
    bot_db.set_log_channel(str(ctx.guild.id), log, str(channel.id))
    embed = create_embed(
        title = "✅ Log Channel Set ",
        description = f"**{log}** logs will now be documented in {channel.mention}"       
    )
    await ctx.send(embed = embed)

@bot.hybrid_command(description = "View current log channel configuration")
#@commands.has_any_role("Announcer", "Admin")
async def viewlogs(ctx):
    settings = bot_db.get_all_log_settings(str(ctx.guild.id))
    if not settings:
        embed = create_embed(
            title = "📋 Log Settings",
            description = "No log channels configured yet"
        )
    else:
        lines = [f"**{log}:** <#{channel_id}>" for log, channel_id in settings]
        embed = create_embed(
            title = "📋 Log Settings",
            description = "\n".join(lines)
        )
    await ctx.send(embed = embed)

@bot.event
async def on_member_join(member):
    await logs.member_join(bot, member)
    await logs.send_welcome(bot, member)

@bot.event
async def on_member_remove(member):
    await logs.member_leave(bot, member)
    
@bot.event
async def on_member_ban(guild, user):
    await logs.member_ban(bot, guild, user)

@bot.event
async def on_member_update(before, after):
    await logs.role_update(bot, before, after)

@bot.hybrid_command(description = "Add flagged terms to flag list")
#@commands.has_any_role("Announcer", "Admin")
async def addflaggedterm(ctx, *, term: str):
    bot_db.add_flagged_term(str(ctx.guild.id), term, str(ctx.author))
    embed = create_embed(
        title = "✅ Term Added",
        description = f"`{term}` will now be flagged"
    )
    await ctx.send(embed = embed, ephemeral = True)
    
@bot.hybrid_command(description = "Remove flagged terms from flag list")
#@commands.has_any_role("Announcer", "Admin")
async def removeflaggedterm(ctx, *, term: str):
    deleted = bot_db.remove_flagged_term(str(ctx.guild.id), term)
    if deleted:
        embed = create_embed(
            title = "🗑️ Term Removed",
            description = f"`{term}` will no longer be flagged"
        )
    else:
        embed = create_embed(
            title = "⚠️ Term Not Found",
            description = f"`{term}` cannot be found in the flagged terms list",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)
    
@bot.hybrid_command(description = "View all flagged terms in the list")
#@commands.has_any_role("Announcer", "Admin")
async def viewftlist(ctx):
    terms = bot_db.get_flagged_terms(str(ctx.guild.id))
    if not terms:
        embed = create_embed(
            title = "📋 Flagged Terms",
            description = "No terms currently in the list"
        )
    else:
        embed = create_embed(
            title = "📋 Flagged Terms",
            description = "\n".join(f"`{t}`" for t in terms)
        )
    await ctx.send(embed = embed, ephemeral = True)

@bot.event
async def on_message_edit(before, after):
    if after.author.bot:
        return
    if before.content == after.content:
        return
    await logs.scan_message_for_flags(bot, after)
    
@bot.hybrid_command(description = "Add a domain (e.g. google.com) to the link flagging list")
#@commands.has_any_role("Announcer", "Admin")
async def addflaggeddomain(ctx, *, domain: str):
    bot_db.add_flagged_domain(str(ctx.guild.id), domain, str(ctx.author))
    embed = create_embed(
        title = "✅ Domain Added",
        description = f"`{domain}` will now be flagged"
    )
    await ctx.send(embed = embed, ephemeral = True)
    
@bot.hybrid_command(description = "Remove a domain (e.g. google.com) from the link flagging list")
#@commands.has_any_role("Announcer", "Admin")
async def removeflaggeddomain(ctx, *, domain: str):
    deleted = bot_db.remove_flagged_domain(str(ctx.guild.id), domain)
    if deleted:
        embed = create_embed(
            title = "🗑️ Domain Removed",
            description = f"`{domain}` will no longer get flagged"
        )
    else:
        embed = create_embed(
            title = "⚠️ Domain Not Found",
            description = f"`{domain}` could not be found in the list",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)
    
@bot.hybrid_command(description = "View list of all flagged domains for this server")
#@commands.has_any_role("Announcer", "Admin")
async def viewflaggeddomains(ctx):
    domains = bot_db.get_flagged_domains(str(ctx.guild.id))
    if not domains:
        embed = create_embed(
            title = "📋 Flagged Domains",
            description = "No domains currently flagged"
        )
    else:
        embed = create_embed(
            title = "📋 Flagged Domains",
            description = "\n".join(f"`{d}`" for d in domains)
        )
    await ctx.send(embed = embed, ephemeral = True)
    
@bot.tree.context_menu(name = "Blacklist Image(s)")
@app_commands.checks.has_any_role("Announcer", "Admin")
async def blacklist_image(interaction: discord.Interaction, message: discord.Message):
    if not message.attachments:
        await interaction.response.send_message("This message has no attachments", ephemeral = True)
        return
    
    added = 0
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image/"):
            image_bytes = await attachment.read()
            phash = helper.compute_phash(image_bytes)
            bot_db.add_scam_hash(str(interaction.guild.id), phash, str(interaction.user))
            added += 1
    await interaction.response.send_message(f"Blacklisted {added} image(s) from this message", ephemeral = True)

@bot.hybrid_command(description = "Assign a honeypot channel")
#@commands.has_any_role("Announcer", "Admin")
async def addhoneypot(ctx, channel: discord.TextChannel):
    bot_db.add_honeypot_channel(str(ctx.guild.id), str(channel.id))
    embed = create_embed(
        title = "✅ Honeypot Set",
        description = f"{channel.mention} is now a honeypot channel"
    )
    await ctx.send(embed = embed, ephemeral = True)

@bot.hybrid_command(description = "Remove a honeypot channel")
#@commands.has_any_role("Announcer", "Admin")
async def removehoneypot(ctx, channel: discord.TextChannel):
    deleted = bot_db.remove_honeypot_channel(str(ctx.guild.id), str(channel.id))
    if deleted:
        embed = create_embed(
            title = "🗑️ Honeypot channel removed",
            description = f"{channel.mention} is no longer a honeypot channel"
        )
    else:
        embed = create_embed(
            title = "⚠️ Honeypot Channel Not Found",
            description = f"{channel.mention} is not registered as a honeypot channel",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)
        
@bot.hybrid_command(description = "Lists all honeypot channels")
#@commands.has_any_role("Announcer", "Admin")
async def honeypotlist(ctx,):
    channel_ids = bot_db.list_honeypot_channels(str(ctx.guild.id))
    if not channel_ids:
        embed = create_embed(
            title = "📋 Honeypot Channel(s)",
            description = "No honeypot channels available yet"
        )
    else:
        embed = create_embed(
            title = "📋 Honeypot Channel(s)",
            description = "\n".join(f"<#{c}>" for c in channel_ids)
        )
    await ctx.send(embed = embed, ephemeral = True)
      
############################# REACTION Commands ##############################

@bot.hybrid_command(description = "Assign/remove roles based on message reaction(s)")
#@commands.has_any_role("Announcer", "Admin")
async def addreactionrole(ctx, message_link: str, emoji: str, add_role: discord.Role = None, remove_role: discord.Role = None, toggle: bool = False):
    if add_role is None and remove_role is None:
        embed = create_embed(
            title = "⚠️ Missing Role",
            description = "Specify an add_role, a remove_role, or both",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return

    parsed = react.parse_message_link(message_link)
    if parsed is None:
        embed = create_embed(
            title = "⚠️ Invalid Link",
            description = "Couldn't parse the message link",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    guild_id, channel_id, message_id = parsed
    
    channel = ctx.guild.get_channel(int(channel_id))
    if channel is None:
        embed = create_embed(
            title = "⚠️ Channel Not Found",
            description = "Couldn't find channel",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    try:
        message = await channel.fetch_message(int(message_id))
        await message.add_reaction(emoji)
    except discord.NotFound:
        embed = create_embed(
            title = "⚠️ Message Not Found",
            description = "Couldn't find message",
            colour = discord.Colour.red()
        ) 
        await ctx.send(embed = embed, ephemeral = True)
        return
    except discord.HTTPException:
        embed = create_embed(
            title = "⚠️ Invalid Emoji",
            description = "Emoji either not in server, or could not be found",
            colour = discord.Colour.red()
        ) 
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    bot_db.add_reaction_role_mapping(
        str(ctx.guild.id), message_id, emoji,
        str(add_role.id) if add_role else None,
        str(remove_role.id) if remove_role else None,
        toggle
    )         
    
    embed = create_embed(
        title = "✅ Reaction Role Added",
        description = f"Reacting with {emoji} will now " +
            (f"add {add_role.mention} " if add_role else "") +
            (f"and " if add_role and remove_role else "") +
            (f"remove {remove_role.mention} " if remove_role else "") +
            f"({'toggleable' if toggle else 'one-time'})"
    )
    await ctx.send(embed = embed, ephemeral = True)
    
@bot.hybrid_command(description = "Remove a role reaction mapping")
#@commands.has_any_role("Announcer", "Admin")
async def removereactrole(ctx, message_link: str, emoji: str):
    parsed = react.parse_message_link(message_link)
    if parsed is None:
        embed = create_embed(
            title = "⚠️ Invalid Link",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    _, _, message_id = parsed
    deleted = bot_db.remove_reaction_role_mapping(str(ctx.guild.id), message_id, emoji)
    if deleted:
        await ctx.send(embed = create_embed(title = "🗑️ Role Map Removed"), ephemeral = True)
    else:
        await ctx.send(embed = create_embed(title = "⚠️ Role Map Not Found", colour = discord.Colour.red()), ephemeral = True)

@bot.hybrid_command(description = "List role reaction mappings for a message")
#@commands.has_any_role("Announcer", "Admin")
async def listreactroles(ctx, message_link: str):
    parsed = react.parse_message_link(message_link)
    if parsed is None:
        embed = create_embed(
            title = "⚠️ Invalid Link",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    _, _, message_id = parsed
    rows = bot_db.list_reaction_role_mappings(str(ctx.guild.id), message_id)
    if not rows:
        embed = create_embed(
            title = "📋 Reaction Roles",
            description = "No role-to-message mapping(s) configured yet"
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    lines = []
    for emoji, add_id, remove_id, toggle in rows:
        add_text = f"<@&{add_id}>" if add_id else "-"
        remove_text = f"<@&{remove_id}>" if remove_id else "-"
        lines.append(f"{emoji} -> Add: {add_text}, Remove: {remove_text} ({'toggle' if toggle else 'sticky'})")
    embed = create_embed(
        title = "📋 Reaction Roles",
        description = "\n".join(lines)
    )
    await ctx.send(embed = embed, ephemeral = True)
    
# Reaction Listeners
@bot.event
async def on_raw_reaction_add(payload):
    if payload.member and payload.member.bot:
        return
    mapping = bot_db.get_reaction_role_mapping(str(payload.guild_id), str(payload.message_id), str(payload.emoji))
    if mapping is None:
        return
    add_role_id, remove_role_id, toggle = mapping
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member is None:
        return
    if remove_role_id and (role := guild.get_role(int(remove_role_id))):
        await member.remove_roles(role, reason = "Reaction role")
    if add_role_id and (role := guild.get_role(int(add_role_id))):
        await member.add_roles(role, reason = "Reaction role")
        
@bot.event
async def on_raw_reaction_remove(payload):
    mapping = bot_db.get_reaction_role_mapping(str(payload.guild_id), str(payload.message_id), str(payload.emoji))
    if mapping is None:
        return
    add_role_id, remove_role_id, toggle = mapping
    if not toggle:
        return # sticky role
    
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member is None:
        return
    if add_role_id and (role := guild.get_role(int(add_role_id))):
        await member.remove_roles(role, reason = "Reaction role removed")
    if remove_role_id and (role := guild.get_role(int(remove_role_id))):
        await member.add_roles(role, reason = "Reaction role removed")
          
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

@checkavail.error
async def checkavail_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(original, commands.MemberNotFound):
        embed = create_embed(
            title = "⚠️ User Not Found",
            description = f"Couldn't find `{original.argument}`. Try adding an '@' in front of their name, or use their user ID",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Try `!checkavail @user`, or `!checkavail user_id`",
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
    
@reply.error
async def reply_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Missing message in `/reply`",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)        

@closeticket.error
async def closeticket_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "To close a ticket, use `/closeticket`",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        
@setlogs.error
async def setlogs_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "To set a log channel, use `/setlogs`",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)        
        
bot.run(TOKEN)
