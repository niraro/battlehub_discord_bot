import sqlite3
from database.db_config import DB_FILE

def create_reaction_roles_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reaction_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            emoji TEXT NOT NULL,
            add_role_id TEXT,
            remove_role_id TEXT,
            toggle INTEGER NOT NULL DEFAULT 0,
            UNIQUE(guild_id, message_id, emoji)         
        )
""")
    conn.commit()
    conn.close()

    
def add_reaction_role_mapping(guild_id, message_id, emoji, add_role_id, remove_role_id, toggle):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()    
    cursor.execute(
        "INSERT INTO reaction_roles (guild_id, message_id, emoji, add_role_id, remove_role_id, toggle) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(guild_id, message_id, emoji) DO UPDATE SET "
        "add_role_id = excluded.add_role_id, remove_role_id = excluded.remove_role_id, toggle = excluded.toggle ",
        (guild_id, message_id, emoji, add_role_id, remove_role_id, int(toggle))
    )
    conn.commit()
    conn.close()
    
def get_reaction_role_mapping(guild_id, message_id, emoji):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT add_role_id, remove_role_id, toggle FROM reaction_roles WHERE guild_id = ? AND message_id = ? AND emoji = ? ",
        (guild_id, message_id, emoji)
    )
    row = cursor.fetchone()
    conn.close()
    return row

def remove_reaction_role_mapping(guild_id, message_id, emoji):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM reaction_roles WHERE guild_id = ? AND message_id = ? AND emoji = ? ",
        (guild_id, message_id, emoji)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount

def list_reaction_role_mappings(guild_id, message_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT emoji, add_role_id, remove_role_id, toggle FROM reaction_roles WHERE guild_id = ? AND message_id = ? ",
        (guild_id, message_id)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows