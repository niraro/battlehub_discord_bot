import re
from zoneinfo import ZoneInfo


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