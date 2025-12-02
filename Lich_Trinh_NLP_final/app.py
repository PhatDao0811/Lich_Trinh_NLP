from flask import Flask, request, render_template, redirect, url_for, jsonify, current_app
# NEW IMPORT: dateutil để phân tích ngôn ngữ tự nhiên về ngày giờ
from dateutil.parser import parse
from database import init_db, add_event, get_events_by_date, get_event, update_event, delete_event, get_all_events, \
    get_events_by_range
from datetime import datetime, timedelta
import re
import json
from icalendar import Calendar, Event, vDatetime
from pytz import timezone

app = Flask(__name__)
init_db()

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

            if reminder_time <= current_time <= event_start_time + timedelta(minutes=1):
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


@app.route("/", methods=["GET", "POST"])
def index():
    selected_date = datetime.now().strftime('%Y-%m-%d')
    return render_template("index.html", selected_date=selected_date)


@app.route("/add", methods=["POST"])
def add():
    text = request.form["event_text"]
    name, dt_iso, reminder = parse_text(text)

    add_event(name, dt_iso, None, None, reminder)
    return redirect(url_for("index"))


# HÀM PARSE_TEXT ĐÃ CẬP NHẬT DÙNG dateutil
def parse_text(text):
    now = datetime.now()
    reminder = 10

    # 1. Khởi tạo giá trị mặc định cho dateutil
    # Nếu không tìm thấy ngày, nó sẽ dùng ngày hôm nay. Nếu không tìm thấy giờ, nó sẽ dùng giờ hiện tại.
    dt_default = datetime(now.year, now.month, now.day, now.hour, now.minute)

    parsed_dt = None

    # Cố gắng Parse ngày tháng bằng dateutil
    try:
        # fuzzy=True cho phép bỏ qua các từ không liên quan. dayfirst=True ưu tiên format ngày/tháng.
        # dateutil xử lý các từ khóa như 'tomorrow', 'next week', 'Friday', v.v.
        parsed_dt = parse(text, default=dt_default, fuzzy=True, dayfirst=True)
    except Exception:
        pass

        # 2. Sử dụng Regex để lọc Tên sự kiện (dựa trên các chuỗi ngày/giờ thường gặp)
    # Chúng ta sử dụng regex để loại bỏ các phần có vẻ là ngày/giờ khỏi tên sự kiện.

    # Regex cho: 10h30, 10:30
    time_pattern = r"(?:(\d{1,2}):(\d{2}))?|(\d{1,2})h\s*(\d{2})"
    # Regex cho: 20/12/2025, 20/12
    date_pattern = r"(\d{1,2})\/(\d{1,2})(?:\/(\d{4}))?"
    # Regex cho: ngày mai, tuần sau, thứ hai, etc.
    relative_words_pattern = r"(?:ngày mai|sáng mai|chiều mai|ngày kia|tuần sau|thứ hai|thứ ba|thứ tư|thứ năm|thứ sáu|thứ bảy|chủ nhật|hôm sau|hôm nay|hôm trước|sáng nay|sáng mốt|sáng kia|sáng ngày kia|sáng kìa|chiều nay|chiều mai|chiều mốt|tối nay|tối mai|tối mốt|tối ngày kia|mai|tối|sáng|chiều)\s*"
    # Regex cho: vào lúc, lúc, ngày, vào
    time_phrases = r"(?:vào\s+lúc|lúc|vào\s+thời\s+điểm|ngày|vào|)"

    # Regex tổng hợp để bắt các chuỗi ngày/giờ
    full_pattern = rf"(\s*{time_phrases}\s*(?:{time_pattern}|{date_pattern}|{relative_words_pattern}))"

    # Lọc tên sự kiện: loại bỏ phần ngày tháng đã tìm thấy bằng regex
    name = re.sub(full_pattern, '', text, 0, re.IGNORECASE).strip()

    # Xử lý trường hợp tên sự kiện quá ngắn hoặc bị loại bỏ hết
    if not name:
        name = text  # Dùng lại text gốc
        # Lọc lại với một regex đơn giản hơn nếu cần, hoặc gán tên mặc định
        if not name:
            name = "Sự kiện không tên"

    # 3. Kết quả cuối cùng
    if parsed_dt:
        # Nếu dateutil parse thành công, sử dụng kết quả này
        dt_iso = parsed_dt.isoformat(timespec="minutes")
    else:
        # Nếu dateutil thất bại (rất hiếm khi xảy ra), dùng thời gian hiện tại
        dt_iso = now.isoformat(timespec="minutes")

    # Gán tên sự kiện bị lỗi nếu ngày/giờ không tìm thấy, chỉ để báo hiệu cho người dùng
    # if dt_iso == now.isoformat(timespec="minutes") and name != "Sự kiện không tên":
    #     name = "[LỖI PARSE NGÀY] " + name

    return name, dt_iso, reminder


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    event = get_event(id)

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

        if return_date == 'list_all':
            return redirect(url_for("list_all"))
        else:
            return redirect(url_for("index", date=return_date))

    return render_template("edit_event.html", event=event, prev_date=prev_date)


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    delete_event(id)
    selected_date = request.form.get("selected_date")

    if selected_date == 'list_all':
        return redirect(url_for("list_all"))
    else:
        return redirect(url_for("index", date=selected_date))


@app.route("/list_all", methods=["GET", "POST"])
def list_all():
    all_events = get_all_events()

    sorted_events = sorted(all_events, key=lambda x: x['start'])

    return render_template("all_events.html", events=sorted_events)


@app.route("/api/events")
def events_feed():
    start_date_iso = request.args.get('start')
    end_date_iso = request.args.get('end')

    if not start_date_iso or not end_date_iso:
        return jsonify([])

    start_date = start_date_iso[:10]
    end_date = end_date_iso[:10]

    events_from_db = get_events_by_range(start_date, end_date)

    fullcalendar_events = []
    for e in events_from_db:
        event_dict = {
            'id': e['id'],
            'title': e['name'],
            'start': e['start'],
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