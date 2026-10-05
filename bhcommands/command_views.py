import discord
from bhcommands.command_config import COMMAND_CATEGORIES
from bhcommands.command_helpers import build_command_page


class CommandPageView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout = None)
        self.ctx = ctx
        self.index = 0
        self.add_item(CategorySelect(self))
        self._update_button_states()
        
    def _update_button_states(self):
        for button in self.children:
            if isinstance(button, discord.ui.Button):
                if "Previous" in str(button.label):
                    button.disabled = (self.index == 0)
                elif "Next" in str(button.label):
                    button.disabled = (self.index == len(COMMAND_CATEGORIES) - 1)
    
    async def on_timeout(self):
        for button in self.children:
            button.disabled = True
        try:
            if self.ctx.interaction:    
                await self.ctx.interaction.edit_original_response(view = self)
        except discord.HTTPException:
           pass
                
    @discord.ui.button(label = "◀ Previous Page", style = discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index -= 1
        self._update_button_states()
        await interaction.response.edit_message(embed = build_command_page(self.index), view = self)
        
    @discord.ui.button(label = "Next Page ▶", style = discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index += 1
        self._update_button_states()
        await interaction.response.edit_message(embed = build_command_page(self.index), view = self)
        
class CategorySelect(discord.ui.Select):
    def __init__(self, page_view):
        options = [discord.SelectOption(label = title, value = str(i)) for i, (title, _) in enumerate(COMMAND_CATEGORIES)]
        super().__init__(placeholder = "Commands List", options = options)
        self.page_view = page_view
    
    async def callback(self, interaction: discord.Interaction):
        self.page_view.index = int(self.values[0])
        self.page_view._update_button_states()
        await interaction.response.edit_message(embed = build_command_page(self.page_view.index), view = self.page_view)
        