import discord
import traceback
import asyncio
import time
from common.embed import create_embed
from database.scheduling_db import (
    create_schedule, get_schedule_by_message, get_availability_by_event, update_schedule_times, delete_schedule_by_event, delete_schedule_data_for_event, get_active_schedules
)
from scheduling.scheduling_config import UNAVAILABLE, MAYBE, WITHDRAW, EDIT, RESET, DEADLOCK_STAFF_ROLES, RESET_CLEAR_SIGNUPS
from scheduling.scheduling_helpers import (
    NO_PINGS, handle_click, render_schedule, suggest_deadline, parse_schedule_input, ScheduleInputError, is_manager, format_for_edit, group_signups
)


def _error_embed(title, description):
    return create_embed(
        title = f"⚠️ {title}",
        description = description,
        colour = discord.Colour.red()
    )

async def _load_schedule_for_manager(interaction):
    if not is_manager(interaction.user):
        await interaction.response.send_message(embed = _error_embed("No Permission", "Only staff with permissions can use this button"), ephemeral = True)
        return None
    row = get_schedule_by_message(str(interaction.message.id), str(interaction.guild_id))
    if not row:
        await interaction.response.send_message(embed = _error_embed("Schedule Not Found", "This schedule is no longer being tracked (the event may have been removed)"), ephemeral = True)
        return None
    return row


class ScheduleButton(discord.ui.Button):
    def __init__(self, label, style, row):
        super().__init__(label = label, style = style, custom_id = f"sched:{label}", row = row)
        
    async def callback(self, interaction: discord.Interaction):
        if self.label == EDIT:
            await open_edit_modal(interaction)
        elif self.label == RESET:
            await open_reset_modal(interaction)
        else:
            await handle_click(interaction, self.label)
        
class ScheduleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout = None)
        blurple = discord.ButtonStyle.primary
        gray = discord.ButtonStyle.secondary
        green = discord.ButtonStyle.success
        red = discord.ButtonStyle.danger
        
        for i, role in enumerate(DEADLOCK_STAFF_ROLES):
            self.add_item(ScheduleButton(role, green, 0 if i < 5 else 1))
        self.add_item(ScheduleButton(MAYBE, blurple, 1))    
        self.add_item(ScheduleButton(UNAVAILABLE, red, 1))    
        self.add_item(ScheduleButton(WITHDRAW, blurple, 1))    
        self.add_item(ScheduleButton(EDIT, gray, 2))    
        self.add_item(ScheduleButton(RESET, red, 2))    

