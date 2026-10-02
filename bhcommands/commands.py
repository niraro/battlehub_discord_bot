import discord
from discord.ext import commands
from common.bot_launch import bot
from common.embed import create_embed
from bhcommands.command_helpers import build_command_page
from bhcommands.command_views import CommandPageView

# Uses command !bhcommands -- Allows user to view the bot's command list
@bot.hybrid_command(description = "Shows commands of different features")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def bhcommands(ctx):
    view = CommandPageView(ctx)
    embed = build_command_page(0)
    await ctx.send(embed = embed, view = view, ephemeral = True)
    
@bhcommands.error
async def bhcommands_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)