import sqlite3
from database.events_db import create_events_tables
from database.moderation_db import create_moderation_tables
from database.reaction_roles_db import create_reaction_roles_tables
from database.scheduling_db import create_scheduling_tables
from database.tickets_db import create_ticket_tables
from database.welcome_db import create_welcome_tables

def init_db():
    create_events_tables()
    create_moderation_tables()
    create_reaction_roles_tables()
    create_scheduling_tables()
    create_ticket_tables()
    create_welcome_tables()