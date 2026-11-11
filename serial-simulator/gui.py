"""Giao diện Tkinter: chọn cổng, baudrate, gửi lệnh test và xem log giao tiếp.

Cách chạy:
    python gui.py
"""
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from serial.tools import list_ports

from host import OK, SerialClient

DEFAULT_SCRIPT = "AT\nAT+SN?\nAT+CHECK_FW\nAT+TEST=START\nAT+TEST?\nAT+TEST=STOP"
BAUDRATES = ["9600", "19200", "38400", "57600", "115200"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Device Communication Simulator")
        self.geometry("760x520")
        self.client: SerialClient | None = None
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ports = [p.device for p in list_ports.comports()] + ["socket://localhost:5000"]
        ttk.Label(top, text="Cổng:").pack(side="left")
        self.port = ttk.Combobox(top, values=ports, width=26)
        self.port.set(ports[-1])
        self.port.pack(side="left", padx=4)
        ttk.Label(top, text="Baudrate:").pack(side="left")
        self.baud = ttk.Combobox(top, values=BAUDRATES, width=8)
        self.baud.set("115200")
        self.baud.pack(side="left", padx=4)
        ttk.Label(top, text="Timeout (s):").pack(side="left")
        self.timeout = ttk.Entry(top, width=5)
        self.timeout.insert(0, "1.0")
        self.timeout.pack(side="left", padx=4)
        self.connect_btn = ttk.Button(top, text="Kết nối", command=self.toggle_connection)
        self.connect_btn.pack(side="left", padx=8)

        body = ttk.Frame(self, padding=(8, 0, 8, 8))
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Kịch bản lệnh (mỗi dòng một lệnh):").pack(anchor="w")
        self.script = tk.Text(left, width=26, height=14)
        self.script.insert("1.0", DEFAULT_SCRIPT)
        self.script.pack()
        self.run_btn = ttk.Button(left, text="Chạy kịch bản", command=self.run_script,
                                  state="disabled")
        self.run_btn.pack(fill="x", pady=6)
        self.status = ttk.Label(left, text="Chưa kết nối")
        self.status.pack(anchor="w")

        self.log = scrolledtext.ScrolledText(body, state="disabled", font=("Consolas", 9))
        self.log.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.log.tag_config("err", foreground="red")

    def append_log(self, line: str):
        # Được gọi từ luồng phụ nên phải chuyển về luồng giao diện bằng after()
        def write():
            self.log.config(state="normal")
            self.log.insert("end", line + "\n", "err" if " !! " in line else "")
            self.log.see("end")
            self.log.config(state="disabled")
        self.after(0, write)

    def toggle_connection(self):
        if self.client:
            self.client.close()
            self.client = None
            self.connect_btn.config(text="Kết nối")
            self.run_btn.config(state="disabled")
            self.status.config(text="Đã ngắt kết nối")
            return
        try:
            self.client = SerialClient(self.port.get(), int(self.baud.get()),
                                       float(self.timeout.get()), "session.log")
        except Exception as exc:  # sai cổng, cổng đang bận, tham số không hợp lệ...
            messagebox.showerror("Không kết nối được", str(exc))
            return
        self.client.on_log = self.append_log
        self.connect_btn.config(text="Ngắt kết nối")
        self.run_btn.config(state="normal")
        self.status.config(text=f"Đã kết nối {self.port.get()}")

    def run_script(self):
        commands = self.script.get("1.0", "end").splitlines()
        self.run_btn.config(state="disabled")

        def worker():  # chạy ở luồng phụ để giao diện không bị treo khi chờ timeout
            results = self.client.run_script(commands)
            passed = sum(r.status == OK for r in results)
            self.after(0, lambda: self.status.config(
                text=f"Xong: {passed}/{len(results)} lệnh OK"))
            self.after(0, lambda: self.run_btn.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
