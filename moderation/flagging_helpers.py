import discord
import re
import io
import time
import imagehash
from PIL import Image
from urllib.parse import urlparse
from common.embed import create_embed
from database.moderation_db import get_log_channel, get_flagged_terms, get_flagged_domains, get_scam_hash, create_pending_review
from moderation.moderation_views import FlaggedMessageView


URL_REGEX = re.compile(r'https?://[^\s<>"]+')

# Audit log for flagged messages/regular messages
def find_matched_terms(content, terms):
    if not content:
        return []
    lowered = content.lower()
    matched = []
    for term in terms:
        pattern = r'\b' + re.escape(term) + r'\b'
        if re.search(pattern, lowered):
            matched.append(term)
    return matched

async def scan_message_for_flags(bot, message):
    if message.author.bot:
        return
    if isinstance(message.channel, discord.DMChannel):
        return
    
    guild_id = str(message.guild.id)
    exempt_roles = {"Admin", "Mod", "The Big Cheeses", "Server Guardians"}
    if any(r.name in exempt_roles for r in message.author.roles):
        return
    terms = get_flagged_terms(guild_id)
    domains = get_flagged_domains(guild_id)
    
    matched_keywords = find_matched_terms(message.content, terms) if terms else []
    matched_domains = find_matched_domains(message.content, domains) if domains else []
    matched_images = await scan_image_for_flags(guild_id, message)
    if not matched_keywords and not matched_domains and not matched_images:
        return
    
    combined = (
        [f"Keyword: {t}" for t in matched_keywords] 
        + [f"Link: {d}" for d in matched_domains]
        + [f"Image: {m}" for m in matched_images]
    )
    await flagged_message(bot, message, combined)
    
async def flagged_message(bot, message, matched_terms):
    log_channel_id = get_log_channel(str(message.guild.id), "Message")
    if log_channel_id is None:
        return
    log_channel = bot.get_channel(int(log_channel_id))
    if log_channel is None:
        return
    
    author = message.author
    content = message.content
    channel = message.channel
    guild_id = str(message.guild.id)
    files = []
    embed_image_filename = None
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image/"):
            image_bytes = await attachment.read()
            file = discord.File(io.BytesIO(image_bytes), filename = attachment.filename)
            files.append(file)
            if embed_image_filename is None:
                embed_image_filename = attachment.filename
    
    try:
        await message.delete()
    except discord.NotFound:
        pass # Continues if it cannot find the user/message
    
    try:
       await author.send("One of your messages was flagged for staff review. You'll be notified of the outcome")
    except discord.Forbidden:
        pass # Message review still proceeds even if user can't be DM'd
    
    review_embed = create_embed(
        title = "🚩 Message Flagged",
        description = (
            f"**Author:** {author.mention} (`{author}`)\n"
            f"**Channel:** {channel.mention}\n"
            f"**Matched:** {', '.join(f'`{t}`' for t in matched_terms)}\n\n"
            f"**Original Message:**\n{content or '*No text content*'}"
        ),
        colour = discord.Colour.red()
    )
    if embed_image_filename:
        review_embed.set_image(url = f"attachment://{embed_image_filename}")
    exempt_roles = {"Admin", "Moderator"}
    mentions = [r.mention for r in message.guild.roles if r.name in exempt_roles]
    if mentions:
        await log_channel.send(f"🚨🚨 Message flagged! Need staff review! 🚨🚨 {' '.join(mentions)}")
    
    view = FlaggedMessageView()
    review_message = await log_channel.send(embed = review_embed, view = view, files = files)
    create_pending_review(guild_id, str(review_message.id), str(author.id), str(channel.id), content, ",".join(matched_terms), int(time.time()))

def extract_domains(content):
    if not content:
        return []
    domains = []
    for url in URL_REGEX.findall(content):
        try:
            netloc = urlparse(url).netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            domains.append(netloc)
        except Exception:
            continue
    return domains

def find_matched_domains(content, flagged_domains):
    found = extract_domains(content)
    return [d for d in found for flagged in flagged_domains if d == flagged or d.endswith("." + flagged)]

def compute_phash(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    return str(imagehash.phash(img))

def hash_distance(hash1, hash2):
    return imagehash.hex_to_hash(hash1) - imagehash.hex_to_hash(hash2)

def find_matching_hash(new_hash, stored_hashes, threshold = 8):
    for stored in stored_hashes:
        if hash_distance(new_hash, stored) <= threshold:
            return stored
    return None

async def scan_image_for_flags(guild_id, message):
    if not message.attachments:
        return []
    stored_hashes = get_scam_hash(guild_id)
    if not stored_hashes:
        return []
    
    matches = []
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image/"):
            image_bytes = await attachment.read()
            new_hash = compute_phash(image_bytes)
            if find_matching_hash(new_hash, stored_hashes):
                matches.append("Known scam or NSFW image")
    return matches