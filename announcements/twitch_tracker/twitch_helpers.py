import discord
import re
import time
from common.embed import create_embed_with_footer

TWITCH_PURPLE = discord.Colour.from_str("#9146FF")
DEFAULT_TEMPLATE = "🔴 {name} is now live on Twitch!"
STYLES = ("embed", "message")
_LOGIN_RE = re.compile(r"^[a-z0-9_]{1,25}$")

def parse_twitch_login(text):
    text = (text or "").strip().lower()
    text = re.sub(r"^https?://", "", text)
    text = re.sub(r"^(www\.|m\.)?twitch\.tv/", "", text)
    text = text.split("/")[0].split("?")[0].lstrip("@")
    return text if _LOGIN_RE.match(text) else None

def stream_url(login):
    return f"https://www.twitch.tv/{login}"

def render_template(template, values):
    text = template or DEFAULT_TEMPLATE
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text

def format_duration(seconds):
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes = rest // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m" if minutes else "under a minute"

def _thumbnail(stream):
    url = stream.get("thumbnail_url")
    if not url:
        return None
    return url.replace("{width}", "1280").replace("{heigh}", "720") + f"?t={int(time.time())}"

def build_live_message(track, stream):
    url = stream_url(track["login"])
    values = {
        "name": discord.utils.escape_markdown(track["display_name"]),
        "title": discord.utils.escape_markdown(stream.get("title") or ""),
        "game": discord.utils.escape_markdown(stream.get("game_name") or "Unknown"),
        "viewers": stream.get("viewer_count", 0),
        "url": url,
    }
    text = render_template(track["message_template"], values)
    
    if track["style"] == "message":
        return {"content": f"{text}\n{url}"[:2000]}
    
    embed = create_embed_with_footer(
        title = (stream.get("title") or "Live on Twitch")[:256],
        description = text[:4096],
        colour = TWITCH_PURPLE
    )
    embed.url = url
    embed.add_field(name = "Game", value = values["game"][:1024], inline = True)
    embed.add_field(name = "Viewers", value = str(values["viewers"]), inline = True)
    image = _thumbnail(stream)
    if image:
        embed.set_image(url = image)
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label = "Watch on Twitch", style = discord.ButtonStyle.link, url = url))
    return {"embed": embed, "view": view}

def build_end_message(track, started_at, ended_at):
    name = track["display_name"]
    duration = f" Broadcast was live for: {format_duration(ended_at - started_at)}." if started_at else ""
    if track["style"] == "message":
        text = f"⚫ **{discord.utils.escape_markdown(name)}** has finished the broadcast. {duration}"
        return {"content": text, "embeds": []}
    embed = create_embed_with_footer(
        title = f"⚫ {name} was live",
        description = f"The broadcast has ended. {duration}"
    )
    return {"embed": embed}