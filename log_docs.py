import discord
from discord import app_commands
import time
import re
import io
from datetime import timedelta
import asyncio
from urllib.parse import urlparse
import bot_db as bot_db
from embed import create_embed
import command_helpers as helper
import battlehub_bot_ui as ui

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

TIMEOUT_OPTIONS = [
    ("60 Seconds", 60),
    ("5 Minutes", 300),
    ("10 Minutes", 600),
    ("1 Hour", 3600),
    ("1 Day", 86400),
    ("1 Week", 604800),
]

URL_REGEX = re.compile(r'https?://[^\s<>"]+')

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

# Audit log for flagged messages/regular messages
def find_matched_terms(content, terms):
    if not content:
        return []
    lowered = content.lower()
    matched = []
    for term in terms:
        pattern = r'\b' + re.escape(term) + r'\b'
        if re.search(pattern, lowered):
            matched.append(term)
    return matched

async def scan_message_for_flags(bot, message):
    if message.author.bot:
        return
    if isinstance(message.channel, discord.DMChannel):
        return
    
    guild_id = str(message.guild.id)
    exempt_roles = {"Admin", "Moderator"}
    if any(r.name in exempt_roles for r in message.author.roles):
        return
    terms = bot_db.get_flagged_terms(guild_id)
    domains = bot_db.get_flagged_domains(guild_id)
    
    matched_keywords = find_matched_terms(message.content, terms) if terms else []
    matched_domains = find_matched_domains(message.content, domains) if domains else []
    matched_images = await helper.scan_image_for_flags(guild_id, message)
    if not matched_keywords and not matched_domains and not matched_images:
        return
    
    combined = (
        [f"Keyword: {t}" for t in matched_keywords] 
        + [f"Link: {d}" for d in matched_domains]
        + [f"Image: {m}" for m in matched_images]
    )
    await flagged_message(bot, message, combined)
    
async def flagged_message(bot, message, matched_terms):
    log_channel_id = bot_db.get_log_channel(str(message.guild.id), "Message")
    if log_channel_id is None:
        return
    log_channel = bot.get_channel(int(log_channel_id))
    if log_channel is None:
        return
    
    author = message.author
    content = message.content
    channel = message.channel
    guild_id = str(message.guild.id)
    files = []
    embed_image_filename = None
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image/"):
            image_bytes = await attachment.read()
            file = discord.File(io.BytesIO(image_bytes), filename = attachment.filename)
            files.append(file)
            if embed_image_filename is None:
                embed_image_filename = attachment.filename
    
    try:
        await message.delete()
    except discord.NotFound:
        pass # Continues if it cannot find the user/message
    
    try:
       await author.send("One of your messages was flagged for staff review. You'll be notified of the outcome")
    except discord.Forbidden:
        pass # Message review still proceeds even if user can't be DM'd
    
    review_embed = create_embed(
        title = "🚩 Message Flagged",
        description = (
            f"**Author:** {author.mention} (`{author}`)\n"
            f"**Channel:** {channel.mention}\n"
            f"**Matched:** {', '.join(f'`{t}`' for t in matched_terms)}\n\n"
            f"**Original Message:**\n{content or '*No text content*'}"
        ),
        colour = discord.Colour.red()
    )
    if embed_image_filename:
        review_embed.set_image(url = f"attachment://{embed_image_filename}")
    exempt_roles = {"Admin", "Moderator"}
    mentions = [r.mention for r in message.guild.roles if r.name in exempt_roles]
    if mentions:
        await log_channel.send(f"🚨🚨 Message flagged! Need staff review! 🚨🚨 {' '.join(mentions)}")
    
    view = ui.FlaggedMessageView()
    review_message = await log_channel.send(embed = review_embed, view = view, files = files)
    bot_db.create_pending_review(guild_id, str(review_message.id), str(author.id), str(channel.id), content, ",".join(matched_terms), int(time.time()))

async def review_decision(interaction, decision):
    review = bot_db.get_pending_review(str(interaction.message.id))
    if review is None:
        await interaction.response.send_message("Couldn't find review", ephemeral = True)
        return
    
    review_id, guild_id, author_id, channel_id, content, matched_terms, status = review
    if status != "pending":
        await interaction.response.send_message("A staff member has already reviewed this flag", ephemeral = True)
        return
    bot_db.set_review_status(review_id, decision)
    
    # Locks button regardless of outcome
    for item in interaction.message.components[0].children if interaction.message.components else []:
        pass
    
    disabled_view = discord.ui.View()
    updated_embed = interaction.message.embeds[0]
    updated_embed.colour = discord.Colour.green() if decision == "approved" else discord.Colour.red()
    updated_embed.add_field(
        name = "**Verdict:**",
        value = f"{decision.capitalize()} by {interaction.user.mention}",
        inline = False
    )
    await interaction.message.edit(embed = updated_embed, view = disabled_view)
    
    guild = interaction.client.get_guild(int(guild_id))
    member = guild.get_member(int(author_id)) if guild else None
    if decision == "approved":
        try:
            user = interaction.client.get_user(int(author_id))
            if user:
                await user.send("Your flagged message was reviewed and approved. You will not be timed out this time, but please be careful moving forward!")
        except discord.Forbidden:
            pass
        await interaction.response.send_message("Marked as approved", ephemeral = True)

