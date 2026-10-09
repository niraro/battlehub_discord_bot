import discord
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, available_timezones


NO_PINGS = discord.AllowedMentions.none()

# Commonly used abbreviation input gets converted to IANA as output
_REGION_ALIASES = {
    "EST": ("America/Toronto", "Eastern"), "EDT": ("America/Toronto", "Eastern"),
    "CST": ("America/Chicago", "Central"), "CDT": ("America/Chicago", "Central"),
    "MST": ("America/Denver", "Mountain"), "MDT": ("America/Denver", "Mountain"),
    "PST": ("America/Los_Angeles", "Pacific"), "PDT": ("America/Los_Angeles", "Pacific"),
    "AKST": ("America/Anchorage", "Alaska"), "AKDT": ("America/Anchorage", "Alaska"),
    "GMT": ("Europe/London", "UK"), "BST": ("Europe/London", "UK"),
    "CET": ("Europe/Berlin", "Central European"), "CEST": ("Europe/Berlin", "Central European"),
    "EET": ("Europe/Athens", "Eastern Europe"), "EEST": ("Europe/Athens", "Eastern Europe"),
    "AEST": ("Australia/Sydney", "Australian Eastern"), "AEDT": ("Australia/Sydney", "Australian Eastern"),
    "NZST": ("Pacific/Auckland", "New Zealand"), "NZDT": ("Pacific/Auckland", "New Zealand")
}

# Regions that don't utilise DST (Daylight Savings Time) include: Hawaii, India, Japan, Korea
_FIXED_OFFSETS = {
    "UTC": (0, "Coordinated Universal Time"), 
    "HST": (-10, "Hawaii"), 
    "IST": (5.5, "India"), 
    "JST": (9, "Japan"), 
    "KST": (9, "Korea"),
}

def _format_offset(hours):
    total = round(hours * 60)
    if total == 0:
        return "UTC"
    sign = "+" if total > 0 else "-"
    h, m = divmod(abs(total), 60)
    return f"UTC{sign}{h}" + (f":{m:02d}" if m else "")

_FIXED_ZONES = {name: timezone(timedelta(hours = hours), name) for name, (hours, _label) in _FIXED_OFFSETS.items()}

_ABBREVIATION_LABELS = {
    **{name: f"{name} - {label} ({region})" for name, (region, label) in _REGION_ALIASES.items()},
    **{name: f"{name} - {label} ({_format_offset(hours)})" for name, (hours, label) in _FIXED_OFFSETS.items()},
}

_IANA_LOOKUP = {name.lower(): name for name in available_timezones()}
_LEGACY_PREFIXES = ("Etc/", "US/", "Canada/", "Brazil/", "Chile/", "Mexico/", "SystemV/")
_IANA_CHOICE_NAMES = sorted(n for n in _IANA_LOOKUP.values() if "/" in n and not n.startswith(_LEGACY_PREFIXES))

# Checks abbreviations before IANA timezones incase legacy DST-aware (can give wrong time outputs)
def get_zone(tz_name):
    if not tz_name:
       return None
    key = tz_name.strip()
    upper = key.upper()
    try:
        if upper in _REGION_ALIASES:
            return ZoneInfo(_REGION_ALIASES[upper][0])
        if upper in _FIXED_ZONES:
            return _FIXED_ZONES[upper]
        return ZoneInfo(_IANA_LOOKUP.get(key.lower(), key))
    except Exception:
        return None
    
def normalise_zone_name(tz_name):
    if get_zone(tz_name) is None:
        return None
    key = tz_name.strip()
    if key.upper() in _REGION_ALIASES or key.upper() in _FIXED_ZONES:
        return key.upper()
    return _IANA_LOOKUP.get(key.lower(), key)

def is_abbreviation(tzname):
    key = (tzname or "").strip().upper()
    return key in _REGION_ALIASES or key in _FIXED_ZONES

def get_abbreviation_choices(current = "", limit = 25):
    current = current.strip().lower()
    return [
        (label[:100], name) for name, label in _ABBREVIATION_LABELS.items()
        if not current or name.lower().startswith(current) or current in label.lower()
    ][:limit]
    
def get_timezone_choices(current = "", limit = 25):
    choices = get_abbreviation_choices(current, limit)
    needle = current.strip().lower()
    for name in _IANA_CHOICE_NAMES:
        if len(choices) >= limit:
            break
        if needle in name.lower():
            choices.append((name[:100], name))
    return choices
    
def parse_time(text):
    return datetime.strptime(text.strip(), "%H:%M").strftime("%H:%M")

def discord_timestamp(unix, style = "F"):
    return f"<t:{int(unix)}:{style}>"