class ScheduleModal(discord.ui.Modal, title = "Event Time Details"):
    def __init__(self, event, settings):
        super().__init__()
        self.event_id, self.event_name, self.event_ts = event[0], event[1], event[2]
        self.settings = settings
        
        self.call_time = discord.ui.TextInput(
            label = "Call Time (HH:MM)", default = settings["call_time"],
            placeholder = "09:00", min_length = 4, max_length = 5
        )
        self.broadcast_start = discord.ui.TextInput(
            label = "Broadcast Start (HH:MM)", default = settings["broadcast_start"],
            placeholder = "10:00", min_length = 4, max_length = 5
        )
        self.signup_deadline = discord.ui.TextInput(
            label = "Sign-up Deadline (DD-MM-YYYY HH:MM)",
            default = suggest_deadline(self.event_ts, settings) or None,
            placeholder = "25-12-2026 18:00", min_length = 12, max_length = 16
        )
        self.tz = discord.ui.TextInput(
            label = "Timezone (IANA)", default = settings["timezone"], placeholder = "America/Toronto"
        )
        for item in (self.call_time, self.broadcast_start, self.signup_deadline, self.tz):
            self.add_item(item)
            
    async def on_submit(self, interaction: discord.Interaction):
        try:
            call, start, deadline, tz_name = parse_schedule_input(self.event_ts, self.call_time.value, self.broadcast_start.value, self.signup_deadline.value, self.tz.value)
        except ScheduleInputError as e:
            embed = create_embed(
                title = f"⚠️ {e.title}",
                description = e.description, colour = discord.Colour.red()
            )  
            await interaction.response.send_message(embed = embed, ephemeral = True)
            return
       
        await interaction.response.defer(ephemeral = True)
        guild_id = str(interaction.guild_id)
       
        # Posts in configured channel, otherwise wherever command is used
        channel = interaction.channel
        if self.settings["schedule_channel_id"]:
            configured = interaction.guild.get_channel(int(self.settings["schedule_channel_id"]))
            if configured is not None:
                channel = configured

        ping_role_id = self.settings["ping_role_id"]
        calendar_url = self.settings["calendar_url"]
        mentions = NO_PINGS
        if ping_role_id:
            mentions = discord.AllowedMentions(everyone = False, users = False, roles = [discord.Object(id = int(ping_role_id))])
        
        content = render_schedule(self.event_name, self.event_ts, call, start, deadline, {}, ping_role_id, calendar_url)
        try:
            message = await channel.send(content, view = ScheduleView(), allowed_mentions = mentions)
        except discord.Forbidden:
            embed = create_embed(
                title = "⚠️ Can't Post Here",
                description = f"No permission to post in {channel.mention}",
                colour = discord.Colour.red()
            )    
            await interaction.followup.send(embed = embed, ephemeral = True)
            return
    
        create_schedule(
            self.event_id, guild_id, str(message.channel.id), str(message.id), call, start, deadline, tz_name, ping_role_id, calendar_url, str(interaction.user.id)
        )
        embed = create_embed(
            title = "✅ Schedule Posted",
            description = f"Sign-ups for **{self.event_name}** are live: {message.jump_url}"
        )
        await interaction.followup.send(embed = embed, ephemeral = True)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        traceback.print_exception(Exception)
        embed = create_embed(
            title = "⚠️ Oops",
            description = "Schedule could not be created",
            colour = discord.Colour.red()
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed = embed, ephemeral = True)
        else:
            await interaction.response.send_message(embed = embed, ephemeral = True)
        

# View for !schedule variant
class OpenScheduleModalView(discord.ui.View):
    def __init__(self, author_id, event, settings):
        super().__init__(timeout = None)
        self.author_id = author_id
        self.event = event
        self.settings = settings
    
    @discord.ui.button(label = "Enter Schedule Details", style = discord.ButtonStyle.primary, emoji = "📝")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the person who ran the command can use this", ephemeral = True)
            return
        await interaction.response.send_modal(ScheduleModal(self.event, self.settings))


async def open_edit_modal(interaction: discord.Interaction):
    row = await _load_schedule_for_manager(interaction)
    if row is None:
        return
    await interaction.response.send_modal(EditScheduleModal(interaction.message.id, row))
    
class EditScheduleModal(discord.ui.Modal, title = "Edit Schedule Times"):
    def __init__(self, message_id, row):
        super().__init__()
        self.message_id = message_id
        (self.event_id, call, start, deadline, self.ping_role_id, self.calendar_url, self.event_name, self.event_ts, self.tz_name) = row
        self.title = f"Edit Times ({self.tz_name})"[:45]
        
        call_text, start_text, deadline_text = format_for_edit(call, start, deadline, self.tz_name)
        self.call_time = discord.ui.TextInput(label = "Call Time (HH:MM)", default = call_text, min_length = 4, max_length = 5)
        self.broadcast_start = discord.ui.TextInput(label = "Broadcast Time (HH:MM)", default = start_text, min_length = 4, max_length = 5)
        self.signup_deadline = discord.ui.TextInput(label = "Sign-up Deadline (DD-MM-YYYY HH:MM)", default = deadline_text, min_length = 12, max_length = 16)
        for item in (self.call_time, self.broadcast_start, self.signup_deadline):
            self.add_item(item)
        
    async def on_submit(self, interaction: discord.Interaction):
        try:
            call, start, deadline, _tz = parse_schedule_input(
                self.event_ts, self.call_time.value, self.broadcast_start.value, self.signup_deadline.value, self.tz_name
            )
        except ScheduleInputError as e:
            await interaction.response.send_message(embed = _error_embed(e.title, e.description), ephemeral = True)
            return
        
        guild_id = str(interaction.guild_id)
        update_schedule_times(str(self.message_id), guild_id, call, start, deadline)
        signups = group_signups(get_availability_by_event(self.event_id, guild_id))
        content = render_schedule(self.event_name, self.event_ts, call, start, deadline, signups, self.ping_role_id, self.calendar_url)
        await interaction.response.edit_message(content = content, allowed_mentions = NO_PINGS)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        embed = _error_embed("Something Went Wrong", "The schedule could not be edited")
        if interaction.response.is_done():
            await interaction.followup.send(embed = embed, ephemeral = True)
        else:
            await interaction.response.send_message(embed = embed, ephemeral = True)
        raise error
    

