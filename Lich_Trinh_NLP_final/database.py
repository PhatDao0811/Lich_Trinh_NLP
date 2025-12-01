import sqlite3
from datetime import datetime


def get_db():
    conn = sqlite3.connect("events.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start TEXT NOT NULL,
            end TEXT,
            location TEXT,
            reminder_minutes INTEGER
        )
    """)
    conn.commit()
    conn.close()


def add_event(name, start, end=None, location=None, reminder=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO events (name, start, end, location, reminder_minutes) VALUES (?, ?, ?, ?, ?)",
        (name, start, end, location, reminder),
    )
    conn.commit()
    conn.close()


def format_for_html(iso_datetime_str):
    if iso_datetime_str:
        try:
            return datetime.fromisoformat(iso_datetime_str).strftime('%Y-%m-%dT%H:%M')
        except ValueError:
            return ''
    return ''


def get_events_by_date(date_str):
    conn = get_db()
    like_pattern = f"{date_str}%"
    cursor = conn.execute("SELECT * FROM events WHERE start LIKE ?", (like_pattern,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_event(id):
    conn = get_db()
    row = conn.execute("SELECT * FROM events WHERE id = ?", (id,)).fetchone()
    conn.close()

    if row:
        event = dict(row)
        event['start_html'] = format_for_html(event['start'])
        event['end_html'] = format_for_html(event['end'])
        return event
    return None


def update_event(id, name, start, end, location, reminder):
    conn = get_db()

    try:
        start_iso = datetime.strptime(start, '%Y-%m-%dT%H:%M').isoformat(timespec="minutes")
        end_iso = datetime.strptime(end, '%Y-%m-%dT%H:%M').isoformat(timespec="minutes") if end else None
    except ValueError:
        start_iso = start
        end_iso = end

    conn.execute(
        "UPDATE events SET name=?, start=?, end=?, location=?, reminder_minutes=? WHERE id=?",
        (name, start_iso, end_iso, location, reminder, id),
    )
    conn.commit()
    conn.close()


def delete_event(id):
    conn = get_db()
    conn.execute("DELETE FROM events WHERE id = ?", (id,))
    conn.commit()
    conn.close()


def get_all_events():
    conn = get_db()
    cursor = conn.execute("SELECT * FROM events")
    rows = cursor.fetchall()
    conn.close()

    events_list = [dict(row) for row in rows]
    return events_list


# FUNCTION: Lấy sự kiện theo phạm vi ngày (dùng cho FullCalendar)
def get_events_by_range(start_date_str, end_date_str):
    """Lấy tất cả sự kiện có thời gian bắt đầu nằm trong khoảng [start_date_str, end_date_str]"""
    conn = get_db()

    # Sử dụng start_date_strT00:00:00 và end_date_strT23:59:59 để đảm bảo bao gồm toàn bộ ngày cuối
    cursor = conn.execute(
        "SELECT * FROM events WHERE start >= ? AND start <= ?",
        (f"{start_date_str}T00:00:00", f"{end_date_str}T23:59:59")
    )
    rows = cursor.fetchall()
    conn.close()

    # Chuyển đổi thành list of dicts
    events_list = [dict(row) for row in rows]
    return events_list