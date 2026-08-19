import discord
from command_helpers import _build_availability_breakdown
from datetime import datetime
from calendar import monthrange
from zoneinfo import ZoneInfo
from bot_db import get_events_by_month
from embed import create_embed

class EventSelect(discord.ui.Select):
    def __init__(self, events, guild_id):
        options = [discord.SelectOption(label = name, value = str(eid)) for eid, name, ts, added_by in events]
        super().__init__(placeholder = "Choose an event...", options = options) 
        self.events_lookup = {str(eid): (eid, name, ts, added_by) for eid, name, ts, added_by in events}
        self.guild_id = guild_id
    
    async def callback(self, interaction: discord.Interaction):
        selected_event = self.events_lookup[self.values[0]]
        embed = await _build_availability_breakdown(interaction, selected_event, self.guild_id)
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
        events = get_events_by_month(start_ts, end_ts, self.guild_id)
        
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
            