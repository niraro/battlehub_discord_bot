import time
from common.embed import create_embed
from database.tickets_db import get_open_ticket, update_ticket_activity, get_tickets_channel
from tickets.ticket_helpers import ticket_images
from tickets.ticket_views import TicketStartView


# Routes user message to selected server
async def route_ticket_message(bot, message, guild):
    guild_id = str(guild.id)
    discord_id = str(message.author.id)
    now = int(time.time())
    existing = get_open_ticket(guild_id, discord_id)
    
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
        update_ticket_activity(thread_id, now)
        await message.author.send(f"Message added to current ticket: **Ticket #{ticket_number}**")
        return
        
    # If no exisiting open tickets, create new one
    tickets_channel_id = get_tickets_channel(guild_id)
    if tickets_channel_id is None:
        await message.author.send("This server hasn't set up a tickets channel yet. Please contact staff directly, or wait until a ticket channel is set up")
        return
   
    view = TicketStartView(bot, message, guild)
    await message.author.send("Click below to create your ticket:", view = view)