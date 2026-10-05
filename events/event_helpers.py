import re
from zoneinfo import ZoneInfo
from database.events_db import get_all_events


DATE_REGEX = re.compile(r"^\d{2}-\d{2}-\d{4}$")
TIME_REGEX = re.compile(r"^\d{2}:\d{2}$")

# !addevent pattern detector of an unquoted mult-word event name. Pushes a valid date/time/timezone one slot to the right
def looks_like_shifted_args(time_str, tz_name):
    if not DATE_REGEX.match(time_str):
        return False
    parts = tz_name.split(maxsplit = 1)
    if len(parts) != 2:
        return False
    time_part, tz_part = parts
    if not TIME_REGEX.match(time_part):
        return False
    try:
        ZoneInfo(tz_part)
    except Exception as e:
        return False
    return True

def get_event_from_list(name, guild_id):
    events = get_all_events(guild_id)
    for event in events:
        if event[1].lower() == name.lower():
            return event
    return None