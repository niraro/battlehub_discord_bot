import sqlite3
from database.db_config import DB_FILE

def create_moderation_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS log_settings (
            guild_id TEXT NOT NULL,
            log_type TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            PRIMARY KEY (guild_id, log_type)
        )  
""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            author_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            original_content TEXT NOT NULL,
            matched_terms TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp INTEGER NOT NULL
        )                   
""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timeout_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            discord_id TEXT NOT NULL,
            duration_seconds INTEGER,
            reason TEXT,
            moderator_id TEXT,
            source TEXT NOT NULL,
            timestamp INTEGER NOT NULL         
        )
""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flagged_terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            term TEXT NOT NULL,
            added_by TEXT NOT NULL
        )                   
""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flagged_domains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            added_by TEXT NOT NULL         
        )
""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scam_image_hashes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            phash TEXT NOT NULL,
            added_by TEXT NOT NULL         
        )
""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS honeypot_settings (
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            PRIMARY KEY (guild_id, channel_id)         
        )
""")
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

def add_flagged_term(guild_id, term, added_by):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO flagged_terms (guild_id, term, added_by) VALUES (?, ?, ?)", 
        (guild_id, term.lower(), added_by)
    )
    conn.commit()
    conn.close()

def remove_flagged_term(guild_id, term):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM flagged_terms WHERE guild_id = ? AND term = ?", 
        (guild_id, term.lower())
    )
    conn.commit()
    conn.close()
    return cursor.rowcount

def get_flagged_terms(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT term FROM flagged_terms WHERE guild_id = ?",
        (guild_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def create_pending_review(guild_id, message_id, author_id, channel_id, content, matched_terms, timestamp):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pending_reviews (guild_id, message_id, author_id, channel_id, original_content, matched_terms, status, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
        (guild_id, message_id, author_id, channel_id, content, matched_terms, timestamp)
    )
    conn.commit()
    conn.close()
    
def get_pending_review(message_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, guild_id, author_id, channel_id, original_content, matched_terms, status FROM pending_reviews " 
        "WHERE message_id = ?",
        (message_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row

def set_review_status(review_id, status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE pending_reviews SET status = ? WHERE id = ?", (status, review_id,)
    )
    conn.commit()
    conn.close()

def log_timeout(guild_id, discord_id, duration_seconds, reason, moderator_id, source, timestamp):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO timeout_history (guild_id, discord_id, duration_seconds, reason, moderator_id, source, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (guild_id, discord_id, duration_seconds, reason, moderator_id, source, timestamp)
    )
    conn.commit()
    conn.close()
    
def get_timeout_count(guild_id, discord_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM timeout_history WHERE guild_id = ? AND discord_id = ? ",
        (guild_id, discord_id)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_timeout_history(guild_id, discord_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT duration_seconds, reason, moderator_id, source, timestamp FROM timeout_history "
        "WHERE guild_id = ? AND discord_id = ? ORDER BY timestamp DESC ", (guild_id, discord_id)
    )  
    rows = cursor.fetchall()
    conn.close()
    return rows
    
def add_flagged_domain(guild_id, domain, added_by):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO flagged_domains (guild_id, domain, added_by) VALUES (?, ?, ?) ",
        (guild_id, domain.lower(), added_by)
    )
    conn.commit()
    conn.close()
    
def remove_flagged_domain(guild_id, domain):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM flagged_domains WHERE guild_id = ? AND domain = ? ",
        (guild_id, domain.lower())
    )
    conn.commit()
    conn.close()
    return cursor.rowcount

def get_flagged_domains(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT domain FROM flagged_domains WHERE guild_id = ? ", (guild_id,)
    )   
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def add_scam_hash(guild_id, phash, added_by):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO scam_image_hashes (guild_id, phash, added_by) VALUES (?, ?, ?) ",
        (guild_id, phash, added_by)
    )
    conn.commit()
    conn.close()
    
def get_scam_hash(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT phash FROM scam_image_hashes WHERE guild_id = ? ", (guild_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def add_honeypot_channel(guild_id, channel_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO honeypot_settings (guild_id, channel_id) VALUES (?, ?) ",
        (guild_id, channel_id)
    )
    conn.commit()
    conn.close()
    
def remove_honeypot_channel(guild_id, channel_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor() 
    cursor.execute(
        "DELETE FROM honeypot_settings WHERE guild_id = ? AND channel_id = ? ",
        (guild_id, channel_id)
    )      
    conn.commit()
    conn.close()
    return cursor.rowcount

def is_honeypot_channel(guild_id, channel_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM honeypot_settings WHERE guild_id = ? AND channel_id = ? ",
        (guild_id, channel_id)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None

def list_honeypot_channels(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT channel_id FROM honeypot_settings WHERE guild_id = ? ",
        (guild_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]