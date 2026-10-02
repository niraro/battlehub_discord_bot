import discord
from discord.ext import commands
from common.bot_launch import bot
from common.embed import create_embed
from database.moderation_db import get_timeout_count, get_timeout_history, get_flagged_terms, get_flagged_domains, list_honeypot_channels, get_all_log_settings


@bot.hybrid_command(description = "View current log channel configuration")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def viewlogs(ctx):
    settings = get_all_log_settings(str(ctx.guild.id))
    if not settings:
        embed = create_embed(
            title = "📋 Log Settings",
            description = "No log channels configured yet"
        )
    else:
        lines = [f"**{log}:** <#{channel_id}>" for log, channel_id in settings]
        embed = create_embed(
            title = "📋 Log Settings",
            description = "\n".join(lines)
        )
    await ctx.send(embed = embed, ephemeral = True)
    
@viewlogs.error
async def viewlogs_error(ctx, error):
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


@bot.hybrid_command(description = "List currently timed out users")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def timeoutlist(ctx):
    now = discord.utils.utcnow()
    active = [m for m in ctx.guild.members if m.timed_out_until and m.timed_out_until > now]
    if not active:
        embed = create_embed(
            title = "📋 Active Timeouts",
            description = "No users currently timed out"
        )
    else:
        lines = []
        for m in active:
            count = get_timeout_count(str(ctx.guild.id), str(m.id))
            lines.append(f"**{m}** timed out until: <t:{int(m.timed_out_until.timestamp())}:F> -- {count} total timeout(s)")
        embed = create_embed(
            title = "📋 Active Timeouts",
            description = "\n".join(lines)
        )
    await ctx.send(embed = embed, ephemeral = True)

@timeoutlist.error
async def timeoutlist_error(ctx, error):
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


@bot.hybrid_command(description = "Show a user's timeout history")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def timeouthistory(ctx, user: discord.Member):
    rows = get_timeout_history(str(ctx.guild.id), str(user.id))
    if not rows:
        embed = create_embed(
            title = f"📋 {user.display_name}'s Timeout History",
            description = "No timeouts on record"
        )
    else:
        lines = []
        for duration, reason, moderator_id, source, timestamp in rows:
            duration_label = f"{duration} seconds" if duration else "Unknown"
            mod_text = f"<@{moderator_id}>" if moderator_id else "Unknown"
            lines.append(f"<t:{timestamp}:F> | {duration_label} | {source} | Timed out by: {mod_text} | Reason: {reason or 'No reason given'}")
        embed = create_embed(
            title = f"📋 {user.display_name}'s Timeout History",
            description = "\n".join(lines)
        )
    await ctx.send(embed = embed, ephemeral = True)

@timeouthistory.error
async def timeouthistory_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Information",
            description = "Make sure to include the name of the user",
            colour = discord.Colour.red()
        )
    elif isinstance(error, commands.MemberNotFound):
        embed = create_embed(
            title = "⚠️ Invalid User",
            description = "User not in the server. Check for any typos, and ensure the user is in the server",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)    


@bot.hybrid_command(description = "List currently banned users")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def banlist(ctx):
    bans = [entry async for entry in ctx.guild.bans(limit = 25)]
    if not bans:
        embed = create_embed(
            title = "📋 Banned Users",
            description = "No bans on record"
        )
    else:
        lines = [f"**{b.user}** (`{b.user.id}`) | {b.reason or 'No reason given'}" for b in bans]
        embed = create_embed(
            title = "📋 Banned Users",
            description = "\n".join(lines)
        )
    await ctx.send(embed = embed, ephemeral = True)
    
@banlist.error
async def banlist_error(ctx, error):
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
    
    
@bot.hybrid_command(description = "View all flagged terms in the list")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def viewflaggedterms(ctx):
    terms = get_flagged_terms(str(ctx.guild.id))
    if not terms:
        embed = create_embed(
            title = "📋 Flagged Terms",
            description = "No terms currently in the list"
        )
    else:
        embed = create_embed(
            title = "📋 Flagged Terms",
            description = "\n".join(f"`{t}`" for t in terms)
        )
    await ctx.send(embed = embed, ephemeral = True)

@viewflaggedterms.error
async def viewflaggedterms_error(ctx, error):
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

    
@bot.hybrid_command(description = "View list of all flagged domains for this server")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def viewflaggeddomains(ctx):
    domains = get_flagged_domains(str(ctx.guild.id))
    if not domains:
        embed = create_embed(
            title = "📋 Flagged Domains",
            description = "No domains currently flagged"
        )
    else:
        embed = create_embed(
            title = "📋 Flagged Domains",
            description = "\n".join(f"`{d}`" for d in domains)
        )
    await ctx.send(embed = embed, ephemeral = True)
    
@viewflaggeddomains.error
async def viewflaggeddomains_error(ctx, error):
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

    
@bot.hybrid_command(description = "Lists all honeypot channels")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def honeypotlist(ctx,):
    channel_ids = list_honeypot_channels(str(ctx.guild.id))
    if not channel_ids:
        embed = create_embed(
            title = "📋 Honeypot Channel(s)",
            description = "No honeypot channels available yet"
        )
    else:
        embed = create_embed(
            title = "📋 Honeypot Channel(s)",
            description = "\n".join(f"<#{c}>" for c in channel_ids)
        )
    await ctx.send(embed = embed, ephemeral = True)
    
@honeypotlist.error
async def honeypotlist_error(ctx, error):
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
    
   
@bot.hybrid_command(description = "Unban a user")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def unban(ctx, user_id: str, *, reason: str = "No reason provided"):
    try:
        user = await bot.fetch_user(int(user_id))
    except (ValueError, discord.NotFound):
        await ctx.send(embed = create_embed(title = "⚠️ Invalid ID", colour = discord.Colour.red()), ephemeral = True)
        return
    try:
        await ctx.guild.unban(user, reason = reason)
    except discord.NotFound:
        embed = create_embed(
            title = "⚠️ Not Banned",
            description = f"`{user}` is not currently banned",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    embed = create_embed(
        title = "✅ Unbanned",
        description = f"**{user}** has been unbanned\n**Reason:** {reason}"
    )
    await ctx.send(embed = embed, ephemeral = True)
    
@unban.error
async def unban_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return 
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Information",
            description = "Make sure to include the user ID",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)        