from database.welcome_db import get_welcome

def render_welcome_message(template, member):
    return (
        template
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{server}", member.guild.name)
        .replace("{membercount}", str(member.guild.member_count))
    )

async def send_welcome(bot, member):
    settings = get_welcome(str(member.guild.id))
    if settings is None:
        return
    channel_id, template = settings
    channel = bot.get_channel(int(channel_id))
    if channel is None:
        return
    rendered = render_welcome_message(template, member)
    await channel.send(rendered)