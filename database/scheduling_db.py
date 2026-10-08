import sqlite3
from database.db_config import DB_FILE

def create_scheduling_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            discord_id TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL,
            note TEXT,
            guild_id TEXT NOT NULL,
            UNIQUE (event_id, discord_id, role, guild_id)
        )    
""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS broadcast_settings (
            guild_id TEXT PRIMARY KEY,
            call_time TEXT NOT NULL,
            broadcast_start TEXT NOT NULL,
            sign_up_deadline INTEGER NOT NULL DEFAULT 72,
            timezone TEXT NOT NULL DEFAULT 'UTC',
            schedule_channel_id TEXT,
            ping_role_id TEXT,
            calendar_url TEXT
        )
""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            call_time TEXT NOT NULL,
            broadcast_start INTEGER NOT NULL,
            signup_deadline INTEGER NOT NULL,
            timezone TEXT NOT NULL,
            ping_role_id TEXT,
            calendar_url TEXT,
            created_by TEXT NOT NULL,
            UNIQUE (event_id, guild_id)
        )                
""")
    conn.commit()
    conn.close()


def get_availability_by_user(discord_id, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT events.name, events.date_timestamp, availability.role, availability.status, availability.note FROM availability
        JOIN events ON availability.event_id = events.id WHERE availability.discord_id = ? AND availability.guild_id = ?
        ORDER BY events.date_timestamp ASC, availability.id ASC
    """, (discord_id, guild_id)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_availability_by_event(event_id, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT discord_id, role, status, note FROM availability WHERE event_id = ? AND guild_id = ? "
        "ORDER BY id ASC", (event_id, guild_id)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def set_broadcast_settings(guild_id, call_time, broadcast_start, sign_up_deadline, timezone, schedule_channel_id, ping_role_id, calendar_url):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO broadcast_settings (guild_id, call_time, broadcast_start, sign_up_deadline, timezone, schedule_channel_id, ping_role_id, calendar_url) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(guild_id) DO UPDATE SET "
        "call_time = excluded.call_time, broadcast_start = excluded.broadcast_start, sign_up_deadline = excluded.sign_up_deadline, "
        "timezone = excluded.timezone, schedule_channel_id = excluded.schedule_channel_id, ping_role_id = excluded.ping_role_id, calendar_url = excluded.calendar_url ",
        (guild_id, call_time, broadcast_start, sign_up_deadline, timezone, schedule_channel_id, ping_role_id, calendar_url)
    )
    conn.commit()
    conn.close()
    
def get_broadcast_settings(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT call_time, broadcast_start, sign_up_deadline, timezone, schedule_channel_id, ping_role_id, calendar_url "
        "FROM broadcast_settings WHERE guild_id = ? ", (guild_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row


def create_schedule(event_id, guild_id, channel_id, message_id, call_time, broadcast_start, signup_deadline, timezone, ping_role_id, calendar_url, created_by):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO schedules (event_id, guild_id, channel_id, message_id, call_time, broadcast_start, signup_deadline, timezone, ping_role_id, calendar_url, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (event_id, guild_id, channel_id, message_id, call_time, broadcast_start, signup_deadline, timezone, ping_role_id, calendar_url, created_by)
    )    
    conn.commit()
    conn.close()
    
def get_schedule_by_event(event_id, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT channel_id, message_id FROM schedules WHERE event_id = ? AND guild_id = ?", (event_id, guild_id)
    )
    row = cursor.fetchone()
    conn.close()
    return row

def get_schedule_by_message(message_id, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT schedules.event_id, schedules.call_time, schedules.broadcast_start, schedules.signup_deadline, schedules.ping_role_id, schedules.calendar_url,
        events.name, events.date_timestamp, schedules.timezone FROM schedules
        JOIN events ON schedules.event_id = events.id WHERE schedules.message_id = ? AND schedules.guild_id = ?
        """, (message_id, guild_id)
    )
    row = cursor.fetchone()
    conn.close()
    return row

def delete_schedule_by_event(event_id, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM schedules WHERE event_id = ? AND guild_id = ? ", (event_id, guild_id) 
    )
    conn.commit()
    conn.close()

def delete_schedule_data_for_event(event_id, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM availability WHERE event_id = ? AND guild_id = ? ", (event_id, guild_id)
    )
    cursor.execute(
        "DELETE FROM schedules WHERE event_id = ? AND guild_id = ? ", (event_id, guild_id)
    )
    conn.commit()
    conn.close()
    
    
def add_signup(event_id, discord_id, role, status, guild_id, note = None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO availability (event_id, discord_id, role, status, note, guild_id) VALUES (?, ?, ?, ?, ?, ?) ",
        (event_id, discord_id, role, status, note, guild_id)
    )
    conn.commit()
    conn.close()
    
def remove_signups(event_id, discord_id, guild_id, roles = None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if roles:
        marks = ",".join("?" * len(roles))  
        cursor.execute(
            f"DELETE FROM availability WHERE event_id = ? AND discord_id = ? AND guild_id = ? AND role IN ({marks}) ",
            (event_id, discord_id, guild_id, *roles)
        )
    else:
        cursor.execute(
            "DELETE FROM availability WHERE event_id = ? AND discord_id = ? AND guild_id = ? ", (event_id, discord_id, guild_id)
        )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted

def get_user_roles(event_id, discord_id, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role FROM availability WHERE event_id = ? AND discord_id = ? AND guild_id = ? ", (event_id, discord_id, guild_id)
    )
    roles = {row[0] for row in cursor.fetchall()}
    conn.close()
    return roles

def update_schedule_times(message_id, guild_id, call_time, broadcast_start, signup_deadline):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE schedules SET call_time = ?, broadcast_start = ?, signup_deadline = ? WHERE message_id = ? AND guild_id = ? ",
        (call_time, broadcast_start, signup_deadline, message_id, guild_id)
    )
    conn.commit()
    conn.close()
    
def get_active_schedules(since_timestamp):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT schedules.event_id, schedules.guild_id, schedules.channel_id, schedules.message_id, schedules.call_time,
        schedules.broadcast_start, schedules.signup_deadline, schedules.ping_role_id, schedules.calendar_url,
        events.name, events.date_timestamp FROM schedules
        JOIN events ON schedules.event_id = events.id WHERE events.date_timestamp >= ? """, (since_timestamp,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows