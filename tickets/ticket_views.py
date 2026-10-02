import discord
from tickets.ticket_helpers import create_ticket_from_modal


class TicketModal(discord.ui.Modal, title = "Open a Ticket"):
    def __init__(self, bot, dm_message, guild):
        super().__init__()
        self.bot = bot
        self.dm_message = dm_message
        self.guild = guild
        
        self.title_input = discord.ui.TextInput(
            label = "What do you need help with?",
            placeholder = "Short summary of your inquiry",
            max_length = 100
        )
        self.description_input = discord.ui.TextInput(
            label = "Description of inquiry",
            placeholder = "Provide more details of your inquiry here",
            style = discord.TextStyle.paragraph,
            default = dm_message.content or "",
            required = False
        )
        self.add_item(self.title_input)
        self.add_item(self.description_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral = True)
        await create_ticket_from_modal(
            self.bot,
            self.dm_message,
            self.guild,
            str(self.title_input),
            str(self.description_input)
        )
        await interaction.followup.send(f"Ticket **{self.title_input}** submitted!")

class TicketStartView(discord.ui.View):
    def __init__(self, bot, dm_message, guild):
        super().__init__(timeout = 300)
        self.bot = bot
        self.dm_message = dm_message
        self.guild = guild
    
    @discord.ui.button(
        label = "Create Ticket",
        style = discord.ButtonStyle.primary,
        emoji = "🎫"
    )
    async def start_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal(self.bot, self.dm_message, self.guild))