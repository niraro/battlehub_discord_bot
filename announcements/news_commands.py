from discord.ext import commands
from common.bot_launch import bot
from common.embed import create_embed
from common.error_handlers import handle_error
from announcements.post_views import PostModal, OpenPostModal

# Uses !post for command -- Bot takes input message, posts it, and removes original command
@bot.hybrid_command(description = "Announcement/news posts")  
@commands.has_any_role("The Big Cheeses", "Server Guardians", "Admin", "Mod")
@commands.guild_only()
async def post(ctx):
    if ctx.interaction is not None:
        await ctx.interaction.response.send_modal(PostModal())
    else:
        embed = create_embed(
            title = "📝 New Post",
            description = "Click the button below to write your post"
        )
        await ctx.send(embed = embed, view = OpenPostModal(ctx.author.id))
    
@post.error
async def post_error(ctx, error):
    await handle_error(ctx, error, "Check the options you entered, then try again")