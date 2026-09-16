# TEMPORARY FOR NOW, WILL DECIDE TO KEEP OR REMOVE THIS AT A LATER TIME
import discord
import re
from embed import create_embed

MESSAGE_LINK_REGEX = re.compile(r"discord\.com/channels/(\d+)/(\d+)/(\d+)")

def parse_message_link(link):
    match = MESSAGE_LINK_REGEX.search(link)
    return match.groups() if match else None
