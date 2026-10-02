import discord
from discord.ext import commands
from common.bot_launch import bot
from common.embed import create_embed
from database.reaction_roles_db import add_reaction_role_mapping, remove_reaction_role_mapping, list_reaction_role_mappings
from reactions.reaction_role_helpers import parse_message_link


@bot.hybrid_command(description = "Assign/remove roles based on message reaction(s)")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def addreactrole(ctx, message_link: str, emoji: str, add_role: discord.Role = None, remove_role: discord.Role = None, toggle: bool = False):
    if add_role is None and remove_role is None:
        embed = create_embed(
            title = "⚠️ Missing Role",
            description = "Specify an add_role, a remove_role, or both",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return

    parsed = parse_message_link(message_link)
    if parsed is None:
        embed = create_embed(
            title = "⚠️ Invalid Link",
            description = "Couldn't parse the message link",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    guild_id, channel_id, message_id = parsed
    
    channel = ctx.guild.get_channel(int(channel_id))
    if channel is None:
        embed = create_embed(
            title = "⚠️ Channel Not Found",
            description = "Couldn't find channel",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    try:
        message = await channel.fetch_message(int(message_id))
        await message.add_reaction(emoji)
    except discord.NotFound:
        embed = create_embed(
            title = "⚠️ Message Not Found",
            description = "Couldn't find message",
            colour = discord.Colour.red()
        ) 
        await ctx.send(embed = embed, ephemeral = True)
        return
    except discord.HTTPException:
        embed = create_embed(
            title = "⚠️ Invalid Emoji",
            description = "Emoji either not in server, or could not be found",
            colour = discord.Colour.red()
        ) 
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    add_reaction_role_mapping(
        str(ctx.guild.id), message_id, emoji,
        str(add_role.id) if add_role else None,
        str(remove_role.id) if remove_role else None,
        toggle
    )         
    
    embed = create_embed(
        title = "✅ Reaction Role Added",
        description = f"Reacting with {emoji} will now "
            + (f"add {add_role.mention} " if add_role else "") 
            + (f"and " if add_role and remove_role else "") 
            + (f"remove {remove_role.mention} " if remove_role else "") 
            + f"({'toggleable' if toggle else 'one-time'})"
    )
    await ctx.send(embed = embed, ephemeral = True)
    
@addreactrole.error
async def addreactrole_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Make sure to include the post's `Message Link`, and the `Emoji`. Optionally, add the role you want to users to receive/get removed, and whether it's toggleable or a one-time role add",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)      

    
@bot.hybrid_command(description = "Remove a role reaction mapping")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def removereactrole(ctx, message_link: str, emoji: str):
    parsed = parse_message_link(message_link)
    if parsed is None:
        embed = create_embed(
            title = "⚠️ Invalid Link",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    _, _, message_id = parsed
    deleted = remove_reaction_role_mapping(str(ctx.guild.id), message_id, emoji)
    if deleted:
        await ctx.send(embed = create_embed(title = "🗑️ Role Map Removed"), ephemeral = True)
    else:
        await ctx.send(embed = create_embed(title = "⚠️ Role Map Not Found", colour = discord.Colour.red()), ephemeral = True)
        
@removereactrole.error
async def removereactrole_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Don't forget to include the post's `Message Link`, and `Emoji`",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)  


@bot.hybrid_command(description = "List role reaction mappings for a message")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def listreactroles(ctx, message_link: str):
    parsed = parse_message_link(message_link)
    if parsed is None:
        embed = create_embed(
            title = "⚠️ Invalid Link",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    _, _, message_id = parsed
    rows = list_reaction_role_mappings(str(ctx.guild.id), message_id)
    if not rows:
        embed = create_embed(
            title = "📋 Reaction Roles",
            description = "No role-to-message mapping(s) configured yet"
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    lines = []
    for emoji, add_id, remove_id, toggle in rows:
        add_text = f"<@&{add_id}>" if add_id else "-"
        remove_text = f"<@&{remove_id}>" if remove_id else "-"
        lines.append(f"{emoji} -> Add: {add_text}, Remove: {remove_text} ({'toggle' if toggle else 'sticky'})")
    embed = create_embed(
        title = "📋 Reaction Roles",
        description = "\n".join(lines)
    )
    await ctx.send(embed = embed, ephemeral = True)
    
@listreactroles.error
async def listreactroles_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Don't forget to include the post's `Message Link`",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)