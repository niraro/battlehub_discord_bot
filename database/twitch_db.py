import sqlite3
from database.db_config import DB_FILE

def create_twitch_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS twitch_tracker(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            twitch_id TEXT NOT NULL,
            login TEXT NOT NULL,
            display_name TEXT NOT NULL,
            discord_channel_id TEXT NOT NULL,
            message_template TEXT,
            style TEXT NOT NULL DEFAULT 'embed',
            announced_stream_id TEXT,
            announcement_message_id TEXT,
            started_at INTEGER,
            added_by TEXT NOT NULL,
            UNIQUE (guild_id, twitch_id, discord_channel_id)
        )
""")
    conn.commit()
    conn.close()
    
def _fetch_tracks(query, params = ()):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_all_twitch_tracks():
    return _fetch_tracks("SELECT * FROM twitch_tracker")

def get_guild_twitch_tracks(guild_id):
    return _fetch_tracks("SELECT * FROM twitch_tracker WHERE guild_id = ? ORDER BY login ASC", (guild_id,))

def get_twitch_tracks_by_login(guild_id, login, discord_channel_id = None):
    if discord_channel_id:
        return _fetch_tracks(
            "SELECT * FROM twitch_tracker WHERE guild_id = ? AND login = ? AND discord_channel_id = ?", (guild_id, login, discord_channel_id)
        )
    return _fetch_tracks("SELECT * FROM twitch_tracker WHERE guild_id = ? AND login = ?", (guild_id, login))

def upsert_twitch_track(guild_id, twitch_id, login, display_name, discord_channel_id, message_template, style, added_by):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM twitch_tracker WHERE guild_id = ? AND twitch_id = ? AND discord_channel_id = ?",
        (guild_id, twitch_id, discord_channel_id)
    )
    row = cursor.fetchone()
    if row:
        track_id, created = row[0], False
        cursor.execute(
            "UPDATE twitch_tracker SET login = ?, display_name = ?, message_template = COALESCE(?, message_template), style = COALESCE(?, style) WHERE id = ?",
            (login, display_name, message_template, style, track_id)
        )
    else:
        cursor.execute(
            "INSERT INTO twitch_tracker (guild_id, twitch_id, login, display_name, discord_channel_id, message_template, style, added_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (guild_id, twitch_id, login, display_name, discord_channel_id, message_template, style, added_by)
        )
        track_id, created = cursor.lastrowid, True
    conn.commit()
    conn.close()
    return track_id, created

def remove_twitch_track(track_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM twitch_tracker WHERE id = ?", (track_id,)
    )
    conn.commit()
    conn.close()
    
def set_announcement(track_id, stream_id, message_id, started_at):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE twitch_tracker SET announced_stream_id = ?, announcement_message_id = ?, started_at = ? WHERE id = ?",
        (stream_id, message_id, started_at, track_id)
    )
    conn.commit()
    conn.close()
    
def mark_announced(track_id, stream_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE twitch_tracker SET announced_stream_id = ? WHERE id = ?", (track_id, stream_id)
    )
    conn.commit()
    conn.close()
    
def clear_announcement(track_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE twitch_tracker SET announcement_message_id = NULL WHERE id = ?", (track_id,)
    )
    conn.commit()
    conn.close()