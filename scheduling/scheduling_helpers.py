import discord
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from common.embed import create_embed
from database.scheduling_db import get_availability_by_event, get_broadcast_settings, get_schedule_by_message, get_user_roles, add_signup, remove_signups
import scheduling.scheduling_config as schedule

NO_PINGS = discord.AllowedMentions.none()

def load_settings(guild_id):
    row = get_broadcast_settings(guild_id)
    if not row:
        return dict(schedule.DEFAULT_SETTINGS)
    return dict(zip(schedule.SETTINGS_KEYS, row))

def get_zone(tz_name):
    try:
        return ZoneInfo(tz_name.strip())
    except Exception:
        return None
    
def parse_time(text):
    return datetime.strptime(text.strip(), "%H:%M").strftime("%H:%M")

def suggest_deadline(event_ts, settings):
    tz = get_zone(settings["timezone"]) or ZoneInfo("UTC")
    try:
        event_date = datetime.fromtimestamp(event_ts, tz).date()
        call_t = datetime.strptime(settings["call_time"], "%H:%M").time()
        call_ts = datetime.combine(event_date, call_t, tzinfo = tz).timestamp()
        deadline = datetime.fromtimestamp(call_ts - settings["sign_up_deadline"] * 3600, tz)
        return deadline.strftime("%d-%m-%Y %H:%M")
    except ValueError:
        return ""
    
class ScheduleInputError(Exception):
    def __init__(self, title, description):
        super().__init__(description)
        self.title = title
        self.description = description
        
def parse_schedule_input(event_ts, call_text, start_text, deadline_text, tz_text):
    tz = get_zone(tz_text)
    if tz is None:
        raise ScheduleInputError(
            "Invalid Timezone",
            "Make sure the timezone entered is an IANA Timezone name (E.g. \"America/Edmonton\", \"Europe/Berlin\", etc)"
        )
    try:
        event_date = datetime.fromtimestamp(event_ts, tz).date()
        call_t = datetime.strptime(call_text.strip(), "%H:%M").time()
        start_t = datetime.strptime(start_text.strip(), "%H:%M").time()
        call = int(datetime.combine(event_date, call_t, tzinfo = tz).timestamp())
        start = int(datetime.combine(event_date, start_t, tzinfo = tz).timestamp())
        deadline = int(datetime.strptime(deadline_text.strip(), "%d-%m-%Y %H:%M").replace(tzinfo = tz).timestamp())
    except ValueError:
        raise ScheduleInputError(
            "Invalid Date/Time",
            "Use `HH:MM` format for times, and `DD-MM-YYYY format for dates"
        )
    if call > start:
        raise ScheduleInputError("Call time must be earlier or same time as broadcast start")
    if deadline > call:
        raise ScheduleInputError("Sign-up deadline must be before call time")
    return call, start, deadline, tz_text.strip()


def _ts(unix, style = "F"):
    return f"<t:{unix}:{style}>"

def render_schedule(name, event_ts, call, start, deadline, signups, ping_role_id = None, calendar_url = None):
    lines = []
    lines += [
        f"## 📋**{name}**",
        f"**Event Date:** {_ts(event_ts, 'D')}",
        f"**Call Time:** {_ts(call)}",
        f"**Broadcast Start:** {_ts(start)}",
        f"**Sign-up Deadline:** {_ts(deadline)} ({_ts(deadline, 'R')})",
        "",
        f"## __**Staff Sign-up:**__",
    ]
    for role in schedule.DISPLAY_ORDER:
        people = signups.get(role, [])
        names = ", ".join(f"<@{u}>" for u in people) if people else "-"
        lines.append(f"**{role}:** {names}")
    lines += ["", "*Click a role to sign up. Click again to withdraw"]
    if ping_role_id:
        lines.append(f"<@&{ping_role_id}>")
    if time.time() > deadline:
        lines.append("🔒 *Sign-ups are closed*")
    if calendar_url:
        lines.append(f"[View Calendar](<{calendar_url}>)")
    content = "\n".join(lines)
    if len(content) > 2000:
        content = content[:1900] + "..."
    return content

def group_signups(entries):
    signups = {}
    for discord_id, role, status, note in entries:
        signups.setdefault(role, []).append(discord_id)
    return signups

def format_settings(settings):
    channel = f"<#{settings['schedule_channel_id']}>" if settings["schedule_channel_id"] else "Wherever command is used"
    role = f"<@&{settings['ping_role_id']}>" if settings["ping_role_id"] else "None"
    return(
        f"**Call Time:** {settings['call_time']}\n"
        f"**Broadcast Start:** {settings['broadcast_start']}\n"
        f"**Sign-up Deadline:** {settings['sign_up_deadline']}h before event call time\n"
        f"**Timezone:** {settings['timezone']}\n"
        f"**Ping Role:** {role}\n"
        f"**Calendar Link:** {settings['calendar_url'] or 'None'}"
    )

def describe_entry(event_name, role, status, note):
    label = schedule.STATUS_LABEL.get(status, status)
    if role in (schedule.UNAVAILABLE, schedule.MAYBE):
        text = f"**{event_name}** | {label}"
    else:
        text = f"**{event_name}** ({role}) | {label}"
    return text + (f" _({note})_" if note else "")

async def _build_availability_breakdown(ctx_or_interaction, event, guild_id):
    entries = get_availability_by_event(event[0], guild_id)
    if not entries:
        return create_embed(
            title = f"📋 Staff Availability — **{event[1]}**",
            description = "No sign-ups yet"
        )
    
    grouped = {}
    for discord_id, role, status, note in entries:
        grouped.setdefault(role, []).append((discord_id, status, note))
    
    lines = []
    for role in schedule.DISPLAY_ORDER:
        responses = grouped.get(role)
        if not responses:
            continue
        lines.append(f"**{role}**")
        for discord_id, note, in responses:
            member = ctx_or_interaction.guild.get_member(int(discord_id))
            name = member.display_name if member else f"Unknown member: `{discord_id}`"
            note_text = f"_({note}_)" if note else ""
            lines.append(f"{name} | {note_text}")
        lines.append("")
    return create_embed(
        title = f"📋 Staff Availability | **{event[1]}**",
        description = "\n".join(lines).strip()
    )

def is_manager(member):
    return any(role.name in schedule.EDIT_AND_RESET_ROLES for role in getattr(member, "roles", []))

def format_for_edit(call, start, deadline, tz_name):
    tz = get_zone(tz_name) or ZoneInfo("UTC")
    return (
        datetime.fromtimestamp(int(call), tz).strftime("%H:%M"),
        datetime.fromtimestamp(int(start), tz).strftime("%H:%M"),
        datetime.fromtimestamp(int(deadline), tz).strftime("%d-%m-%Y %H:%M"),
    )
    
async def handle_click(interaction, action):
    guild_id = str(interaction.guild.id)
    row = get_schedule_by_message(str(interaction.message.id), guild_id)
    if not row:
        embed = create_embed(
            title = "⚠️ Schedule Not Found",
            description = "This schedule is no longer being tracked (event may have been removed)",
            colour = discord.Colour.red()
        )
        await interaction.response.send_message(embed = embed, ephemeral = True)
        return
    event_id, call, start, deadline, ping_role_id, calendar_url, name, event_ts, _tz = row
    
    if time.time() > deadline and action not in (schedule.UNAVAILABLE, schedule.WITHDRAW):
        embed = create_embed(
            title = "🔒 Sign-ups Closed",
            description = "You can still `Withdraw` or set yourself as `Unavailable`",
            colour = discord.Colour.red()
        )
        await interaction.response.send_message(embed = embed, ephemeral = True)
        return
    
    uid = str(interaction.user.id)
    mine = get_user_roles(event_id, uid, guild_id)
    
    if schedule.REQUIRE_DISCORD_ROLE and action in schedule.DEADLOCK_STAFF_ROLES and action not in mine:
        required = schedule.ROLE_REQUIREMENT.get(action)    
        if required:
            names = [required] if isinstance(required, str) else list(required)
            wanted = {n.lower() for n in names}
            shown = " or ".join(f"`{n}`" for n in names)

            if not any(r.name.lower() in wanted for r in interaction.guild.roles):
                embed = create_embed(
                    title = "⚠️ Role Not Found",
                    description = f"The {shown} role doesn't exist in this server. Sign-ups cannot be checked for it",
                    colour = discord.Colour.red()
                )
                await interaction.response.send_message(embed = embed, ephemeral = True)
                return
            if not any(r.name.lower() in wanted for r in interaction.user.roles):
                embed = create_embed(
                    title = "⚠️ Role Mismatch",
                    description = f"You do not have the `{shown}` role",
                    colour = discord.Colour.red()
                )
                await interaction.response.send_message(embed = embed, ephemeral = True)
                return
        
    if action == schedule.WITHDRAW:
        remove_signups(event_id, uid, guild_id)
    elif action == schedule.UNAVAILABLE:
        if schedule.UNAVAILABLE in mine:
            remove_signups(event_id, uid, guild_id, [schedule.UNAVAILABLE])
        else:
            remove_signups(event_id, uid, guild_id) # Removes all role sign-ups
            add_signup(event_id, uid, schedule.UNAVAILABLE, schedule.STATUS_UNAVAILABLE, guild_id)
    elif action == schedule.MAYBE:
        if schedule.MAYBE in mine:
            remove_signups(event_id, uid, guild_id, [schedule.MAYBE])
        else:
            remove_signups(event_id, uid, guild_id)
            add_signup(event_id, uid, schedule.MAYBE, schedule.STATUS_MAYBE, guild_id)
    else:
        if action in mine:
            remove_signups(event_id, uid, guild_id, [action])
        else:
            remove_signups(event_id, uid, guild_id, [schedule.UNAVAILABLE, schedule.MAYBE])
            add_signup(event_id, uid, action, schedule.STATUS_SIGNED_UP, guild_id)
            
    signups = group_signups(get_availability_by_event(event_id, guild_id))
    content = render_schedule(name, event_ts, call, start, deadline, signups, ping_role_id, calendar_url)
    await interaction.response.edit_message(content = content, allowed_mentions = NO_PINGS)
