import sqlite3
from database.db_config import DB_FILE
    
def create_welcome_tables():    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS welcome_settings (
            guild_id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            message TEXT NOT NULL         
        )
""")
    conn.commit()
    conn.close()
    
    
def set_welcome(guild_id, channel_id, message):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO welcome_settings (guild_id, channel_id, message) VALUES (?, ?, ?) "
        "ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id, message = excluded.message",
        (guild_id, channel_id, message)
    )
    conn.commit()
    conn.close()
    
def get_welcome(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT channel_id, message FROM welcome_settings WHERE guild_id = ? ", (guild_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row 