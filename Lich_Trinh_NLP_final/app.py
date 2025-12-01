from flask import Flask, request, render_template, redirect, url_for, jsonify, current_app
from database import init_db, add_event, get_events_by_date, get_event, update_event, delete_event, get_all_events, \
    get_events_by_range
from datetime import datetime, timedelta
import re
import json
from icalendar import Calendar, Event, vDatetime
from pytz import timezone

app = Flask(__name__)
init_db()

# Cần thiết cho iCalendar
LOCAL_TIMEZONE = timezone('Asia/Ho_Chi_Minh')


def check_reminders():
    """Kiểm tra sự kiện nào cần được nhắc nhở."""
    all_events = get_all_events()
    current_time = datetime.now()
    due_reminders = []

    for event in all_events:
        if not event['reminder_minutes'] or event['reminder_minutes'] <= 0:
            continue

        try:
            event_start_time = datetime.fromisoformat(event['start'])
            reminder_time = event_start_time - timedelta(minutes=event['reminder_minutes'])

            # Cửa sổ thông báo: Từ thời điểm nhắc nhở đến 1 phút sau thời gian bắt đầu
            if reminder_time <= current_time <= event_start_time + timedelta(minutes=1):
                # Đảm bảo sự kiện chưa kết thúc
                if current_time < event_start_time:
                    due_reminders.append({
                        'id': event['id'],
                        'name': event['name'],
                        'start': event['start'],
                        'reminder_time': reminder_time.strftime('%H:%M, %d/%m')
                    })
        except ValueError:
            continue

    return due_reminders


# CẬP NHẬT: Trang chủ chỉ hiển thị Lịch (FullCalendar)
@app.route("/", methods=["GET", "POST"])
def index():
    # Giữ lại logic mặc định ngày hiện tại nếu cần, nhưng không dùng để truy vấn list
    selected_date = datetime.now().strftime('%Y-%m-%d')
    return render_template("index.html", selected_date=selected_date)


@app.route("/add", methods=["POST"])
def add():
    text = request.form["event_text"]
    name, dt_iso, reminder = parse_text(text)

    add_event(name, dt_iso, None, None, reminder)
    return redirect(url_for("index"))


def parse_text(text):
    name = text
    reminder = 10

    time_pattern = r"(?:(\d{1,2})h\s*(\d{2})?|(\d{1,2}):(\d{2}))"
    date_pattern = r"(\d{1,2})\/(\d{1,2})(?:\/(\d{4}))?"
    time_phrases = r"(?:vào\s+lúc|lúc|vào\s+thời\s+điểm|ngày|vào|)"

    full_pattern = rf"\s*{time_phrases}\s*{time_pattern}.*?{date_pattern}"

    match = re.search(full_pattern, text, re.IGNORECASE)

    now = datetime.now()
    year = now.year
    hour = 0
    minute = 0
    day = now.day
    month = now.month

    if match:
        if match.group(1):
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
        elif match.group(3):
            hour = int(match.group(3))
            minute = int(match.group(4))

        day = int(match.group(5))
        month = int(match.group(6))

        if match.group(7):
            year = int(match.group(7))

        try:
            dt_iso = datetime(year, month, day, hour, minute).isoformat(timespec="minutes")
        except ValueError:
            dt_iso = now.isoformat(timespec="minutes")
            name = "[LỖI NGÀY/THÁNG] " + name
    else:
        dt_iso = now.isoformat(timespec="minutes")

    name = re.sub(full_pattern, '', text, 1, re.IGNORECASE).strip()

    if not name:
        name = "Sự kiện không tên"

    return name, dt_iso, reminder


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    event = get_event(id)

    # Lấy ngày được truyền từ query param (hoặc ngày hiện tại nếu không có)
    prev_date = request.args.get("prev_date")
    if not prev_date and event:
        prev_date = event['start'].split('T')[0]

    if not event:
        return "Sự kiện không tồn tại", 404

    if request.method == "POST":
        update_event(
            id=id,
            name=request.form["name"],
            start=request.form["start"],
            end=request.form["end"],
            location=request.form["location"],
            reminder=request.form["reminder"]
        )

        return_date = request.form.get("return_date")

        # Chuyển hướng về trang index hoặc trang danh sách tổng (dựa vào return_date)
        if return_date == 'list_all':
            return redirect(url_for("list_all"))
        else:
            return redirect(url_for("index", date=return_date))

    return render_template("edit_event.html", event=event, prev_date=prev_date)


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    delete_event(id)
    # Lấy ngày/route cần quay lại (từ hidden field trong form xóa)
    selected_date = request.form.get("selected_date")

    # Chuyển hướng về trang tương ứng
    if selected_date == 'list_all':
        return redirect(url_for("list_all"))
    else:
        return redirect(url_for("index", date=selected_date))


