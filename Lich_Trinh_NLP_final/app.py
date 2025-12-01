from flask import Flask, request, render_template, redirect, url_for, jsonify, current_app
from database import init_db, add_event, get_events_by_date, get_event, update_event, delete_event, get_all_events
from datetime import datetime, timedelta
import re
import json

app = Flask(__name__)
init_db()


def check_reminders():
    """Kiểm tra sự kiện nào cần được nhắc nhở khi tải trang."""
    all_events = get_all_events()
    current_time = datetime.now()
    due_reminders = []

    for event in all_events:
        # Bỏ qua nếu không có thời gian nhắc nhở
        if not event['reminder_minutes'] or event['reminder_minutes'] <= 0:
            continue

        try:
            event_start_time = datetime.fromisoformat(event['start'])
            # Tính thời điểm cần nhắc nhở
            reminder_time = event_start_time - timedelta(minutes=event['reminder_minutes'])

            # Kiểm tra: Thời điểm nhắc nhở đã qua và sự kiện chưa bắt đầu (hoặc chỉ mới bắt đầu 1 phút)
            # Điều kiện này mô phỏng cửa sổ hiển thị pop-up khi người dùng truy cập
            if reminder_time <= current_time <= event_start_time + timedelta(minutes=1):
                # Đảm bảo sự kiện chưa kết thúc (hoặc đơn giản là chưa bắt đầu)
                if current_time < event_start_time:
                    due_reminders.append({
                        'name': event['name'],
                        'start': event['start'],
                        'reminder_time': reminder_time.strftime('%H:%M, %d/%m')
                    })
        except ValueError:
            continue

    return due_reminders


@app.route("/", methods=["GET", "POST"])
def index():
    events = []
    selected_date = None

    # 1. Kiểm tra 'date' từ query parameter (khi quay lại từ trang sửa/xóa)
    selected_date = request.args.get("date")

    # 2. Kiểm tra date trong POST form (khi người dùng nhấn nút 'Xem')
    if request.method == "POST":
        date_input = request.form.get("date")
        if date_input:
            selected_date = date_input

    # 3. Mặc định là ngày hiện tại
    if not selected_date:
        selected_date = datetime.now().strftime('%Y-%m-%d')

    events = get_events_by_date(selected_date)

    # 4. Kiểm tra nhắc nhở khi tải trang chính
    due_reminders = check_reminders()

    return render_template("index.html", events=events, selected_date=selected_date, due_reminders=due_reminders)


@app.route("/add", methods=["POST"])
def add():
    text = request.form["event_text"]
    name, dt_iso, reminder = parse_text(text)

    add_event(name, dt_iso, None, None, reminder)
    return redirect(url_for("index"))


def parse_text(text):
    # ... (Hàm parse_text giữ nguyên) ...
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
    # ... (Hết hàm parse_text giữ nguyên) ...


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    event = get_event(id)

    # Lấy ngày được chọn trên trang index để quay lại
    prev_date = request.args.get("prev_date")
    # Fallback: Nếu không có ngày nào được truyền, lấy ngày bắt đầu của sự kiện
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

        # Lấy ngày cần quay lại (từ hidden field)
        return_date = request.form.get("return_date")

        # Chuyển hướng về trang index với ngày đã chọn
        return redirect(url_for("index", date=return_date))

    return render_template("edit_event.html", event=event, prev_date=prev_date)


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    delete_event(id)
    # Lấy ngày đã chọn từ hidden field trong form xóa
    selected_date = request.form.get("selected_date")

    # Chuyển hướng về trang index với ngày đã chọn
    return redirect(url_for("index", date=selected_date))


# NEW ROUTE: Chức năng xuất dữ liệu ra JSON
@app.route("/export_json")
def export_json():
    events_data = get_all_events()

    # Chuyển đổi list of dicts sang JSON string
    json_string = json.dumps(events_data, indent=4, ensure_ascii=False)

    # Tạo Response với header Content-Disposition để trình duyệt tải về file
    response = current_app.response_class(
        response=json_string,
        mimetype='application/json',
        headers={"Content-Disposition": "attachment; filename=events_export.json"}
    )
    return response


if __name__ == "__main__":
    app.run(debug=True)