import sqlite3
from database.db_config import DB_FILE

def create_ticket_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()
    

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