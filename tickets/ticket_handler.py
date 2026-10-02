from common.bot_launch import bot
from tickets.route_ticket import route_ticket_message
from tickets.server_select_views import ServerSelectView


async def handle_ticket_dm(bot, message):
    user = message.author
    mutual_servers = [g for g in bot.guilds if g.get_member(user.id) is not None]
    
    if not mutual_servers:
        await user.send("Cannot open ticket as we have no mutual server(s)")
        return
    if len(mutual_servers) == 1:
        await route_ticket_message(bot, message, mutual_servers[0])
        return
    
    # If multiple servers detected
    view = ServerSelectView(mutual_servers, message)
    await user.send("Which server is this ticket for?", view = view)