import discord
from datetime import datetime
from calendar import monthrange
from zoneinfo import ZoneInfo
import bot_db as bot_db
from embed import create_embed
import command_helpers as helper
import log_docs as logs
from log_docs import TIMEOUT_OPTIONS

class ServerSelect(discord.ui.Select):
    def __init__(self, guilds, original_message):
        options = [discord.SelectOption(label = g.name, value = str(g.id)) for g in guilds]
        super().__init__(placeholder = "Choose a server: ", options = options)
        self.guilds_lookup = {str(g.id): g for g in guilds}
        self.original_message = original_message
    
    async def callback(self, interaction: discord.Interaction):
        selected_server = self.guilds_lookup[self.values[0]]
        await helper.route_ticket_message(interaction.client, self.original_message, selected_server)
        await interaction.response.send_message(f"You have chosen to create a ticket for **{selected_server}**", ephemeral = True)
        
class ServerSelectView(discord.ui.View):
    def __init__(self, guilds, original_message):
        super().__init__(timeout = 300) # 5 minute (300 seconds) timer for user to choose server
        self.add_item(ServerSelect(guilds, original_message))

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
        await helper.create_ticket_from_modal(
            self.bot,
            self.dm_message,
            self.guild,
            str(self.title_input),
            str(self.description_input)
        )
        await interaction.response.send_message(f"Ticket **{self.title_input}** submitted!")

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


class EventSelect(discord.ui.Select):
    def __init__(self, events, guild_id):
        options = [discord.SelectOption(label = name, value = str(eid)) for eid, name, ts, added_by in events]
        super().__init__(placeholder = "Choose an event...", options = options) 
        self.events_lookup = {str(eid): (eid, name, ts, added_by) for eid, name, ts, added_by in events}
        self.guild_id = guild_id
    
    async def callback(self, interaction: discord.Interaction):
        selected_event = self.events_lookup[self.values[0]]
        embed = await helper._build_availability_breakdown(interaction, selected_event, self.guild_id)
        await interaction.response.send_message(embed = embed)
        
class EventSelectView(discord.ui.View):
    def __init__(self, events, guild_id):
        super().__init__(timeout = 60)
        self.add_item(EventSelect(events, guild_id))
  
def _add_months(dt, months):
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    return dt.replace(year = year, month = month, day = 1)

class MonthSelect(discord.ui.Select):
    def __init__(self, tz_name = "America/Edmonton", guild_id = None):
        self.tz_name = tz_name
        self.guild_id = guild_id
        now = datetime.now(ZoneInfo(tz_name))
        options = []
        for i in range(12):
            month_date = _add_months(now, i)
            options.append(discord.SelectOption(
                label = month_date.strftime("%B %Y"),
                value = month_date.strftime("%m-%Y")    
            ))
        super().__init__(placeholder = "Choose a month", options = options)
        
    async def callback(self, interaction: discord.Interaction):
        month_dt = datetime.strptime(self.values[0], "%m-%Y")
        tz = ZoneInfo(self.tz_name)
        month_start = month_dt.replace(day = 1, tzinfo = tz)
        last_day = monthrange(month_dt.year, month_dt.month)[1]
        month_end = month_dt.replace(day = last_day, hour = 23, minute = 59, second = 59, tzinfo = tz)
        
        start_ts = int(month_start.timestamp())
        end_ts = int(month_end.timestamp())
        events = bot_db.get_events_by_month(start_ts, end_ts, self.guild_id)
        
        if not events:
                embed = create_embed(
                    title = f"📅 {month_dt.strftime('%B %Y')}",
                    description = f"Currently no upcoming events in {month_dt.strftime('%B %Y')}"
                )
        else:
            lines = [f"**{name}** - <t:{ts}:F>" for eid, name, ts, added_by in events]
            embed = create_embed(
                title = f"📅 {month_dt.strftime('%B %Y')}",
                description = "\n".join(lines)
            )
        await interaction.response.send_message (embed = embed)

class MonthSelectView(discord.ui.View):
    def __init__(self, tz_name = "America/Edmonton", guild_id = None):
        super().__init__(timeout = 60)
        self.add_item(MonthSelect(tz_name, guild_id))


class FlaggedMessageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout = None)
    
    @discord.ui.button(
        label = "Approve",
        style = discord.ButtonStyle.success,
        emoji = "✅"
    )
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await logs.review_decision(interaction, "approved")
        
    @discord.ui.button(
        label = "Block + Timeout",
        style = discord.ButtonStyle.danger,
        emoji = "🚫"        
    )
    async def block(self, interaction: discord.Interaction, button: discord.ui.Button):
        review = bot_db.get_pending_review(str(interaction.message.id))
        if review is None:
            await interaction.response.send_message("Couldn't find review", ephemeral = True)
            return
        review_id, guild_id, author_id, channel_id, content, matched_terms, status = review
        if status != "pending":
            await interaction.response.send_message("A staff member has already reviewed this flag", ephemeral = True)
            return
        strikes = bot_db.get_strike_count(guild_id, author_id)
        if strikes >= 2:
            await interaction.response.send_modal(BlockReasonModal(interaction.message.id, None, is_ban = True))
        else:      
            view = TimeoutDurationSelectView(interaction.message.id)
            await interaction.response.send_message("Select a timeout duration:", view = view, ephemeral = True)
        
class BlockReasonModal(discord.ui.Modal):
    reason = discord.ui.TextInput(
        label = "Reason",
        style = discord.TextStyle.paragraph,
        required = True
    )
    
    def __init__(self, message_id, duration_seconds = None, is_ban = False):
        title = "Block Message: 3rd Strike (Ban)" if is_ban else "Block Message"
        super().__init__(title = title)
        self.message_id = message_id
        self.duration_seconds = duration_seconds
        self.is_ban = is_ban
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.is_ban:
            await logs.strike_ban(interaction, str(self.reason), self.message_id)
        else:
            await logs.block_decision(interaction, str(self.reason), self.message_id, self.duration_seconds)

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