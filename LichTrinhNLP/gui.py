import tkinter as tk
from tkinter import messagebox
from nlp_module import understand_text

def handle_input():
    user_text = entry.get()
    if not user_text.strip():
        messagebox.showwarning("Cảnh báo", "Vui lòng nhập nội dung.")
        return

    result = understand_text(user_text)
    messagebox.showinfo("Kết quả", result.get("msg", "Không có phản hồi."))

    entry.delete(0, tk.END)

def run_gui():
    root = tk.Tk()
    root.title("Trợ lý lịch trình NLP")
    root.geometry("420x300")

    tk.Label(root, text="Nhập lệnh của bạn:", font=("Arial", 12)).pack(pady=10)
    global entry
    entry = tk.Entry(root, width=50)
    entry.pack(pady=10)

    tk.Button(root, text="Gửi", command=handle_input).pack(pady=10)
    root.mainloop()

if __name__ == "__main__":
    run_gui()
