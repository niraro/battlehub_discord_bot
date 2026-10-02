import discord
from tickets.route_ticket import route_ticket_message


class ServerSelect(discord.ui.Select):
    def __init__(self, guilds, original_message):
        options = [discord.SelectOption(label = g.name, value = str(g.id)) for g in guilds]
        super().__init__(placeholder = "Choose a server: ", options = options)
        self.guilds_lookup = {str(g.id): g for g in guilds}
        self.original_message = original_message
    
    async def callback(self, interaction: discord.Interaction):
        selected_server = self.guilds_lookup[self.values[0]]
        await route_ticket_message(interaction.client, self.original_message, selected_server)
        await interaction.response.send_message(f"You have chosen to create a ticket for **{selected_server}**", ephemeral = True)
        
class ServerSelectView(discord.ui.View):
    def __init__(self, guilds, original_message):
        super().__init__(timeout = 300) # 5 minute (300 seconds) timer for user to choose server
        self.add_item(ServerSelect(guilds, original_message))