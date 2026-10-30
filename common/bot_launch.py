import discord
from discord.ext import commands

# Intents tell discord what info the bot is allowed to receive
intents = discord.Intents.default()
# Needed to read message text
intents.message_content = True
intents.members = True
intents.presences = True 

# Shutdown/Closer(s)
class BattleBot(commands.Bot):
    async def close(self):
        from announcements.twitch_tracker.twitch_api import twitch_client
        await twitch_client.close()
        await super().close()

#Adding prefix to trigger bot (e.g. !post)
bot = BattleBot(command_prefix = "!", intents = intents)