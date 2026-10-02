import discord
from discord import app_commands
from discord.ext import commands
from common.bot_launch import bot
from common.embed import create_embed
from database.moderation_db import set_log_channel, add_honeypot_channel, remove_honeypot_channel
from moderation.logs_helpers import LOG_TYPES


@bot.hybrid_command(description = "Set channel for chosen log(s)")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
@app_commands.choices(log = LOG_TYPES)
async def setlogs(ctx, log: str, channel: discord.TextChannel):
    valid_types = [c.value for c in LOG_TYPES]
    if log not in valid_types:
        embed = create_embed(
            title = "⚠️ Invalid Log Type",
            description = f"Log does not exist. Make sure to choose one of: \n**`{'\n'.join(valid_types)}`**",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    set_log_channel(str(ctx.guild.id), log, str(channel.id))
    embed = create_embed(
        title = "✅ Log Channel Set ",
        description = f"**{log}** logs will now be documented in {channel.mention}"       
    )
    await ctx.send(embed = embed, ephemeral = True)

@setlogs.error
async def setlogs_error(ctx, error):      
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure to check log type and channel to track where to track logs",
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
        

@bot.hybrid_command(description = "Assign a honeypot channel")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def addhoneypot(ctx, channel: discord.TextChannel):
    add_honeypot_channel(str(ctx.guild.id), str(channel.id))
    embed = create_embed(
        title = "✅ Honeypot Set",
        description = f"{channel.mention} is now a honeypot channel"
    )
    await ctx.send(embed = embed, ephemeral = True)

@addhoneypot.error
async def addhoneypot_error(ctx, error):      
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure to include the channel name",
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


@bot.hybrid_command(description = "Remove a honeypot channel")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def removehoneypot(ctx, channel: discord.TextChannel):
    deleted = remove_honeypot_channel(str(ctx.guild.id), str(channel.id))
    if deleted:
        embed = create_embed(
            title = "🗑️ Honeypot channel removed",
            description = f"{channel.mention} is no longer a honeypot channel"
        )
    else:
        embed = create_embed(
            title = "⚠️ Honeypot Channel Not Found",
            description = f"{channel.mention} is not registered as a honeypot channel",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)

@removehoneypot.error
async def removehoneypot_error(ctx, error):      
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure to include the channel name",
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