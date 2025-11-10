import threading
import time
import sqlite3
from datetime import datetime
from tkinter import messagebox

def check_reminders():
    # Tạo kết nối SQLite riêng cho thread này
    conn = sqlite3.connect("reminder.db", check_same_thread=False)
    c = conn.cursor()

    # ✅ Đảm bảo bảng events tồn tại
    c.execute("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT,
            start_time TEXT,
            location TEXT,
            remind INTEGER
        )
    """)
    conn.commit()

    while True:
        c.execute("SELECT id, event, start_time, remind FROM events")
        events = c.fetchall()
        now = datetime.now()

        for e in events:
            start = datetime.fromisoformat(e[2])
            delta = (start - now).total_seconds() / 60
            if 0 < delta <= e[3]:
                messagebox.showinfo("Nhắc nhở", f"Sắp đến: {e[1]} trong {int(delta)} phút!")
                c.execute("DELETE FROM events WHERE id=?", (e[0],))
                conn.commit()

        time.sleep(60)

def start_reminder():
    t = threading.Thread(target=check_reminders, daemon=True)
    t.start()
