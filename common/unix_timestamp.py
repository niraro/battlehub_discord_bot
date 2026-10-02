from datetime import datetime
from zoneinfo import ZoneInfo

def get_discord_timestamp(date_str, tz_name):
    local_date = datetime.strptime(date_str, "%d-%m-%Y %H:%M")
    local_date = local_date.replace(tzinfo=ZoneInfo(tz_name))
    
    unix_time = int(local_date.timestamp())
    discord_time = f"<t:{unix_time}:F>"
    
    return unix_time, discord_time
