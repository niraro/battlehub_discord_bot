import discord
from discord.ext import commands
from datetime import datetime
from common.bot_launch import bot
from common.embed import create_embed
from common.error_handlers import error_embed, handle_error
from common.general_helpers import get_zone, normalise_zone_name, is_abbreviation, get_timezone_choices, discord_timestamp

# Uses !timeconvert for command -- Converts given date and time to Discord-formatted unix timestamp
@bot.hybrid_command(description = "Converts date and time to Discord-formatted unix timestamp")  
@discord.app_commands.describe(
    date = "DD-MM-YYYY",
    time = "HH:MM (24-hour)",
    timezone = "An abbreviation (EST, CET, etc) or an IANA name (America/Toronto, Europe/Berlin, etc)"
)
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def timeconvert(ctx, date: str, time: str, timezone: str):
    zone = get_zone(timezone)
    if zone is None:
        await ctx.send(embed = error_embed("Invalid Timezone", "Use an abbreviation like `EST` or `CET`, or an IANA name like `America/Toronto` or `Europe/Berlin`"), ephemeral = True)
        return
    
    try:
        naive = datetime.strptime(f"{date.strip()} {time.strip()}", "%d-%m-%Y %H:%M")
    except ValueError:
        await ctx.send(embed = error_embed("Invalid Date/Time", "Use `DD-MM-YYYY` for the date, and `HH:MM` for the time (E.g. `08-10-2026` `18:00`)"), ephemeral = True)
        return
    
    aware = naive.replace(tzinfo = zone)
    try:
        unix = int(aware.timestamp())
    except(OverflowError, OSError, ValueError):
        await ctx.send(embed = error_embed("Invalid Date", "That data is out of the supported range"), ephemeral = True)
        return
    
    notes = []
    shifted = datetime.fromtimestamp(unix, zone)
    if shifted.replace(tzinfo = None) != naive:
        notes.append(f"`{naive:%H:%M}` doesn't exist on that date because clocks skip forward, so it was read as `{shifted:%H:%M}`")
        aware = shifted
    elif aware.replace(fold = 1).utcoffset() != aware.utcoffset():
        notes.append("That time happens twice on that date because clocks go back. The first occurence was used")
    
    zone_name = normalise_zone_name(timezone)
    actual = aware.tzname()
    if is_abbreviation(timezone) and actual != zone_name:
        notes.append(f"`{zone_name}` isn't in effect on that date. That region is on `{actual}` then, so that was used")
    
    offset = aware.strftime("%z")
    description = (
        f"{discord_timestamp(unix, 'F')} ({discord_timestamp(unix, 'R')}) converted to Discord format: `{discord_timestamp(unix, 'F')}` `{discord_timestamp(unix, 'R')}`\n\n"
        f"**Interpreted as:** {aware:%d-%m-%Y %H:%M} {actual} (UTC{offset[:3]}:{offset[3:]})"
    )
    if notes:
        description += "\n\n" + "\n".join(f"⚠️ {n}" for n in notes)
    await ctx.send(embed = create_embed(title = "🕐 Timestamp Converter", description = description), ephemeral = True)

@timeconvert.autocomplete("timezone")
async def timeconvert_timezone_autocomplete(interaction: discord.Interaction, current: str):
    return [discord.app_commands.Choice(name = label, value = value) for label, value in get_timezone_choices(current)]
   
@timeconvert.error
async def timeconvert_error(ctx, error):
    await handle_error(ctx, error, "Make sure the format is `<DD-MM-YYYY> <HH:MM> <Timezone>`")