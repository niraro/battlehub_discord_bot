BUILTIN_COMMANDS = [
    ("post", "Posts an announcement in an embed. Uses format `!post <Message>`"),
    ("timeconvert", "Converts a date and time into Discord format. Uses format `!timeconvert <DD-MM-YYYY> <HH:MM> <Timezone>`"),
    ("addevent", "Adds an event to the list of upcoming events. Uses format `!addevent <\"Name\"> <DD-MM-YYYY> <HH:MM> <Timezone>`"),
    ("remove_event", "Removes event from the list of upcoming events. Uses format `!remove_event <\"Event Name\">`"),
    ("showevents", "Shows the list of upcoming events."),
    ("addavail", "Adds availability of a user for a given role for the event. Uses format `!addavail <\"Event Name\"> <Role> <Status> <Note (optional)>`. **NB: If the role has multiple words, put \"\" around it**"),
    ("adjustavail", "Adjusts availability of a user for a given role for the event. Uses format `!adjustavail <\"Event Name\"> <Role> <Status> <Note (optional)>`. Can also write `clear` as note to remove it. **NB: If the role has multiple words, put \"\" around it**"),
    ("removeavail", "Removes availability of a user for a given role for the event. Uses format `!removeavail <\"Event Name\"> <Role>`. **NB: If the role has multiple words, put \"\" around it**"),
    ("checkavail", "Shows availability of a user for all events they are available for. Uses format `!checkavail @<User>`"),
    ("checkevent", "Shows availability of users for the chosen event. Uses format `!checkevent <\"Event Name\">`"),
    ("checkdate", "Shows event(s), then availability. If two or more events are present, will prompt you to pick the event. Uses format `!checkdate <DD-MM-YYYY> <Timezone>`"),
    ("checkcalendar", "Shows all upcoming events for a picked month via dropdown. Uses format `!checkcalendar <Timezone>`"),
    ("bhcommands", "Shows all available commands for BattleHub Bot")
]