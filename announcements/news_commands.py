import discord
from discord.ext import commands
from common.bot_launch import bot
from common.embed import create_embed_with_footer, create_embed

# Uses !post for command -- Bot takes input message, posts it, and removes original command
@bot.hybrid_command(description = "Announcement/news posts")  
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def post(ctx, *, message: str):
    embed = create_embed_with_footer(
        title = "📢 Announcement", 
        description = message
    )
    await ctx.send(embed = embed, content = "")
    if ctx.interaction is None:
        await ctx.message.delete()
    
@post.error
async def post_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure to include a message in the post",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)