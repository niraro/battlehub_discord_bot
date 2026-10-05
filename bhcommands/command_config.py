GENERAL_COMMANDS = [
    ("bhcommands", "Show all available BattleBot commands, shown by features. Also uses format `!bhcommands`"),
    ("timeconvert", "Convert a date and time into Discord format. Uses format `!timeconvert <DD-MM-YYYY> <HH:MM> <IANA Timezone>` **NB: IANA Timezone example: America/Edmonton**"),
]

NEWS_AND_ANNOUNCEMENTS = [
    ("post", "Post an announcement in an embed. Links work, but pings turn into mentions, and will not notify user(s) and/or roles. Can also us the format `!post <Message>`"),
    ("setwelcomemessage", "Set a custom welcome message to an assigned channel. Also uses format `!setwelcomemessage <Channel Name/Channel ID> <Message>`. **NB: When adding emojis, if the bot does not have access to them (i.e. bot is not in the emoji's server), the emoji will not show. Global and server-specific emojis work**"),
]

EVENT_COMMANDS = [
    ("addevent", "Add an event to the list of upcoming events. Also uses format `!addevent <\"Event Name\"> <DD-MM-YYYY> <HH:MM> <IANA Timezone>`"),
    ("remove_event", "Remove event from the list of upcoming events. Uses format `!remove_event <\"Event Name\">`"),
    ("showevents", "Show the list of upcoming events. Also uses format `!showevents`"),
    ("checkcalendar", "Show all upcoming events for a picked month via dropdown. Also uses format `!checkcalendar <Timezone>`"),
]

MODERATION_COMMANDS = [
    ("unban", "Unban a user. Also user format `!unban <user_id>`"),
    ("addflaggedterm", "Add a specified word/term to the list of flaggable terms. Also uses format `!addflaggedterm <term>`"),
    ("removeflaggedterm", "Remove a specified word/term from the list of flaggable terms. Also uses format `!removeflaggedterm <term>`. **NB: multiple instances of the same term will remove all duplicates as well**"),
    ("viewflaggedterms", "Show a list of all flaggable terms. Also uses format `!viewflaggedterms`"),
    ("addflaggeddomain", "Add a specified domain to the list of flaggable domains. Also uses format `!addflaggeddomain <domain>`"),
    ("removeflaggeddomain", "Remove a specified domain from the list of flaggable domains. Also uses format `!removeflaggeddomain <domain>`"),
    ("viewflaggeddomains", "View the list of all flagged domains. Also uses format `!viewflaggeddomains`"),
    ("blacklist_image", "App command that can be accessed by right-clicking a post -> `Apps` -> `BattleBot` -> `Blacklist Image`"),
]

LOG_COMMANDS = [
    ("setlogs", "Assign a log type to a channel. Also uses format `!setlogs \"<Log Name>\" \"<channel name/channel ID>\"`"),
    ("viewlogs", "View log channels currently set. Also uses format `!viewlogs`"),
    ("timeoutlist", "View currently times out users. Also uses format `!timeoutlist`"),
    ("timeouthistory", "View the timeout history of a specified user. Also uses format `!timeouthistory <user>`. **NB: Can '@' the user, write out their displayed name, or input their user ID**"),
    ("banlist", "View all currently banned users. Also uses format `!banlist`"),
    ("addhoneypot", "Assign specified channel as honeypot channel. Can have multiple honeypot channels at the same time. Also uses format `!addhoneypot <channel name/channel ID>`"),
    ("removehoneypot", "Remove an assigned honeypot channel. Also uses format `!removehoneypot <channel name/channel ID>`"),
    ("honeypotlist", "View all honeypot-assigned channels. Also uses format `!honeypotlist`"),
]

REACTION_COMMANDS = [
    ("addreactrole", "Add a link between emoji and role to a message post, to add or remove a role(s) when reacting. True = Toggleable, False = One-time. Also uses format `!addreactrole <Message Link> <Emoji> <Add Role> <Remove Role> <Toggle>`. **NB: If this note is still here, this means the need to add all input for the `!` variant of the command still holds true**"),
    ("removereactrole", "Remove a link between emoji and role on a message post. Also uses format `!removereactrole <Message Link> <Emoji>`"),
    ("listreactroles", "View the list of all emoji-to-role mappings. Also uses format `!listreactroles <Message Link>`"),
]

SCHEDULING_COMMANDS = [
    ("addavail", "Add availability of a user for a given role for the event. Also uses format `!addavail <\"Event Name\"> <Role> <Status> <Note (optional)>`. **NB: If the role has multiple words, put \"\" around it**"),
    ("adjustavail", "Adjust availability of a user for a given role for the event. Also uses format `!adjustavail <\"Event Name\"> <Role> <Status> <Note (optional)>`. Can also write `clear` as note to remove it. **NB: If the role has multiple words, put \"\" around it**"),
    ("removeavail", "Remove availability of a user for a given role for the event. Also uses format `!removeavail <\"Event Name\"> <Role>`. **NB: If the role has multiple words, put \"\" around it**"),
    ("checkavail", "Show availability of a user for all events they are available for. Also uses format `!checkavail @<User>/<User ID>`"),
    ("eventavail", "Show availability of users for the chosen event. Also uses format `!checkevent <\"Event Name\">`"),
    ("dateavail", "Show event(s), then availability. If two or more events are present, will prompt you to pick the event. Also uses format `!checkdate <DD-MM-YYYY> <Timezone>`"),
]

TICKET_COMMANDS = [
    ("setticketschannel", "Assign a channel to act as a ticket-message board. Each new ticket creates a new thread. Also uses format `!setticketschannel <Channel Name/Channel ID>`"),
    ("reply", "Reply to the user inside the ticket's thread. Also uses format `!reply <Message>`"),
    ("closeticket", "Close ticket. This will notify the user as well. Also uses format `!closeticket`"),
]


COMMAND_CATEGORIES = [
    ("General Commands", GENERAL_COMMANDS),
    ("News & Announcements Commands", NEWS_AND_ANNOUNCEMENTS),
    ("Event Commands", EVENT_COMMANDS),
    ("Moderation Commands", MODERATION_COMMANDS),
    ("Log Commands", LOG_COMMANDS),
    ("Reaction Commands", REACTION_COMMANDS),
    ("Scheduling Commands", SCHEDULING_COMMANDS),
    ("Ticket Commands", TICKET_COMMANDS),
]