async def block_decision(interaction, reason, message_id, duration_seconds):
    await interaction.response.defer(ephemeral = True)
    review = bot_db.get_pending_review(str(message_id))
    if review is None:
        await interaction.followup.send("Couldn't find review", ephemeral = True)
        return
    
    review_id, guild_id, author_id, channel_id, content, matched_terms, status = review
    if status != "pending":
        await interaction.followup.send("A staff member has already reviewed this flag", ephemeral = True)
        return
    bot_db.set_review_status(review_id, "blocked")
    
    guild = interaction.client.get_guild(int(guild_id))
    member = guild.get_member(int(author_id)) if guild else None
    duration_label = next((label for label, seconds in TIMEOUT_OPTIONS if seconds == duration_seconds), f"{duration_seconds} seconds")
    if member is None:
        result_note = "User no longer in the server"
    else:
        try:
            await member.timeout(discord.utils.utcnow() + timedelta(seconds = duration_seconds), reason = reason)
        except discord.Forbidden:
            pass
        try:
            await member.send(
                f"Your flagged message was reviewed and blocked.\n"
                f"**You have been timed out for {duration_label}**\n"
                f"**Reason:** {reason}"
            )
        except discord.Forbidden:
            pass
        bot_db.increment_strike_count(guild_id, author_id)
        new_count = bot_db.get_strike_count(guild_id, author_id)
        result_note = ( 
                    f"**Blocked by:** {interaction.user.mention}\n"
                    f"**Timeout:** {duration_label}\n"
                    f"**Reason:** {reason}\n"
                    f"**Current strike:** {new_count}/3"
        )
    log_channel_id = bot_db.get_log_channel(guild_id, "Message")
    log_channel = interaction.client.get_channel(int(log_channel_id))
    review_msg = await log_channel.fetch_message(int(message_id))
    
    original_embed = review_msg.embeds[0]
    original_embed.colour = discord.Colour.red()
    original_embed.add_field(
        name = "**Verdict:**",
        value = result_note,
        inline = False
    )
    await review_msg.edit(embed = original_embed, view = discord.ui.View())
    await interaction.followup.send("Message blocked and logged", ephemeral = True)

async def strike_ban(interaction, staff_reason, message_id, origin):
    await interaction.response.defer(ephemeral = True)
    review = bot_db.get_pending_review(str(message_id))
    if review is None:
        await interaction.followup.send("Couldn't find review", ephemeral = True)
        return
    review_id, guild_id, author_id, channel_id, content, matched_terms, status = review
    if status != "pending":
        await interaction.followup.send("A staff member has already reviewed this flag", ephemeral = True)
        return
    
    bot_db.set_review_status(review_id, "blocked")
    if origin == "strike":
        combined_reason = f"3 strikes, you're out!\n**Staff note:** {staff_reason}"
    else:
        combined_reason = f"User Ban (Severe Rule Violation): {staff_reason}"
    guild = interaction.client.get_guild(int(guild_id))
    member = guild.get_member(int(author_id)) if guild else None
    if member is None:
        result_note = "User no longer in the server"
    else:
        try:
            await member.send(
                f"You have been banned for breaking server rules\n"
                f"**Reason:** {combined_reason}"
            )
        except discord.Forbidden:
            pass
        try:
            await guild.ban(member, reason = combined_reason)
        except discord.Forbidden:
            pass
        result_note = f"Banned by {interaction.user.mention}\nReason: {staff_reason}"
    
    bot_db.reset_strike_count(guild_id, author_id)
    log_channel_id = bot_db.get_log_channel(guild_id, "Message")
    log_channel = interaction.client.get_channel(int(log_channel_id))
    review_msg = await log_channel.fetch_message(int(message_id))
    
    original_embed = review_msg.embeds[0]
    original_embed.colour = discord.Colour.red()
    original_embed.add_field(
        name = "**Verdict:**",
        value = result_note,
        inline = False
    )
    await review_msg.edit(embed = original_embed, view = discord.ui.View())
    await interaction.followup.send("User banned and logged", ephemeral = True)

def extract_domains(content):
    if not content:
        return []
    domains = []
    for url in URL_REGEX.findall(content):
        try:
            netloc = urlparse(url).netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            domains.append(netloc)
        except Exception:
            continue
    return domains

def find_matched_domains(content, flagged_domains):
    found = extract_domains(content)
    return [d for d in found for flagged in flagged_domains if d == flagged or d.endswith("." + flagged)]

def render_welcome_message(template, member):
    return (
        template
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{server}", member.guild.name)
        .replace("{membercount}", str(member.guild.member_count))
    )

async def send_welcome(bot, member):
    settings = bot_db.get_welcome(str(member.guild.id))
    if settings is None:
        return
    channel_id, template = settings
    channel = bot.get_channel(int(channel_id))
    if channel is None:
        return
    rendered = render_welcome_message(template, member)
    await channel.send(rendered)