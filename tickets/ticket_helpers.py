import discord
from discord.ext import tasks
import time
from common.bot_launch import bot
from common.embed import create_embed
from database import tickets_db as db


TICKET_INACTIVITY_SECONDS = 120 # Temporarily 2 minute for testing

@tasks.loop(minutes = 1) # Temporarily set to check every minute
async def check_stale_tickets():
    cutoff = int(time.time()) - TICKET_INACTIVITY_SECONDS
    stale_tickets = db.get_stale_tickets(cutoff)
    
    for ticket_id, guild_id, discord_id, thread_id, ticket_number in stale_tickets:
        db.close_ticket(ticket_id)
        await update_ticket_board(bot, guild_id)
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
    tickets_channel_id = db.get_tickets_channel(guild_id)
    if tickets_channel_id is None:
        return
    channel = bot.get_channel(int(tickets_channel_id))
    if channel is None:
        return
    
    open_tickets = db.get_open_tickets_for_board(guild_id)
    closed_count = db.get_closed_ticket_count(guild_id)
    
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
    
    board_message_id = db.get_board_message_id(guild_id)
    if board_message_id:
        try:
            message = await channel.fetch_message(int(board_message_id))
            await message.edit(embed = embed)
            return
        except discord.NotFound:
            pass # Creates new message board if deleted or non-existent
    
    new_message = await channel.send(embed = embed)
    db.set_board_message_id(guild_id, str(new_message.id))
    
async def notify_ticket_staff(bot, guild, thread):
    tickets_channel_id = db.get_tickets_channel(str(guild.id))
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
        
    tickets_channel_id = db.get_tickets_channel(guild_id)
    tickets_channel = bot.get_channel(int(tickets_channel_id))
    if tickets_channel is None:
        await dm_message.author.send("Couldn't find the configured tickets channel. Please contact staff directly")
        return    
    
    ticket_number = db.get_next_ticket_number(guild_id)
    thread_name = f"Ticket #{ticket_number} -- {title}" [:100]
    thread = await tickets_channel.create_thread(
        name = thread_name,
        type = discord.ChannelType.private_thread
    )
    
    db.create_ticket(guild_id, discord_id, ticket_number, str(thread.id), title, now)
    
    # Embed seen by staff in newly created ticket thread
    _, image_url = ticket_images(dm_message)
    intro_embed = create_embed(
        title = f"🎫 Ticket #{ticket_number}: {title}",
        description = f"**User:** {dm_message.author.mention} (`{dm_message.author}`)\n **Inquiry Description:**\n{description or '*No description provided*'}"
    )
    if image_url:
        intro_embed.set_image(url = image_url)
    await thread.send(embed = intro_embed)
    await dm_message.author.send(f"Your ticket has been created: **Ticket #{ticket_number}**. Staff will respond ASAP")
    await notify_ticket_staff(bot, guild, thread)
    await update_ticket_board(bot, str(guild.id))
    