import discord
from discord.ext import commands
import traceback
from common.embed import create_embed


def error_embed(title, description):
    return create_embed(title = f"⚠️ {title}", description = description, colour = discord.Colour.red())

async def handle_error(ctx, error, missing_info_text):
    original = error
    while hasattr(original, "original"):
        original = original.original
        
    if isinstance(error, commands.MissingAnyRole):
        if ctx.interaction is None:
            await ctx.message.delete()
        else:
            await ctx.send("You don't have permission to use this command", ephemeral = True)
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = missing_info_text,
            colour = discord.Colour.red()
        )
    elif isinstance(original, commands.MemberNotFound):
        embed = create_embed(
            title = "⚠️ User Not Found",
            description = f"Couldn't find `{original.argument}`. Try adding an '@' in front of their name, or use their user ID",
            colour = discord.Colour.red()
        )
    else:
        traceback.print_exception(original)
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: {type(original).__name__}: {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)