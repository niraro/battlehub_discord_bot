import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
from database import init_db
from common.bot_launch import bot
from common.embed import create_embed
from database.reaction_roles_db import get_reaction_role_mapping
from tickets.ticket_helpers import check_stale_tickets
from tickets.ticket_handler import handle_ticket_dm
from moderation.logs_helpers import log_command_usage, member_ban, member_join, member_leave, role_update, check_honeypot
from moderation.moderation_helpers import timeout_update
from moderation.flagging_helpers import scan_message_for_flags
from scheduling.scheduling_views import ScheduleView, refresh_schedule_posts
from welcome.welcome_helpers import send_welcome
import announcements.news_commands
import bhcommands.commands
import common.general_commands
import events.event_commands
import moderation.flag_setup_commands, moderation.moderation_commands, moderation.moderation_setup_commands
import reactions.reaction_role_commands
import scheduling.scheduling_commands
import tickets.ticket_commands
import welcome.welcome_commands

# Load the token from the .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
dev_guild_id_raw = os.getenv("DEV_GUILD_ID")
DEV_GUILD_ID = int(dev_guild_id_raw) if dev_guild_id_raw else None

# Initialises all tables in "database"
init_db()

# Tells user that bot is online
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} - bot is online!")
    if DEV_GUILD_ID:
        guild = discord.Object(id = DEV_GUILD_ID)
        bot.tree.clear_commands(guild = guild)
        await bot.tree.sync(guild = guild)
        print(f"Guild-synced commands to {DEV_GUILD_ID}")
    else:
        print("Dev_GUILD_ID not set -- Skipping guild-scoped sync")
        
    if not check_stale_tickets.is_running():
        check_stale_tickets.start()
    
    if not getattr(bot, "schedule_ready", False):
        bot.schedule_ready = True
        bot.add_view(ScheduleView())
        bot.schedule_refresh_task = asyncio.create_task(refresh_schedule_posts(bot))

# !sync -- Syncs commands from dev testing to VPS version
@bot.command()
@commands.is_owner()
async def sync(ctx):
    synced = await bot.tree.sync()
    await ctx.send(f"Synced {len(synced)} command(s) globally. May take up to 1h to sync globally")

@sync.error
async def sync_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.message.delete()
        return

# !clear_guild_sync -- Clears duplicate commands  
@bot.command()
@commands.is_owner()
async def clear_guild_sync(ctx):
    bot.tree.clear_commands(guild = ctx.guild)
    await bot.tree.sync(guild = ctx.guild)
    await ctx.send("Guild-specific command duplicates cleared")

@clear_guild_sync.error
async def clear_guild_sync_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.message.delete()
        return    

# Non-existent command error check listener
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        attempted = ctx.message.content.split()[0] if ctx.message else "that command"
        await ctx.send(f"Command `{attempted}` does not exist.")
        return

# Logs which command gets used, by which user, and in which channel
@bot.before_invoke
async def before_command_use(ctx):
    await log_command_usage(ctx, create_embed)

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
    triggered = await check_honeypot(bot, message)
    if triggered:
        return
    
    # Message Flag listener
    await scan_message_for_flags(bot, message)
    
    # Allows commands with prefix to work
    await bot.process_commands(message)

################################ Moderation Tools ##################################

@bot.event
async def on_member_join(member):
    await member_join(bot, member)
    await send_welcome(bot, member)

@bot.event
async def on_member_remove(member):
    await member_leave(bot, member)
    
@bot.event
async def on_member_ban(guild, user):
    await member_ban(bot, guild, user)

@bot.event
async def on_member_update(before, after):
    await role_update(bot, before, after)
    await timeout_update(bot, before, after)

@bot.event
async def on_message_edit(before, after):
    if after.author.bot:
        return
    if before.content == after.content:
        return
    await scan_message_for_flags(bot, after)
      
############################# REACTION Commands ##############################
    
# Reaction Listeners
@bot.event
async def on_raw_reaction_add(payload):
    if payload.member and payload.member.bot:
        return
    mapping = get_reaction_role_mapping(str(payload.guild_id), str(payload.message_id), str(payload.emoji))
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
    mapping = get_reaction_role_mapping(str(payload.guild_id), str(payload.message_id), str(payload.emoji))
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
          
        
bot.run(TOKEN)