async def open_reset_modal(interaction: discord.Interaction):
    row = await _load_schedule_for_manager(interaction)
    if row is None:
        return
    event_id, event_name = row[0], row[6]
    kept = "Everyone's sign-ups are deleted too" if RESET_CLEAR_SIGNUPS else "Sign-ups are kept, and will show again if you rebuild it"
    embed = create_embed(
        title = "⚠️ Reset Schedule?",
        description = f"This deletes the sign-up sheet for **{event_name}**. {kept}\nYou can rebuild it with `/buildschedule <Event Name>`"
    )
    view = ResetConfirmView(interaction.user.id, interaction.message, event_id, event_name)
    await interaction.response.send_message(embed = embed, view = view, ephemeral = True)

class ResetConfirmView(discord.ui.View):
    def __init__(self, user_id, message, event_id, event_name):
        super().__init__(timeout = 60)
        self.user_id = user_id
        self.message = message
        self.event_id = event_id
        self.event_name = event_name
    
    @discord.ui.button(label = "Yes, reset", style = discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the person who pressed 'Reset' can confirm this", ephemeral = True)
            return
        
        guild_id = str(interaction.guild_id)
        if RESET_CLEAR_SIGNUPS:
            delete_schedule_data_for_event(self.event_id, guild_id)
        else:
            delete_schedule_by_event(self.event_id, guild_id)
        
        post_deleted = True
        try:
            await self.message.delete()
        except discord.NotFound:
            pass
        except discord.HTTPException:
            post_deleted = False
            
        note = "" if post_deleted else "\nCouldn't delete the post itself, so please remove it manually"
        embed = create_embed(
            title = "✅ Schedule Reset",
            description = f"**{self.event_name}** can now be rebuilt with `/buildschedule`{note}"
        )
        await interaction.response.edit_message(embed = embed, view = None)
        self.stop()
        
    @discord.ui.button(label = "Cancel", style = discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the person who pressed 'Reset' can cancel this", ephemeral = True)
            return
        embed = create_embed(
            title = "Cancelled",
            description = "The event sign-up was left as is"
        )
        await interaction.response.edit_message(embed = embed, view = None)
        self.stop()
        
def _message_button_ids(message):
    return {
        child.custom_id
        for row in message.components
        for child in getattr(row, "children", [])
        if getattr(child, "custom_id", None)
    }
    
async def refresh_schedule_posts(bot):
    wanted_ids = {item.custom_id for item in ScheduleView().children}
    refreshed = 0
    for (event_id, guild_id, channel_id, message_id, call, start, deadline, ping_role_id, calendar_url, name, event_ts) in get_active_schedules(int(time.time()) - 86400):
        try:
            channel = bot.get_channel(int(channel_id)) or await bot.fetch_channel(int(channel_id))
            message = await channel.fetch_message(int(message_id))
            signups = group_signups(get_availability_by_event(event_id, guild_id))
            content = render_schedule(name, event_ts, int(call), int(start), int(deadline), signups, ping_role_id, calendar_url)
            if _message_button_ids(message) == wanted_ids and message.content == content:
                continue
            await message.edit(content = content, view = ScheduleView(), allowed_mentions = NO_PINGS)
            refreshed += 1
            await asyncio.sleep(1)
        except (discord.NotFound, discord.Forbidden):
            continue
        except discord.HTTPException as e:
            print(f"Could not refresh schedule post {message}: {e}")
    return refreshed