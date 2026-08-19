import discord

EMBED_COLOUR = discord.Colour.blurple() # placeholder colour, can change later as needed
FOOTER_TEXT = "BattleHub News"

def create_embed(title, description = None, colour = EMBED_COLOUR):
    embed = discord.Embed(
        title = title,
        description = description,
        colour = colour,
    )
    return embed

def create_embed_with_footer(title, description = None, colour = EMBED_COLOUR):
    embed = discord.Embed(
        title = title,
        description = description,
        colour = colour,
        timestamp = discord.utils.utcnow()
    )
    embed.set_footer(text = FOOTER_TEXT)
    return embed