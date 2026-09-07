import discord
from discord import app_commands
import time
import asyncio
import bot_db as bot_db
from embed import create_embed
import command_helpers as helper

# Current types of logs to set a channel for
LOG_TYPES = [
    app_commands.Choice(name = "Member Join", value = "Join"),
    app_commands.Choice(name = "Member Leave", value = "Leave"),
    app_commands.Choice(name = "Role Update", value = "Role Update"),
    app_commands.Choice(name = "Ban", value = "Ban"),
    app_commands.Choice(name = "Command", value = "Command"),
    app_commands.Choice(name = "Message Moderation", value = "Message"),
]

LOG_EXCLUDED_COMMANDS = set()

# Audit log for command usage
async def log_command_usage(ctx, create_embed):
    if ctx.command and ctx.command.name in LOG_EXCLUDED_COMMANDS:
        return
    try:
        channel_id = bot_db.get_log_channel(str(ctx.guild.id), "Command")
        if channel_id is None:
            return
        log_channel = ctx.bot.get_channel(int(channel_id))
        if log_channel is None:
            return
        timestamp = ctx.message.created_at if ctx.message else ctx.message.interaction.created_at
        embed = create_embed(
            title = "📝 Command Used",
            description = (
                f"**Command:** `{ctx.command}`\n"
                f"**User:** {ctx.author.mention} (`{ctx.author}`)\n"
                f"**Channel:** {ctx.channel.mention}\n"
                f"**Timestamp: ** <t:{int(timestamp.timestamp())}:F>"
            )
        )
        await log_channel.send(embed = embed)
    except Exception as e:
        print(f"Logging failed: {e}")
        
# Audit log(s) for entry (join/leave)
async def member_join(bot, member):
    channel_id = bot_db.get_log_channel(str(member.guild.id), "Join")
    if channel_id is None:
        return
    channel = bot.get_channel(int(channel_id))
    if channel is None:
        return
    
    created_ts = int(member.created_at.timestamp())
    embed = create_embed(
        title = "📥 New Member Joined",
        description = (
            f"**User:** {member.mention} (`{member}`)\n"
            f"**ID:** `{member.id}`\n"
            f"**Account Created:** <t:{created_ts}:F> (<t:{created_ts}:R>)\n"
            f"**Member Count:** {member.guild.member_count}"
        )
    )
    await channel.send(embed = embed)

async def member_leave(bot, member):
    channel_id = bot_db.get_log_channel(str(member.guild.id), "Leave")
    if channel_id is None:
        return
    channel = bot.get_channel(int(channel_id))
    if channel is None:
        return
    
    ban_entry = await helper.find_audit_log_entry(member.guild, discord.AuditLogAction.ban, member)
    kick_entry = None
    if not ban_entry:
        kick_entry = await helper.find_audit_log_entry(member.guild, discord.AuditLogAction.kick, member)
    
    created_ts = int(member.created_at.timestamp())
    joined_ts = int(member.joined_at.timestamp()) if member.joined_at else None
    
    lines = [
        f"**User:** {member.mention} (`{member}`)",
        f"**ID:** `{member.id}`",
        f"**Account Created:** <t:{created_ts}:F> (<t:{created_ts}:R>)",
    ]
    if joined_ts:
        lines.append(f"**Member Since:** <t:{joined_ts}:F> (<t:{joined_ts}:R>)")
    lines.append(f"**Member Count:** {member.guild.member_count}")
    
    if ban_entry:
        title = "📤 Member Left"
        ban_link = await get_ban_link(member.guild.id, member.id)
        note = f"[Banned]({ban_link})" if ban_link else "Banned. See ban log for details"   
        lines.append(note) 
    elif kick_entry:
        title = "📤 Member Left"
        lines.append(f"**Kicked by:** {kick_entry.user.mention}")
        lines.append(f"**Reason:** {kick_entry.reason or 'No reason provided'}")
    else:
        title = "📤 Member Left"
    embed = create_embed(
        title = title,
        description = "\n".join(lines)
    )
    await channel.send(embed = embed)

# Audit log for role update
async def role_update(bot, before, after):
    # Isolating to only check role update(s)
    if before.roles == after.roles:
        return
    channel_id = bot_db.get_log_channel(str(after.guild.id), "Role Update")
    if channel_id is None:
        return
    channel = bot.get_channel(int(channel_id))
    if channel is None:
        return
    
    before_roles = set(before.roles)
    after_roles = set(after.roles)
    added_roles = after_roles - before_roles
    removed_roles = before_roles - after_roles
    entry = await helper.find_audit_log_entry(after.guild, discord.AuditLogAction.member_role_update, after)

    lines = [
        f"**User:** {after.mention} (`{after}`)",
        f"**ID:** `{after.id}`",
    ]
    if added_roles:
        title = "🎭 Role(s) Added"
        lines.append(f"**Role(s) Added:** {', '.join(r.mention for r in added_roles)}")
    if removed_roles:
        title = "🎭 Role(s) Removed"
        lines.append(f"**Role(s) Removed:** {', '.join(r.mention for r in removed_roles)}")  
        
    if entry:
        actor = entry.user
        if actor.id == after.id:
            lines.append("**Changed by:** Self")
        else:
            lines.append(f"**Changed by:** {actor.mention}")
    else:
        lines.append(f"**Changed By:** Unknown (no matching user found in <#{channel_id}>)")
    
    embed = create_embed(
        title = title,
        description = "\n".join(lines)
    )
    await channel.send(embed = embed)

# Grabs guild_id and user_id, then finds its corresponding 
_pending_ban_link = {}

# Audit log for ban
async def member_ban(bot, guild, user):
    channel_id = bot_db.get_log_channel(str(guild.id), "Ban")
    if channel_id is None:
        return
    channel = bot.get_channel(int(channel_id))
    if channel is None:
        return

    ban_entry = await helper.find_audit_log_entry(guild, discord.AuditLogAction.ban, user)
    created_ts = int(user.created_at.timestamp())
    lines = [
        f"**User:** {user.mention} (`{user}`)",
        f"**ID** `{user.id}`",
        f"**Account Created:** <t:{created_ts}:F> (<t:{created_ts}:R>)",
        f"**Duration:** Permanent",
        f"**Reason:** {ban_entry.reason if ban_entry and ban_entry.reason else 'No reason provided'}",
        f"**Banned by:** {ban_entry.user.mention if ban_entry else 'Unknown'}",
    ]
    embed = create_embed(
        title = "🔨 Member Banned",
        description = "\n".join(lines)
    )
    sent_message = await channel.send(embed = embed)
    _pending_ban_link[(guild.id, user.id)] = sent_message.jump_url
    
async def get_ban_link(guild_id, user_id, wait_seconds = 2):
    key = (guild_id, user_id)
    if key in _pending_ban_link:
        return _pending_ban_link.pop(key)
    
    for _ in range(int(wait_seconds / 0.5)):
        await asyncio.sleep(0.5)
        if key in _pending_ban_link:
            return _pending_ban_link.pop(key)
    return None    
    