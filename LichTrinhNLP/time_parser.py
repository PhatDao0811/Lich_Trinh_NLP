from datetime import datetime, timedelta
from dateutil import parser

def parse_time(text):
    """
    Nhận vào chuỗi tiếng Việt, cố gắng trích xuất thời gian (ví dụ: 'ngày mai', 'lúc 12 giờ', v.v.)
    Trả về datetime hoặc None
    """
    text = text.lower()
    now = datetime.now()

    # Xử lý các từ phổ biến
    if "ngày mai" in text:
        base_time = now + timedelta(days=1)
    elif "hôm nay" in text:
        base_time = now
    elif "ngày kia" in text:
        base_time = now + timedelta(days=2)
    else:
        base_time = now

    # Tìm giờ (ví dụ: "12 giờ", "15h30")
    import re
    time_pattern = re.search(r"(\d{1,2})\s*(giờ|h)(\d{1,2})?", text)
    if time_pattern:
        hour = int(time_pattern.group(1))
        minute = int(time_pattern.group(3)) if time_pattern.group(3) else 0
        base_time = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return base_time

    # Nếu không có giờ cụ thể, thử dùng parser
    try:
        parsed = parser.parse(text, fuzzy=True, default=base_time)
        return parsed
    except Exception:
        return None
