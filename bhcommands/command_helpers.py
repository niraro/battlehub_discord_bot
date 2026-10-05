from bhcommands.command_config import COMMAND_CATEGORIES
from common.embed import create_embed


def build_command_page(index):
    title, commands_list = COMMAND_CATEGORIES[index]
    embed = create_embed(title = f"📖 {title}")
    for name, note in commands_list:
        embed.add_field(
            name = f"**__{name}__**",
            value = f"{note}",
            inline = False
        )
    embed.set_footer(text = f"Page {index + 1}/{len(COMMAND_CATEGORIES)} | {title}")
    return embed