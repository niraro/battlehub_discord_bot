import discord
import time
from datetime import timedelta
from moderation.logs_helpers import find_audit_log_entry
import database.moderation_db as db


TIMEOUT_OPTIONS = [
    ("60 Seconds", 60),
    ("5 Minutes", 300),
    ("10 Minutes", 600),
    ("1 Hour", 3600),
    ("1 Day", 86400),
    ("1 Week", 604800),
]

async def review_decision(interaction, decision):
    review = db.get_pending_review(str(interaction.message.id))
    if review is None:
        await interaction.response.send_message("Couldn't find review", ephemeral = True)
        return
    
    review_id, guild_id, author_id, channel_id, content, matched_terms, status = review
    if status != "pending":
        await interaction.response.send_message("A staff member has already reviewed this flag", ephemeral = True)
        return
    db.set_review_status(review_id, decision)
    
    # Locks button regardless of outcome
    for item in interaction.message.components[0].children if interaction.message.components else []:
        pass
    
    disabled_view = discord.ui.View()
    updated_embed = interaction.message.embeds[0]
    updated_embed.colour = discord.Colour.green() if decision == "approved" else discord.Colour.red()
    updated_embed.add_field(
        name = "**Verdict:**",
        value = f"{decision.capitalize()} by {interaction.user.mention}",
        inline = False
    )
    await interaction.message.edit(embed = updated_embed, view = disabled_view)
    
    guild = interaction.client.get_guild(int(guild_id))
    member = guild.get_member(int(author_id)) if guild else None
    if decision == "approved":
        try:
            user = interaction.client.get_user(int(author_id))
            if user:
                await user.send("Your flagged message was reviewed and approved. You will not be timed out this time, but please be careful moving forward!")
        except discord.Forbidden:
            pass
        await interaction.response.send_message("Marked as approved", ephemeral = True)

async def block_decision(interaction, reason, message_id, duration_seconds):
    await interaction.response.defer(ephemeral = True)
    review = db.get_pending_review(str(message_id))
    if review is None:
        await interaction.followup.send("Couldn't find review", ephemeral = True)
        return
    
    review_id, guild_id, author_id, channel_id, content, matched_terms, status = review
    if status != "pending":
        await interaction.followup.send("A staff member has already reviewed this flag", ephemeral = True)
        return
    db.set_review_status(review_id, "blocked")
    
    guild = interaction.client.get_guild(int(guild_id))
    member = guild.get_member(int(author_id)) if guild else None
    duration_label = next((label for label, seconds in TIMEOUT_OPTIONS if seconds == duration_seconds), f"{duration_seconds} seconds")
    if member is None:
        result_note = "User no longer in the server"
    else:
        try:
            await member.timeout(discord.utils.utcnow() + timedelta(seconds = duration_seconds), reason = reason)
        except discord.Forbidden:
            pass
        try:
            await member.send(
                f"Your flagged message was reviewed and blocked.\n"
                f"**You have been timed out for {duration_label}**\n"
                f"**Reason:** {reason}"
            )
        except discord.Forbidden:
            pass
        result_note = ( 
                    f"**Blocked by:** {interaction.user.mention}\n"
                    f"**Timeout:** {duration_label}\n"
                    f"**Reason:** {reason}\n"
                    #f"**Current strike:** {new_count}/3"
        )
    log_channel_id = db.get_log_channel(guild_id, "Message")
    log_channel = interaction.client.get_channel(int(log_channel_id))
    review_msg = await log_channel.fetch_message(int(message_id))
    
    original_embed = review_msg.embeds[0]
    original_embed.colour = discord.Colour.red()
    original_embed.add_field(
        name = "**Verdict:**",
        value = result_note,
        inline = False
    )
    await review_msg.edit(embed = original_embed, view = discord.ui.View())
    await interaction.followup.send("Message blocked and logged", ephemeral = True)

async def strike_ban(interaction, staff_reason, message_id, origin):
    await interaction.response.defer(ephemeral = True)
    review = db.get_pending_review(str(message_id))
    if review is None:
        await interaction.followup.send("Couldn't find review", ephemeral = True)
        return
    review_id, guild_id, author_id, channel_id, content, matched_terms, status = review
    if status != "pending":
        await interaction.followup.send("A staff member has already reviewed this flag", ephemeral = True)
        return
    
    db.set_review_status(review_id, "blocked")
    if origin == "strike":
        combined_reason = f"3 strikes, you're out!\n**Staff note:** {staff_reason}"
    else:
        combined_reason = f"User Ban (Severe Rule Violation): {staff_reason}"
    guild = interaction.client.get_guild(int(guild_id))
    member = guild.get_member(int(author_id)) if guild else None
    if member is None:
        result_note = "User no longer in the server"
    else:
        try:
            await member.send(
                f"You have been banned for breaking server rules\n"
                f"**Reason:** {combined_reason}"
            )
        except discord.Forbidden:
            pass
        try:
            await guild.ban(member, reason = combined_reason)
        except discord.Forbidden:
            pass
        result_note = f"Banned by {interaction.user.mention}\nReason: {staff_reason}"
    
    log_channel_id = db.get_log_channel(guild_id, "Message")
    log_channel = interaction.client.get_channel(int(log_channel_id))
    review_msg = await log_channel.fetch_message(int(message_id))
    
    original_embed = review_msg.embeds[0]
    original_embed.colour = discord.Colour.red()
    original_embed.add_field(
        name = "**Verdict:**",
        value = result_note,
        inline = False
    )
    await review_msg.edit(embed = original_embed, view = discord.ui.View())
    await interaction.followup.send("User banned and logged", ephemeral = True)

async def timeout_update(bot, before, after):
    if before.timed_out_until == after.timed_out_until:
        return
    if after.timed_out_until is None or after.timed_out_until <= discord.utils.utcnow():
        return
    
    guild = after.guild
    entry = await find_audit_log_entry(guild, discord.AuditLogAction.member_update, after)
    duration_seconds = int((after.timed_out_until - discord.utils.utcnow()).total_seconds())
    reason = entry.reason if entry and entry.reason else None
    moderator_id = str(entry.user.id) if entry else None
    source = "flagged block" if entry and entry.user.id == bot.user.id else "manual"
    
    db.log_timeout(str(guild.id), str(after.id), duration_seconds, reason, moderator_id, source, int(time.time()))
