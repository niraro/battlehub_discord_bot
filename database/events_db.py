import sqlite3
from database.db_config import DB_FILE

def create_events_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date_timestamp INTEGER NOT NULL,
            added_by TEXT NOT NULL,
            guild_id TEXT NOT NULL
        )
""")
    conn.commit()
    conn.close()
    

def add_event(name, date, added_by, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO events (name, date_timestamp, added_by, guild_id) VALUES (?, ?, ?, ?)",
        (name, date, added_by, guild_id)
    )
    conn.commit()
    conn.close()
    
def event_remove(name, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM events WHERE name = ? AND guild_id = ?", (name, guild_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount

def get_all_events(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, date_timestamp, added_by FROM events WHERE guild_id = ? ORDER BY date_timestamp ASC",
        (guild_id,)        
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_event_from_list(name, guild_id):
    events = get_all_events(guild_id)
    for event in events:
        if event[1].lower() == name.lower():
            return event
    return None
    
def get_events_by_date_range(start_ts, end_ts, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, date_timestamp, added_by FROM events WHERE date_timestamp BETWEEN ? AND ? AND guild_id = ? ORDER BY date_timestamp ASC",
        (start_ts, end_ts, guild_id)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_events_by_month(start_ts, end_ts, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, date_timestamp, added_by FROM events WHERE date_timestamp BETWEEN ? AND ? AND guild_id = ? ORDER BY date_timestamp ASC",
        (start_ts, end_ts, guild_id)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows