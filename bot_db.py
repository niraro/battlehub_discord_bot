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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            ticket_number INTEGER NOT NULL,
            discord_id TEXT NOT NULL,
            thread_id TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            last_activity INTEGER NOT NULL,
            title TEXT
        )                  
""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticket_settings (
            guild_id TEXT PRIMARY KEY,
            tickets_channel_id TEXT NOT NULL,
            board_message_id TEXT
        )           
""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS log_settings (
            guild_id TEXT NOT NULL,
            log_type TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            PRIMARY KEY (guild_id, log_type)
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



def add_command(name, note, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO commandlist (name, note, guild_id) VALUES (?, ?, ?)", (name, note, guild_id)
    )
    conn.commit()
    conn.close()
    
def remove_command(name, guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM commandlist WHERE name = ? AND guild_id = ?", (name, guild_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount

def get_all_commands(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, note FROM commandlist WHERE guild_id = ? ORDER BY name ASC", (guild_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows



def set_tickets_channel(guild_id, channel_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO ticket_settings (guild_id, tickets_channel_id) VALUES (?, ?) "
        "ON CONFLICT(guild_id) DO UPDATE SET tickets_channel_id = excluded.tickets_channel_id",
        (guild_id, channel_id)
    )
    conn.commit()
    conn.close()
    
def get_tickets_channel(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT tickets_channel_id FROM ticket_settings WHERE guild_id = ?", (guild_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_open_ticket(guild_id, discord_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, ticket_number, thread_id FROM tickets WHERE guild_id = ? AND discord_id = ? AND status = 'open'",
        (guild_id, discord_id)
    )
    row = cursor.fetchone()
    conn.close()
    return row

def get_next_ticket_number(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT MAX(ticket_number) FROM tickets WHERE guild_id = ?", (guild_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return (row[0] or 0) + 1

def create_ticket(guild_id, discord_id, ticket_number, thread_id, title, timestamp):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tickets (guild_id, ticket_number, discord_id, thread_id, title, status, created_at, last_activity) "
        "VALUES (?, ?, ?, ?, ?, 'open', ?, ?)",
        (guild_id, ticket_number, discord_id, thread_id, title, timestamp, timestamp)
    )
    conn.commit()
    conn.close()
    
def update_ticket_activity(thread_id, timestamp):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tickets SET last_activity = ? WHERE thread_id = ?", (timestamp, thread_id)
    )
    conn.commit()
    conn.close()
    
def get_ticket_by_thread(thread_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()    
    cursor.execute(
        "SELECT id, discord_id, status FROM tickets WHERE thread_id = ?", (thread_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row

def close_ticket(ticket_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor() 
    cursor.execute(
        "UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,)
    )
    conn.commit()
    conn.close()
    
def get_stale_tickets(cutoff_timestamp):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, guild_id, discord_id, thread_id, ticket_number FROM tickets "
        "WHERE status = 'open' AND last_activity < ?", (cutoff_timestamp,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_open_tickets_for_board(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ticket_number, title, thread_id FROM tickets WHERE guild_id = ? AND status = 'open' ORDER BY ticket_number ASC",
        (guild_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_closed_ticket_count(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM tickets WHERE guild_id = ? AND status = 'closed'", (guild_id,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_board_message_id(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT board_message_id FROM ticket_settings WHERE guild_id = ?", (guild_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def set_board_message_id(guild_id, message_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE ticket_settings SET board_message_id = ? WHERE guild_id = ?", (message_id, guild_id)
    )
    conn.commit()
    conn.close()
    


def set_log_channel(guild_id, log_type, channel_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO log_settings (guild_id, log_type, channel_id) VALUES (?, ?, ?) "
        "ON CONFLICT(guild_id, log_type) DO UPDATE SET channel_id = excluded.channel_id",
        (guild_id, log_type, channel_id)
    )
    conn.commit()
    conn.close()
    
def get_log_channel(guild_id, log_type):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT channel_id FROM log_settings WHERE guild_id = ? AND log_type = ?", (guild_id, log_type)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_all_log_settings(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT log_type, channel_id FROM log_settings WHERE guild_id = ?", (guild_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows