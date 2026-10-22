import discord
from common.error_handlers import error_embed
from common.general_helpers import parse_term_list
from moderation.flagging_helpers import add_terms_and_report


class AddTermModal(discord.ui.Modal, title = "Add Flagged Terms"):
    terms = discord.ui.TextInput(
        label = "Terms (comma or new line separated)",
        style = discord.TextStyle.paragraph,
        placeholder = "Example(s): free nitro, mr beast giving away money for free, any phrase with spaces",
        max_length = 4000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        parsed = parse_term_list(self.terms.value)
        if not parsed:
            await interaction.response.send_message(embed = error_embed("No Terms", "Nothing to add. Separate terms with commas or new lines"), ephemeral = True)
            return
        embed = add_terms_and_report(str(interaction.guild_id), parsed, str(interaction.user))
        await interaction.response.send_message(embed = embed, ephemeral = True)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        embed = error_embed("Something Went Wrong", "The terms could not be added to the list")
        if interaction.response.is_done():
            await interaction.followup.send(embed = embed, ephemeral = True)
        else:
            await interaction.response.send_message(embed = embed, ephemeral = True)
        raise error
    
class OpenAddTermView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout = 600) # 10 min before modal closes/becomes unavailable
        self.author_id = author_id
    
    @discord.ui.button(label = "Add Terms", style = discord.ButtonStyle.success, emoji = "📝")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the person who ran the command can use this", ephemeral = True)
            return
        await interaction.response.send_modal(AddTermModal())