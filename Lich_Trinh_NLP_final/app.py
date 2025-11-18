from flask import Flask, request, render_template, redirect, url_for
from database import init_db, add_event, get_events_by_date, get_event, update_event, delete_event
from datetime import datetime
import re

app = Flask(__name__)
init_db()


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

    return render_template("index.html", events=events, selected_date=selected_date)


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


if __name__ == "__main__":
    app.run(debug=True)