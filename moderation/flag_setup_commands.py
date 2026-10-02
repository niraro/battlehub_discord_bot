import discord
from discord import app_commands
from discord.ext import commands
from common.bot_launch import bot
from common.embed import create_embed
from database.moderation_db import add_flagged_term, remove_flagged_term, add_flagged_domain, remove_flagged_domain, add_scam_hash
from moderation.flagging_helpers import compute_phash


@bot.hybrid_command(description = "Add flagged terms to flag list")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def addflaggedterm(ctx, *, term: str):
    add_flagged_term(str(ctx.guild.id), term, str(ctx.author))
    embed = create_embed(
        title = "✅ Term Added",
        description = f"`{term}` will now be flagged"
    )
    await ctx.send(embed = embed, ephemeral = True)

@addflaggedterm.error
async def addflaggedterm_error(ctx, error):      
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Term(s)",
            description = "Don't forget to add a term that will get flagged",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )  
    await ctx.send(embed = embed, ephemeral = True)
    
    
@bot.hybrid_command(description = "Remove flagged terms from flag list")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def removeflaggedterm(ctx, *, term: str):
    deleted = remove_flagged_term(str(ctx.guild.id), term)
    if deleted:
        embed = create_embed(
            title = "🗑️ Term Removed",
            description = f"`{term}` will no longer be flagged"
        )
    else:
        embed = create_embed(
            title = "⚠️ Term Not Found",
            description = f"`{term}` cannot be found in the flagged terms list",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)

@removeflaggedterm.error
async def removeflaggedterm_error(ctx, error):      
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Term(s)",
            description = "Don't forget to remove a term that will no longer get flagged",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )   
    await ctx.send(embed = embed, ephemeral = True)    

    
@bot.hybrid_command(description = "Add a domain (e.g. google.com) to the link flagging list")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def addflaggeddomain(ctx, *, domain: str):
    add_flagged_domain(str(ctx.guild.id), domain, str(ctx.author))
    embed = create_embed(
        title = "✅ Domain Added",
        description = f"`{domain}` will now be flagged"
    )
    await ctx.send(embed = embed, ephemeral = True)
    
@addflaggeddomain.error
async def addflaggeddomain_error(ctx, error):      
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Domain",
            description = "Don't forget to add a domain that will get flagged",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )   
    await ctx.send(embed = embed, ephemeral = True)

    
@bot.hybrid_command(description = "Remove a domain (e.g. google.com) from the link flagging list")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def removeflaggeddomain(ctx, *, domain: str):
    deleted = remove_flagged_domain(str(ctx.guild.id), domain)
    if deleted:
        embed = create_embed(
            title = "🗑️ Domain Removed",
            description = f"`{domain}` will no longer get flagged"
        )
    else:
        embed = create_embed(
            title = "⚠️ Domain Not Found",
            description = f"`{domain}` could not be found in the list",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)
    
@removeflaggeddomain.error
async def removeflaggeddomain_error(ctx, error):      
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Term(s)",
            description = "Don't forget to add a domain name that will no longer get flagged",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )   
    await ctx.send(embed = embed, ephemeral = True)

    
@bot.tree.context_menu(name = "Blacklist Image(s)")
@app_commands.default_permissions(manage_messages = True)
@app_commands.checks.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def blacklist_image(interaction: discord.Interaction, message: discord.Message):
    if not message.attachments:
        await interaction.response.send_message("This message has no attachments", ephemeral = True)
        return
    
    added = 0
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image/"):
            image_bytes = await attachment.read()
            phash = compute_phash(image_bytes)
            add_scam_hash(str(interaction.guild.id), phash, str(interaction.user))
            added += 1
    await interaction.response.send_message(f"Blacklisted {added} image(s) from this message", ephemeral = True)
    
@blacklist_image.error
async def blacklist_image_error(interaction: discord.Interaction, error: app_commands.AppCommandError):    
    if isinstance(error, app_commands.errors.MissingAnyRole):
        await interaction.response.send_message("You do not have the perms to blacklist images", ephemeral = True)
