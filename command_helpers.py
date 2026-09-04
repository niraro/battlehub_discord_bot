import discord
import re
import time
import battlehub_bot_ui as bh_ui
from zoneinfo import ZoneInfo
import bot_db as bot_db
from embed import create_embed


DATE_REGEX = re.compile(r"^\d{2}-\d{2}-\d{4}$")
TIME_REGEX = re.compile(r"^\d{2}:\d{2}$")

LOG_EXCLUDED_COMMANDS = set()

# Audit log for command usage
async def log_command_usage(ctx, log_channel_id, create_embed_fn):
    if ctx.command and ctx.command.name in LOG_EXCLUDED_COMMANDS:
        return
    try:
        log_channel = ctx.bot.get_channel(log_channel_id)
        if log_channel_id is None:
            return
        embed = create_embed(
            title = "📝 Command Used",
            description = (
                f"**Command:** `{ctx.command}`\n"
                f"**User:** {ctx.author.mention} (`{ctx.author}`)\n"
                f"**Channel:** {ctx.channel.mention}"
            )
        )
        await log_channel.send(embed = embed)
    except Exception as e:
        print(f"Command logging failed: {e}")

# Routes user message to selected server
async def route_ticket_message(bot, message, guild):
    guild_id = str(guild.id)
    discord_id = str(message.author.id)
    now = int(time.time())
    existing = bot_db.get_open_ticket(guild_id, discord_id)
    
    # Open/exisitng ticket case
    if existing:
        ticket_id, ticket_number, thread_id = existing
        thread = bot.get_channel(int(thread_id))
        if thread is None:
            await message.author.send("Could not find your ticket. Please try again")
            return
        description, image_url = ticket_images(message)
        embed = create_embed(
            title = f"Ticket #{ticket_number}",
            description = description
        )
        if image_url:
            embed.set_image(url = image_url)
        await thread.send(embed = embed)
        bot_db.update_ticket_activity(thread_id, now)
        await message.author.send(f"Message added to current ticket: **Ticket #{ticket_number}**")
        return
        
    # If no exisiting open tickets, create new one
    tickets_channel_id = bot_db.get_tickets_channel(guild_id)
    if tickets_channel_id is None:
        await message.author.send("This server hasn't set up a tickets channel yet. Please contact staff directly, or wait until a ticket channel is set up")
        return
   
    view = bh_ui.TicketStartView(bot, message, guild)
    await message.author.send("Click below to create your ticket:", view = view)
    
def ticket_images(message):
    text = message.content or ""
    image_url = None
    extra_links = []
    
    for attachment in message.attachments:
        content_type = (attachment.content_type or "").lower()
        if image_url is None and (content_type.startswith("image/")):
            image_url = attachment.url
        else:
            extra_links.append(attachment.url)
            
    if extra_links:
        text += "\n\n" + "\n".join(extra_links)
    if not text.strip() and not image_url:
        text = "*[No text/attachment]*"
    return text, image_url

async def update_ticket_board(bot, guild_id):
    tickets_channel_id = bot_db.get_tickets_channel(guild_id)
    if tickets_channel_id is None:
        return
    channel = bot.get_channel(int(tickets_channel_id))
    if channel is None:
        return
    
    open_tickets = bot_db.get_open_tickets_for_board(guild_id)
    closed_count = bot_db.get_closed_ticket_count(guild_id)
    
    if not open_tickets:
        open_lines = "Currently no open tickets"
    else:
        lines = []
        for ticket_number, title, thread_id in open_tickets:
            thread = bot.get_channel(int(thread_id))
            link = thread.jump_url if thread else "Thread unavailable"
            lines.append(f"**#{ticket_number}**: {title or 'Untitled'} --> {link}")
        open_lines = "\n".join(lines)
    
    embed = create_embed(
        title = "🎫 Ticket Board",
        description = f"**Open Tickets**\n{open_lines}\n\n**Closed Tickets:** {closed_count} total"
    )
    
    board_message_id = bot_db.get_board_message_id(guild_id)
    if board_message_id:
        try:
            message = await channel.fetch_message(int(board_message_id))
            await message.edit(embed = embed)
            return
        except discord.NotFound:
            pass # Creates new message board if deleted or non-existent
    
    new_message = await channel.send(embed = embed)
    bot_db.set_board_message_id(guild_id, str(new_message.id))
    
async def notify_ticket_staff(bot, guild, thread):
    tickets_channel_id = bot_db.get_tickets_channel(str(guild.id))
    channel = bot.get_channel(int(tickets_channel_id))
    if channel is None:
        return
    role_names = ("Announcer", "Admin") 
    mentions = [r.mention for r in guild.roles if r.name in role_names]
    if not mentions:
        return
    await channel.send(f"{' '.join(mentions)} New ticket: {thread.jump_url}", delete_after = 10)
   
