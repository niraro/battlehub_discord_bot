import discord
import time
import traceback
from discord.ext import tasks
from common.bot_launch import bot
from common.general_helpers import NO_PINGS
from database.twitch_db import get_all_twitch_tracks, set_announcement, mark_announced, clear_announcement
from announcements.twitch_tracker.twitch_api import twitch_client
from announcements.twitch_tracker.twitch_helpers import build_end_message, build_live_message

POLL_SECONDS = 60 # Change to 60 when testing is done
OFFLINE_GRACE_SECONDS = 300 # Change to 300 when testing is done
_offline_since = {}
LIVE_MENTIONS = discord.AllowedMentions(everyone = True, users = True, roles = True)

@tasks.loop(seconds = POLL_SECONDS)
async def poll_twitch():
    try:
        tracks = get_all_twitch_tracks()
        if not tracks:
            return
        ids = sorted({t["twitch_id"] for t in tracks})
        try:
            live = await twitch_client.get_streams(ids)
        except Exception as e:
            print(f"Twitch poll failed, keeping previous state: {e}")
            return
        now = int(time.time())
        for track in tracks:
            try:
                await _process_track(track, live.get(track["twitch_id"]), now)
            except Exception:
                traceback.print_exc()
    except Exception:
        traceback.print_exc()
        
@poll_twitch.before_loop
async def _before_poll():
    await bot.wait_until_ready()
    
def start_twitch_polling():
    if not poll_twitch.is_running():
        poll_twitch.start()
        

async def _process_track(track, stream, now):
    twitch_id = track["twitch_id"]
    if stream is not None:
        _offline_since.pop(twitch_id, None)
        if track["announced_stream_id"] != stream["id"]:
            if track ["announcement_message_id"]:
                await end_announcement(track, now)
            await _announce(track, stream)
    elif track["announcement_message_id"]:
        first_offline = _offline_since.setdefault(twitch_id, now)
        print(f"[twitch] track = {track['id']}, login = {track['login']}, twitch_id = {twitch_id!r}, offline_for = {now - first_offline}s")
        if now - first_offline >= OFFLINE_GRACE_SECONDS:
            await end_announcement(track, first_offline)
                
async def _announce(track, stream):
    channel = bot.get_channel(int(track["discord_channel_id"]))
    if channel is None:
        mark_announced(track["id"], stream["id"])
        print(f"Twitch: Discord channel {track['discord_channel_id']} not found for {track['login']}")
        return
    try:
        message = await channel.send(allowed_mentions = LIVE_MENTIONS, **build_live_message(track, stream))
    except (discord.Forbidden, discord.NotFound):
        mark_announced(track["id"], stream["id"])
        print(f"Twitch: no access to post in {track['discord_channel_id']} for {track['login']}")
        return
    except discord.HTTPException as e:
        print(f"Twitch: could not post announcement, will retry {e}")
        return
    set_announcement(track["id"], stream["id"], str(message.id), stream["started_at_ts"])
    
async def end_announcement(track, ended_at):
    channel = bot.get_channel(int(track["discord_channel_id"]))
    message = None
    if channel is not None:
        try:
            message = await channel.fetch_message(int(track["announcement_message_id"]))
        except (discord.NotFound, discord.Forbidden):
            message = None
        except discord.HTTPException:
            return
    if message is not None:
        try:
            await message.edit(view = None, allowed_mentions = NO_PINGS, **build_end_message(track, track["started_at"], ended_at))
        except discord.HTTPException as e:
            print(f"Twitch: could not edit announcement: {e}")
    clear_announcement(track["id"])
    