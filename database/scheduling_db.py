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
            role TEXT,
            status TEXT NOT NULL,
            note TEXT,
            guild_id TEXT NOT NULL
        )    
""")
    conn.commit()
    conn.close()
    

def upsert_availability(event_id, discord_id, role, status, note, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, note FROM availability WHERE event_id = ? AND discord_id = ? AND role = ? AND guild_id = ?", (event_id, discord_id, role, guild_id)
    )
    existing = cursor.fetchone()
    if existing:
        final_note = None if note and note.lower() == "clear" else (note if note is not None else existing[1])
        cursor.execute(
            "UPDATE availability SET status = ?, note = ? WHERE id = ?", (status, final_note, existing[0])
        )
    else:
        cursor.execute(
            "INSERT INTO availability (event_id, discord_id, role, status, note, guild_id) VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, discord_id, role, status, note, guild_id)
        )
    conn.commit()
    conn.close()
    
def remove_availability(event_id, discord_id, role, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM availability WHERE event_id = ? AND discord_id = ? AND role = ? AND guild_id = ?", (event_id, discord_id, role, guild_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount

def remove_all_availability_for_event(event_id, discord_id, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM availability WHERE event_id = ? AND discord_id = ? AND guild_id = ?", (event_id, discord_id, guild_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount

def get_availability_by_user(discord_id, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT events.name, events.date_timestamp, availability.role, availability.status, availability.note FROM availability
        JOIN events ON availability.event_id = events.id WHERE availability.discord_id = ? AND availability.guild_id = ?
        ORDER BY events.date_timestamp ASC
    """, (discord_id, guild_id)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_availability_by_event(event_id, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT discord_id, role, status, note FROM availability WHERE event_id = ? AND guild_id = ?", (event_id, guild_id)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows