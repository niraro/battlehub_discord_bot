import discord
from discord.ext import commands
from common.bot_launch import bot
from common.embed import create_embed
from common.unix_timestamp import get_discord_timestamp

# Uses !timeconvert for command -- Converts given date and time to Discord-formatted unix timestamp
@bot.hybrid_command(description = "Converts date and time to Discord-formatted unix timestamp")  
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def timeconvert(ctx, date: str, time: str, timezone: str):
    try:
        unix_time, discord_format = get_discord_timestamp(f"{date} {time}", timezone)
        embed = create_embed(
            title = "🕐 Timestamp Converter",
            description = f"<t:{unix_time}:F> converted to Discord format: `{discord_format}`\n" 
        )
        await ctx.send(embed = embed, ephemeral = True)
    except Exception as e:
        error_embed = create_embed(
            title = "⚠️ Conversion Failed",
            description = f"Could not convert. Make sure the date format is `<DD-MM-YYYY>` `<HH:MM>` `<Timezone>`\n\nError: {e}",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = error_embed, ephemeral = True)
        
@timeconvert.error
async def timeconvert_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure the format is `<DD-MM-YYYY> <HH:MM> <Timezone>`",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)      