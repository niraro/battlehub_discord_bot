import discord
from discord.ext import commands
from common.bot_launch import bot
from common.embed import create_embed
from database.welcome_db import set_welcome


@bot.hybrid_command(description = "Set a custom welcome message for new players in a chosen channel")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def setwelcomemessage(ctx, channel: discord.TextChannel, *, message: str):
    set_welcome(str(ctx.guild.id), str(channel.id), message)
    embed = create_embed(
        title = "✅ Welcome Message Set",
        description = f"New members will now be greeted in {channel.mention}"
    )
    await ctx.send(embed = embed, ephemeral = True)
    
@setwelcomemessage.error
async def setwelcomemessage_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure to include the channel name and the custom message",
            colour = discord.Colour.red()
        )
    elif  isinstance(error, commands.ChannelNotFound):
        embed = create_embed(
            title = "⚠️ Channel Not Found",
            description = "Make sure the chosen channel exists, and/or the bot can see the channel",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )     
    await ctx.send(embed = embed, ephemeral = True)