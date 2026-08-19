import discord
from bot_db import get_availability_by_event, upsert_availability, get_event_from_list
from embed import create_embed
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DATE_REGEX = re.compile(r"^\d{2}-\d{2}-\d{4}$")
TIME_REGEX = re.compile(r"^\d{2}:\d{2}$")

# !addevent pattern detector of an unquoted mult-word event name. Pushes a valid date/time/timezone one slot to the right
def looks_like_shifted_args(time_str, tz_name):
    if not DATE_REGEX.match(time_str):
        return False
    parts = tz_name.split(maxsplit = 1)
    if len(parts) != 2:
        return False
    time_part, tz_part = parts
    if not TIME_REGEX.match(time_part):
        return False
    try:
        ZoneInfo(tz_part)
    except Exception as e:
        return False
    return True


async def _set_availability(ctx, event_name, role, status, note):
    event = get_event_from_list(event_name, str(ctx.guild.id))
    if not event:
        embed = create_embed(
            title = "⚠️ Event Not Found", 
            description = f"**{event_name}** not found. Make sure event exists (check spelling, typos, etc)",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        return
    
    role_obj = discord.utils.find(lambda r: r.name.lower() == role.lower(), ctx.guild.roles)
    if not role_obj:
        embed = create_embed(
            title = "⚠️ Role Not Found",
            description = f"No role called `{role}`",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        return
    if role_obj not in ctx.author.roles:
        embed = create_embed(
            title = "⚠️ Role Mismatch",
            description = f"You do not have the `{role_obj.name}` role",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        return

    status = status.capitalize()
    if status not in ("Yes", "No", "Maybe"):
        embed = create_embed(
            title = "⚠️ Invalid Status",
            description = "Options are `Yes`, `No`, `Maybe` (caps matter)",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed)
        return
    upsert_availability(event[0], str(ctx.author.id), role_obj.name, status, note, str(ctx.guild.id))
    note_text = f"\nNote: {note}" if note else ""
    embed = create_embed(
        title = "✅ Availability Updated",
        description = f"Availability for **{event[1]}** as `{role_obj.name}` has been updated to: `{status}`\n_{note_text}_"
    )
    await ctx.send(embed = embed)
    await ctx.message.delete()


async def _build_availability_breakdown(ctx_or_interaction, event, guild_id):
    entries = get_availability_by_event(event[0], guild_id)
    if not entries:
        return create_embed(
            title = f"📋 Staff Availability — **{event[1]}**",
            description = "No staff currently available"
        )
    
    grouped = {}
    for discord_id, role, status, note in entries:
        grouped.setdefault(role, []).append((discord_id, status, note))
    
    lines = []
    for role, responses in  grouped.items():
        lines.append(f"**{role}**")
        for discord_id, status, note, in responses:
                member = ctx_or_interaction.guild.get_member(int(discord_id))
                name = member.display_name if member else f"Unknown member: `{discord}`"
                note_text = f"_({note}_)" if note else ""
                lines.append(f"{name} - {status} {note_text}")
        lines.append("")
    return create_embed(
        title = f"📋 Staff Availability — **{event[1]}**",
        description = "\n".join(lines).strip()
    )