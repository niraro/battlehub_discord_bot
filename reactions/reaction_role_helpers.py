import re

MESSAGE_LINK_REGEX = re.compile(r"discord\.com/channels/(\d+)/(\d+)/(\d+)")

def parse_message_link(link):
    match = MESSAGE_LINK_REGEX.search(link)
    return match.groups() if match else None