async def create_ticket_from_modal(bot, dm_message, guild, title, description):
    guild_id = str(guild.id)
    discord_id = str(dm_message.author.id)
    now = int(time.time())
        
    tickets_channel_id = bot_db.get_tickets_channel(guild_id)
    tickets_channel = bot.get_channel(int(tickets_channel_id))
    if tickets_channel is None:
        await dm_message.author.send("Couldn't find the configured tickets channel. Please contact staff directly")
        return    
    
    ticket_number = bot_db.get_next_ticket_number(guild_id)
    thread_name = f"Ticket #{ticket_number} -- {title}" [:100]
    thread = await tickets_channel.create_thread(
        name = thread_name,
        type = discord.ChannelType.private_thread
    )
    
    bot_db.create_ticket(guild_id, discord_id, ticket_number, str(thread.id), title, now)
    
    # Embed seen by staff in newly created ticket thread
    _, image_url = ticket_images(dm_message)
    intro_embed = create_embed(
        title = f"🎫 Ticket #{ticket_number}: {title}",
        description = f"**User:** {dm_message.author.mention} (`{dm_message.author}`)\n **Inquiry Description:**\n{description or '*No description provided*'}"
    )
    if image_url:
        intro_embed.set_image(url = image_url)
    await thread.send(embed = intro_embed)
    await dm_message.author.send(f"Your ticket has been created -- **Ticket #{ticket_number}**. Staff will respond ASAP")
    await notify_ticket_staff(bot, guild, thread)
    await update_ticket_board(bot, str(guild.id))



# !addevent pattern detector of an unquoted mult-word event name. Pushes a valid date/time/timezone one slot to the right
def looks_like_shifted_args(time_str, tz_name):
    if not DATE_REGEX.match(time_str):
        return False
    parts = tz_name.split(maxsplit = 1)
    if len(parts) != 2:
        return False
    time_part, tz_part = parts
    if not TIME_REGEX.match(time_part):
        return False
    try:
        ZoneInfo(tz_part)
    except Exception as e:
        return False
    return True


async def _set_availability(ctx, event_name, role, status, note):
    event = bot_db.get_event_from_list(event_name, str(ctx.guild.id))
    if not event:
        embed = create_embed(
            title = "⚠️ Event Not Found", 
            description = f"**{event_name}** not found. Make sure event exists (check spelling, typos, etc)",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    role_obj = discord.utils.find(lambda r: r.name.lower() == role.lower(), ctx.guild.roles)
    if not role_obj:
        embed = create_embed(
            title = "⚠️ Role Not Found",
            description = f"No role called `{role}`",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    if role_obj not in ctx.author.roles:
        embed = create_embed(
            title = "⚠️ Role Mismatch",
            description = f"You do not have the `{role_obj.name}` role",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True )
        return

    status = status.capitalize()
    if status not in ("Yes", "No", "Maybe"):
        embed = create_embed(
            title = "⚠️ Invalid Status",
            description = "Options are `Yes`, `No`, `Maybe`",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    bot_db.upsert_availability(event[0], str(ctx.author.id), role_obj.name, status, note, str(ctx.guild.id))
    note_text = f"\nNote: {note}" if note else ""
    embed = create_embed(
        title = "✅ Availability Updated",
        description = f"Availability for **{event[1]}** as `{role_obj.name}` has been updated to: `{status}`\n_{note_text}_"
    )
    await ctx.send(embed = embed)
    if ctx.interaction is None:
        await ctx.message.delete()


async def _build_availability_breakdown(ctx_or_interaction, event, guild_id):
    entries = bot_db.get_availability_by_event(event[0], guild_id)
    if not entries:
        return create_embed(
            title = f"📋 Staff Availability — **{event[1]}**",
            description = "No staff currently available"
        )
    
    grouped = {}
    for discord_id, role, status, note in entries:
        grouped.setdefault(role, []).append((discord_id, status, note))
    
    lines = []
    for role, responses in  grouped.items():
        lines.append(f"**{role}**")
        for discord_id, status, note, in responses:
                member = ctx_or_interaction.guild.get_member(int(discord_id))
                name = member.display_name if member else f"Unknown member: `{discord}`"
                note_text = f"_({note}_)" if note else ""
                lines.append(f"{name} - {status} {note_text}")
        lines.append("")
    return create_embed(
        title = f"📋 Staff Availability — **{event[1]}**",
        description = "\n".join(lines).strip()
    )