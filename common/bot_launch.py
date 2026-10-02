import discord
from discord.ext import commands

# Intents tell discord what info the bot is allowed to receive
intents = discord.Intents.default()
# Needed to read message text
intents.message_content = True
intents.members = True
intents.presences = True 

#Adding prefix to trigger bot (e.g. !post)
bot = commands.Bot(command_prefix = "!", intents = intents)