import discord
from discord.ext import commands
import time
from common.bot_launch import bot
from common.embed import create_embed
from database import tickets_db as db
from tickets.ticket_helpers import update_ticket_board

@bot.hybrid_command(description = "Sets channel for support tickets")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def setticketschannel(ctx, channel: discord.TextChannel):
    db.set_tickets_channel(str(ctx.guild.id), str(channel.id))
    embed = create_embed(
        title = "✅ Tickets Channel Set",
        description = f"New tickets will now appear in {channel.mention}"
    )
    await ctx.send(embed = embed, ephemeral = True)
    
@setticketschannel.error
async def setticketschannel_error(ctx, error):
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
    elif isinstance(error, commands.ChannelNotFound):
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


@bot.hybrid_command(description = "Reply to the user in the ticket thread")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def reply(ctx, *, message: str):
    if not isinstance(ctx.channel, discord.Thread):
        embed = create_embed(
            title = "⚠️ Wrong Channel",
            description = "This command only works in a ticket thread",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    ticket = db.get_ticket_by_thread(str(ctx.channel.id))
    if ticket is None:
        embed = create_embed(
            title = "⚠️ Invalid Ticket",
            description = "This thread is not linked to an open ticket",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    ticket_id, discord_id, status = ticket
    if status != "open":
        embed = create_embed(
            title = "⚠️ Ticket Closed",
            description = "This ticket is already closed",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    user = bot.get_user(int(discord_id))
    if user is None:
        embed = create_embed(
            title = "⚠️ User Not Found",
            description = "Could not find user of this ticket",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    dm_embed = create_embed(
        title = "💬 Staff",
        description = message
    )
    try:
        await user.send(embed = dm_embed)
    except discord.Forbidden:
        embed = create_embed(
            title = "⚠️ Message Not Delivered",
            description = "Could not send reply. User either has DMs disabled or has blocked the bot",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    db.update_ticket_activity(str(ctx.channel.id), int(time.time()))
    confirm_embed = create_embed(
        title = "✅ Reply Sent",
        description = message
    )
    await ctx.send(embed = confirm_embed, ephemeral = True)

@reply.error
async def reply_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original    

    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return    
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "Missing message in the reply",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)   

    
@bot.hybrid_command(description = "Closes ticket")
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
async def closeticket(ctx):
    if not isinstance(ctx.channel, discord.Thread):
        embed = create_embed(
            title = "⚠️ Wrong Channel",
            description = "This command only works in a ticket thread",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return     

    ticket = db.get_ticket_by_thread(str(ctx.channel.id))
    if ticket is None:
        embed = create_embed(
            title = "⚠️ Invalid Ticket",
            description = "This thread is not linked to an open ticket",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    ticket_id, discord_id, status = ticket
    if status != "open":
        embed = create_embed(
            title = "⚠️ Ticket Closed",
            description = "This ticket is already closed",
            colour = discord.Colour.red()
        )
        await ctx.send(embed = embed, ephemeral = True)
        return
    
    db.close_ticket(ticket_id)
    await update_ticket_board(bot, str(ctx.guild.id))
    user = bot.get_user(int(discord_id))
    if user is not None:
        close_embed = create_embed(
            title = "🔒 Ticket Closed",
            description = "Ticket has been closed by staff. DM again to open a new ticket",
            colour = discord.Colour.red()
        )
        try:
            await user.send(embed = close_embed)
        except discord.Forbidden:
            pass # Closes ticket even if user has closed DMs
    confirm_embed = create_embed(
            title = "🔒 Ticket Closed",
            description = "Ticket has been closed and archived",
            colour = discord.Colour.red()
    )
    await ctx.send(embed = confirm_embed)
    await ctx.channel.edit(archived = True, locked = True)

@closeticket.error
async def closeticket_error(ctx, error):
    original = error
    while hasattr(original, "original"):
        original = original.original
    
    if isinstance(error, commands.MissingAnyRole):
        await ctx.message.delete()
        return    
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed(
            title = "⚠️ Missing Info",
            description = "To close a ticket, use `/closeticket`",
            colour = discord.Colour.red()
        )
    else:
        embed = create_embed(
            title = "⚠️ Something Went Wrong",
            description = f"Unexpected Error: `{type(original).__name__}:` {original}",
            colour = discord.Colour.red()
        )
    await ctx.send(embed = embed, ephemeral = True)