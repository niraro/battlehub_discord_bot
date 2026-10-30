import discord
import asyncio
import time
import aiohttp
from discord import app_commands
from discord.ext import commands
from common.bot_launch import bot
from common.embed import create_embed
from common.error_handlers import handle_error, error_embed
from common.general_helpers import NO_PINGS
from database.twitch_db import get_guild_twitch_tracks, get_twitch_tracks_by_login, upsert_twitch_track, remove_twitch_track, mark_announced
from announcements.twitch_tracker.twitch_api import twitch_client, describe_twitch_error
from announcements.twitch_tracker.twitch_helpers import STYLES, DEFAULT_TEMPLATE, parse_twitch_login, build_live_message, build_end_message
from announcements.twitch_tracker.twitch_tasks import end_announcement, LIVE_MENTIONS


MAX_TRACKS_PER_GUILD = 25
MAX_TEMPLATE_LENGTH = 1500
STYLE_CHOICES = [
    app_commands.Choice(name = "Embed", value = "embed"),
    app_commands.Choice(name = "Plain Message", value = "message"),
]

async def tracked_channel_autocomplete(interaction: discord.Interaction, current: str):
    logins = sorted({t["login"] for t in get_guild_twitch_tracks(str(interaction.guild_id))})
    return [app_commands.Choice(name = l, value = l) for l in logins if current.lower() in l][:25]

@bot.hybrid_command(description = "Add Twitch channel(s) to track when live, in a specified Discord channel, with a custom message")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
@app_commands.choices(style = STYLE_CHOICES)
async def tracktwitch(ctx, twitch_channel: str, discord_channel: discord.TextChannel, style: str = None, *, message: str = None):
    login = parse_twitch_login(twitch_channel)
    if login is None:
        await ctx.send(embed = error_embed("Invalid Channel", "Use the channel name, or the `twitch.tv/...` link"), ephemeral = True)
        return
    style = style.lower() if style else None
    if style not in (None, *STYLES):
        await ctx.send(embed = error_embed("Invalid Style", f"Style must one of: {', '.join(f'`{s}`' for s in STYLES)}"), ephemeral = True)
        return
    message = message.strip() if message else None
    if message and len(message) > MAX_TEMPLATE_LENGTH:
        await ctx.send(embed = error_embed("Message Too Long", f"Custom messages can be up to `{MAX_TEMPLATE_LENGTH}` characters long"), ephemeral = True)
        return
    
    user_perms = discord_channel.permissions_for(ctx.author)
    bot_perms = discord_channel.permissions_for(ctx.guild.me)
    if not (user_perms.view_channel and user_perms.send_messages):
        await ctx.send(embed = error_embed("No Permission", f"You can't post in {discord_channel.mention}"), ephemeral = True)
        return
    if not (bot_perms.view_channel and bot_perms.send_messages and bot_perms.embed_links):
        await ctx.send(embed = error_embed("Can't Post", f"The `View Channels`, `Send Messages` and `Embed Links` are needed in {discord_channel.mention}"), ephemeral = True)
        return
    
    await ctx.defer(ephemeral = True)
    try:
        user = await twitch_client.get_user(login)
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        print(f"Twitch lookup failed ({type(e).__name__}): {describe_twitch_error(e)} | {e}")
        await ctx.send(embed = error_embed("Twitch Unavailable", "Couldn't reach Twitch. Try again in a moment"), ephemeral = True)
        return
    if user is None:
        await ctx.send(embed = error_embed("Channel Not Found", f"No Twitch channel named `{login}`"), ephemeral = True)
        return
    
    guild_id = str(ctx.guild.id)
    existing = get_guild_twitch_tracks(guild_id)
    is_new = not any(t["twitch_id"] == user["id"] and t["discord_channel_id"] == str(discord_channel.id) for t in existing)
    if is_new and len(existing) >= MAX_TRACKS_PER_GUILD:
        await ctx.send(embed = error_embed("Channel Limit Reached", f"This server can track up to `{MAX_TRACKS_PER_GUILD}` Twitch channels"), ephemral = True)
        return
    track_id, created = upsert_twitch_track(guild_id, user["id"], user["login"], user["display_name"], str(discord_channel.id), message, style, str(ctx.author))
    note = ""
    if created:
        try:
            stream = (await twitch_client.get_streams([user["id"]])).get(user["id"])
        except (aiohttp.ClientError, asyncio.TimeoutError):
            stream = None
        if stream:
            mark_announced(track_id, stream["id"])
            note = "\n\nThey're live right now, so this broadcast won't be announced. The next one will be announced"
            
    track = get_twitch_tracks_by_login(guild_id, user["login"], str(discord_channel.id))[0]
    embed = create_embed(
        title = "✅ Twitch Channel Added" if created else "✅ Twitch Track Updated",
        description = (
            f"**Channel:** {user['display_name']}\n"
            f"**Posts in:** {discord_channel.mention}\n"
            f"**Style:** `{track['style']}`\n"
            f"**Message:** {track['message_template'] or f'*Default:* {DEFAULT_TEMPLATE}'}"
            f"{note}"
        )
    )
    await ctx.send(embed = embed, ephemeral = True)
    
