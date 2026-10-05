# Options used for buttons
DEADLOCK_STAFF_ROLES = [
    "Tournament Admin",
    "Stream Moderator",
    "Player Moderator",
    "Talent",
    "Observer",
    "Producer",
]
UNAVAILABLE = "Unavailable"
MAYBE = "Maybe"
WITHDRAW = "Withdraw"
EDIT = "Edit"
RESET = "Reset"
DISPLAY_ORDER = DEADLOCK_STAFF_ROLES + [UNAVAILABLE, MAYBE]

# Status that gets stored in availability's status
STATUS_SIGNED_UP = "signed_up"
STATUS_UNAVAILABLE = "unavailable"
STATUS_MAYBE = "maybe"
STATUS_LABEL = {
    STATUS_SIGNED_UP: "Signed Up",
    STATUS_UNAVAILABLE: "Unavailable",
    STATUS_MAYBE: "Maybe",
}

REQUIRE_DISCORD_ROLE = True
EDIT_AND_RESET_ROLES = ("The Big Cheeses", "Admin", "Mod")
RESET_CLEAR_SIGNUPS = False

DEFAULT_TIMEZONE = "UTC"
SETTINGS_KEYS = (
    "call_time",
    "broadcast_start",
    "sign_up_deadline",
    "timezone",
    "schedule_channel_id",
    "ping_role_id",
    "calendar_url",
)

DEFAULT_SETTINGS = {
    "call_time": "00:00",
    "broadcast_start": "01:00",
    "sign_up_deadline": 72,
    "timezone": DEFAULT_TIMEZONE,
    "schedule_channel_id": None,
    "ping_role_id": None,
    "calendar_url": None,
}
