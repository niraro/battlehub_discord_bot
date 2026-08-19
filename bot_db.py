import sqlite3

DB_FILE = "bot_data.db"

def init_db():
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
    cursor.execute("""    
        CREATE TABLE IF NOT EXISTS commandlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            note TEXT NOT NULL,
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
    
def remove_event(name, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events WHERE name = ? AND guild_id = ?", (name, guild_id))
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
    """, (discord_id, guild_id))
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



def add_command(name, note, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO commandlist (name, note, guild_id) VALUES (?, ?, ?)", (name, note, guild_id))
    conn.commit()
    conn.close()
    
def remove_command(name, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM commandlist WHERE name = ? AND guild_id = ?", (name, guild_id))
    conn.commit()
    conn.close()
    return cursor.rowcount

def get_all_commands(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, note FROM commandlist WHERE guild_id = ? ORDER BY name ASC", (guild_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows