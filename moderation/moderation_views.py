import discord
from moderation.moderation_helpers import TIMEOUT_OPTIONS, review_decision, strike_ban, block_decision
from database.moderation_db import get_pending_review


class FlaggedMessageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout = None)
    
    @discord.ui.button(
        label = "Approve",
        style = discord.ButtonStyle.success,
        emoji = "✅"
    )
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await review_decision(interaction, "approved")
        
    @discord.ui.button(
        label = "Timeout",
        style = discord.ButtonStyle.danger,
        emoji = "🚫"        
    )
    async def timeout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        review = get_pending_review(str(interaction.message.id))
        if review is None:
            await interaction.response.send_message("Couldn't find review", ephemeral = True)
            return
        review_id, guild_id, author_id, channel_id, content, matched_terms, status = review
        if status != "pending":
            await interaction.response.send_message("A staff member has already reviewed this flag", ephemeral = True)
            return      
        view = TimeoutDurationSelectView(interaction.message.id)
        await interaction.response.send_message("Select a timeout duration:", view = view, ephemeral = True)
    
    @discord.ui.button(
        label = "Ban",
        style = discord.ButtonStyle.danger,
        emoji = "🔨"
    )
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BlockReasonModal(interaction.message.id, None, ban_origin = "manual"))
            
class BlockReasonModal(discord.ui.Modal):
    reason = discord.ui.TextInput(
        label = "Reason",
        style = discord.TextStyle.paragraph,
        required = True
    )
    
    def __init__(self, message_id, duration_seconds = None, ban_origin = None):
        if ban_origin == "manual":
            title = "Ban User: Severe Rule Violation"
        else:
            title = "Block Message"
        super().__init__(title = title)
        self.message_id = message_id
        self.duration_seconds = duration_seconds
        self.ban_origin = ban_origin
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.ban_origin:
            await strike_ban(interaction, str(self.reason), self.message_id, self.ban_origin)
        else:
            await block_decision(interaction, str(self.reason), self.message_id, self.duration_seconds)

class TimeoutDurationSelect(discord.ui.Select):
    def __init__(self, message_id):
        options = [discord.SelectOption(label = label, value = str(seconds)) for label, seconds in TIMEOUT_OPTIONS]
        super().__init__(
            placeholder = "Choose timeout duration...",
            options = options
        )
        self.message_id = message_id
        
    async def callback(self, interaction: discord.Interaction):
        duration_seconds = int(self.values[0])
        await interaction.response.send_modal(BlockReasonModal(self.message_id, duration_seconds))
        
class TimeoutDurationSelectView(discord.ui.View):
    def __init__(self, message_id):
        super().__init__(timeout = 120)
        self.add_item(TimeoutDurationSelect(message_id))    