import re
import sqlite3
from datetime import datetime, timedelta

def connect_db():
    conn = sqlite3.connect("events.db")
    c = conn.cursor()
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
    return conn

def understand_text(text):
    text = text.lower().strip()
    now = datetime.now()
    conn = connect_db()
    c = conn.cursor()

    # --- Nhận dạng ý định ---
    if any(x in text for x in ["nhắc", "thêm", "tạo sự kiện", "ghi chú", "lịch hẹn"]):
        intent = "add_event"
    elif any(x in text for x in ["lịch", "có gì", "sự kiện", "việc gì"]):
        intent = "show_event"
    else:
        conn.close()
        return {"intent": "unknown", "msg": "Tôi chưa hiểu ý bạn."}

    # --- Xử lý khi thêm sự kiện ---
    if intent == "add_event":
        hour_match = re.search(r"(\d{1,2})\s*(?:giờ|h)", text)
        hour = hour_match.group(1) if hour_match else "00"

        # Ngày
        if any(x in text for x in ["ngày kìa", "hôm kìa"]):
            event_date = (now + timedelta(days=3)).strftime("%Y-%m-%d")
        elif any(x in text for x in ["ngày kia", "hôm kia"]):
            event_date = (now + timedelta(days=2)).strftime("%Y-%m-%d")
        elif "ngày mai" in text or "mai" in text:
            event_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "hôm nay" in text:
            event_date = now.strftime("%Y-%m-%d")
        else:
            event_date = now.strftime("%Y-%m-%d")

        event_time = f"{event_date} {hour.zfill(2)}:00"
        # Tách phần nội dung sự kiện: lấy đoạn sau “lịch hẹn”, “có lịch”, “đi”
        event_clean = re.sub(r".*?(?:lịch hẹn|lịch|nhắc tôi|đi)\s*", "", text)
        event_clean = re.sub(r"lúc\s*\d{1,2}\s*(?:giờ|h).*", "", event_clean).strip()
        if not event_clean:
            event_clean = "sự kiện không rõ"

        c.execute("INSERT INTO events (event, start_time, location, remind) VALUES (?, ?, ?, ?)",
                  (event_clean, event_time, "", 0))
        conn.commit()
        conn.close()
        return {"intent": "add_event", "msg": f"Đã thêm lịch {event_clean} vào {hour} giờ, ngày {event_date}."}

    # --- Xử lý khi xem lịch ---
    elif intent == "show_event":
        if any(x in text for x in ["ngày kìa", "hôm kìa"]):
            date_check = (now + timedelta(days=3)).strftime("%Y-%m-%d")
            label = "Ngày kìa"
        elif any(x in text for x in ["ngày kia", "hôm kia"]):
            date_check = (now + timedelta(days=2)).strftime("%Y-%m-%d")
            label = "Ngày kia"
        elif "ngày mai" in text or "mai" in text:
            date_check = (now + timedelta(days=1)).strftime("%Y-%m-%d")
            label = "Ngày mai"
        elif "hôm nay" in text:
            date_check = now.strftime("%Y-%m-%d")
            label = "Hôm nay"
        else:
            date_check = now.strftime("%Y-%m-%d")
            label = "Hôm nay"

        c.execute("SELECT event, start_time FROM events WHERE DATE(start_time)=?", (date_check,))
        rows = c.fetchall()
        conn.close()

        if rows:
            formatted = "\n".join([
                f"- {label.lower()} bạn có lịch {r[0]} lúc {r[1].split()[1]}"
                for r in rows
            ])
            return {"intent": "show_event", "msg": formatted}
        else:
            return {"intent": "show_event", "msg": f"{label} bạn không có lịch nào cả."}
