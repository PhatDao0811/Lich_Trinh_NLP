import sqlite3

def connect_db():
    conn = sqlite3.connect("events.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT, start_time TEXT,
            location TEXT, remind INTEGER
        )
    """)
    conn.commit()
    return conn