# NEW ROUTE: Danh sách tổng hợp tất cả sự kiện
@app.route("/list_all", methods=["GET", "POST"])
def list_all():
    all_events = get_all_events()

    # Sắp xếp các sự kiện theo thời gian bắt đầu
    sorted_events = sorted(all_events, key=lambda x: x['start'])

    # Render template mới
    return render_template("all_events.html", events=sorted_events)


# API Endpoint cho FullCalendar
@app.route("/api/events")
def events_feed():
    start_date_iso = request.args.get('start')
    end_date_iso = request.args.get('end')

    if not start_date_iso or not end_date_iso:
        return jsonify([])

    # Lấy phần ngày (YYYY-MM-DD)
    start_date = start_date_iso[:10]
    end_date = end_date_iso[:10]

    events_from_db = get_events_by_range(start_date, end_date)

    fullcalendar_events = []
    for e in events_from_db:
        event_dict = {
            'id': e['id'],
            'title': e['name'],
            'start': e['start'],
            # Tạo URL để chuyển đến trang Edit. prev_date dùng để quay lại đúng ngày trên lịch sau khi sửa.
            'url': url_for('edit', id=e['id'], prev_date=e['start'].split('T')[0])
        }
        if e['end']:
            event_dict['end'] = e['end']

        fullcalendar_events.append(event_dict)

    return jsonify(fullcalendar_events)


@app.route("/api/check_reminders", methods=["GET"])
def api_check_reminders():
    due_reminders = check_reminders()
    return jsonify(due_reminders)


@app.route("/export_json")
def export_json():
    events_data = get_all_events()

    json_string = json.dumps(events_data, indent=4, ensure_ascii=False, default=str)

    response = current_app.response_class(
        response=json_string,
        mimetype='application/json',
        headers={"Content-Disposition": "attachment; filename=events_export.json"}
    )
    return response


@app.route("/export_ics")
def export_ics():
    cal = Calendar()
    cal.add('prodid', '-//Lịch Thông Minh//example.com//')
    cal.add('version', '2.0')

    events_data = get_all_events()

    for event_row in events_data:
        event = Event()
        event.add('summary', event_row['name'])

        try:
            start_dt = datetime.fromisoformat(event_row['start']).replace(tzinfo=LOCAL_TIMEZONE)
            event.add('dtstart', vDatetime(start_dt))

            if event_row['end']:
                end_dt = datetime.fromisoformat(event_row['end']).replace(tzinfo=LOCAL_TIMEZONE)
                event.add('dtend', vDatetime(end_dt))
            else:
                end_dt = start_dt + timedelta(hours=1)
                event.add('dtend', vDatetime(end_dt))

            if event_row['reminder_minutes'] and event_row['reminder_minutes'] > 0:
                alarm = Event()
                alarm.add('action', 'DISPLAY')
                alarm.add('description', f"NHẮC NHỞ: {event_row['name']}")
                trigger_delta = timedelta(minutes=-event_row['reminder_minutes'])
                alarm.add('trigger', trigger_delta)
                event.add_component(alarm)

            if event_row['location']:
                event.add('location', event_row['location'])

            cal.add_component(event)

        except Exception as e:
            print(f"Lỗi khi xử lý sự kiện ID {event_row['id']}: {e}")
            continue

    ics_string = cal.to_ical()

    response = current_app.response_class(
        response=ics_string,
        mimetype='text/calendar',
        headers={"Content-Disposition": "attachment; filename=events_export.ics"}
    )
    return response


if __name__ == "__main__":
    app.run(debug=True)