@tracktwitch.error
async def tracktwitch_error(ctx, error):
    await handle_error(ctx, error, "Make sure to follow the format `<Twitch Channel> <Discord Channel>`")


@bot.hybrid_command(description = "Remove a Twitch channel from the track list")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
@commands.guild_only()
async def untracktwitch(ctx, twitch_channel: str, discord_channel: discord.TextChannel = None):
    login = parse_twitch_login(twitch_channel)
    tracks = get_twitch_tracks_by_login(str(ctx.guild.id), login, str(discord_channel.id) if discord_channel else None) if login else []
    if not tracks:
        await ctx.send(embed = error_embed("Channel Not Tracked", f"{twitch_channel} is not being tracked here"), ephemeral = True)
        return
    await ctx.defer(ephemeral = True)
    now = int(time.time())
    for track in tracks:
        if track["announcement_message_id"]:
            await end_announcement(track, now)
        remove_twitch_track(track["id"])
    embed = create_embed(
        title = "🗑️ Twitch Channel Removed",
        description = f"`{login}` will no longer be announced when live"
    )
    await ctx.send(embed = embed, ephemeral = True)

untracktwitch.autocomplete("twitch_channel")(tracked_channel_autocomplete)
@untracktwitch.error
async def untracktwitch_error(ctx, error):
    await handle_error(ctx, error, "Make sure to include the Twitch channel name")


@bot.hybrid_command(description = "Show a list of tracked Twitch channel(s)")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
@commands.guild_only()
async def listtwitch(ctx):
    tracks = get_guild_twitch_tracks(str(ctx.guild.id))
    if not tracks:
        embed = create_embed(
            title = "📋 Tracked Twitch Channels",
            description = "No Twitch channels currently being tracked"
        )
    else:
        lines = [
            f"{'🔴' if t['announcement_message_id'] else '⚫'} **{t['display_name']}** -> <#{t['discord_channel_id']}> (`{t['style']}`)" for t in tracks
        ]
        embed = create_embed(
            title = "📋 Tracked Twitch Channels",
            description = "\n".join(lines) + "\n\n🔴 = Currently announced as live"
        )
    await ctx.send(embed = embed, ephemeral = True)
    
@listtwitch.error
async def listtwitch_error(ctx, error):
    await handle_error(ctx, error, "Something went wrong")
    

@bot.hybrid_command(description = "Preview how a tracked channel's go-live message will look like")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
@commands.guild_only()
async def twitchpreview(ctx, twitch_channel: str):
    login = parse_twitch_login(twitch_channel)
    tracks = get_twitch_tracks_by_login(str(ctx.guild.id), login) if login else []
    if not tracks:
        await ctx.send(embed = error_embed("Channel Not Tracked", "Track the channel first with `/tracktwitch`"), ephemeral = True)
        return
    await ctx.defer(ephemeral = True)
    now = int(time.time())
    sample = {
        "id": "preview", "title": "Deadlock grind: Solomon is best hero", "game_name": "Deadlock", "view_count": 69420, "thumbnail_url": None, "started_at_ts": now - 3725,
    }
    
    for style in STYLES:
        track = {**tracks[0], "style": style}
        await ctx.send(f"**{style.capitalize()}: live**", ephemeral = True)
        await ctx.send(allowed_mentions = LIVE_MENTIONS, ephemeral = True, **build_live_message(track, sample))
        await ctx.send(f"**{style.capitalize()}: after the broadcast ends**", ephemeral = True)
        await ctx.send(allowed_mentions = NO_PINGS, ephemeral = True, **build_end_message(track, sample["started_at_ts"], now))
        
twitchpreview.autocomplete("twitch_channel")(tracked_channel_autocomplete)
@twitchpreview.error
async def twitchpreview_error(ctx, error):
    await handle_error(ctx, error, "Make sure to include the Twitch channel name/link")