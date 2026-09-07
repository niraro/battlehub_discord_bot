# TEMPORARY FOR NOW, WILL DECIDE TO KEEP OR REMOVE THIS AT A LATER TIME
import discord
from embed import create_embed


# Turns message ID to corresponding emoji role ID
REACTION_ROLE_MESSAGES = {}

async def test_reaction_role(ctx, head_coach: discord.Role, hallo: discord.Role):
    embed = create_embed(
        title = "Test Reaction Role",
        description = "React ✅ to get `Head Coach` role, ❌ to get `Hallo` role"
    )
    message = await ctx.send(embed = embed)
    await message.add_reaction("✅")
    await message.add_reaction("❌")
    
    REACTION_ROLE_MESSAGES[message.id] = {"✅": head_coach.id, "❌": hallo.id}
    
async def react_role(bot, payload, adding: bool):
    if payload.message_id not in REACTION_ROLE_MESSAGES:
        return
    role_map = REACTION_ROLE_MESSAGES[payload.message_id]
    emoji = str(payload.emoji)
    if emoji not in role_map:
       return
   
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member is None or member.bot:
        return
    role = guild.get_role(role_map[emoji])
    if role is None:
        return
    if adding:
        await member.add_roles(role, reason = "Reaction Role")
    else:    
        await member.remove_roles(role, reason = "Reaction Role")