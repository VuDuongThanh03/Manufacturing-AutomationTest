# Device Communication Simulator

Mô phỏng việc máy tính kết nối với thiết bị qua cổng Serial/COM, gửi lệnh test dạng AT
và kiểm tra phản hồi. Gồm thiết bị giả lập, thư viện phía máy tính và giao diện Tkinter.

## Cách chạy (không cần phần cứng)

Mở 2 cửa sổ dòng lệnh:

```
pip install -r requirements.txt
python device_sim.py --tcp 5000
```

```
python gui.py
```

Trong giao diện, chọn cổng `socket://localhost:5000`, bấm **Kết nối** rồi **Chạy kịch bản**.
Hoặc dùng dòng lệnh:

```
python host.py --port socket://localhost:5000 AT AT+CHECK_FW AT+TEST=START
```

Thêm `--fault-rate 0.3` khi chạy `device_sim.py` để thiết bị thỉnh thoảng im lặng hoặc trả lời
sai cấu trúc, dùng để xem cách phần mềm xử lý timeout và lỗi.

## Chạy với cổng COM ảo

Tạo một cặp cổng COM ảo (ví dụ COM5 <-> COM6 bằng com0com), rồi:

```
python device_sim.py --port COM6
python host.py --port COM5 AT AT+SN?
```

Lưu ý: phần chạy qua cổng COM ảo chưa được kiểm thử tự động; các test trong `tests/` chạy qua TCP.

## Giao thức

Mỗi lệnh là một dòng kết thúc bằng `\r\n`. Thiết bị trả 0 hoặc nhiều dòng `KEY:value`,
rồi `OK` hoặc `ERROR`.

| Lệnh | Phản hồi |
|---|---|
| `AT` | `OK` |
| `AT+SN?` | `SN:DUT000001`, `OK` |
| `AT+CHECK_FW` | `FW:1.2.3`, `OK` |
| `AT+TEST=START` / `AT+TEST=STOP` | `TEST:RUNNING` / `TEST:STOPPED`, `OK` |
| `AT+TEST?` | `TEST:RUNNING` hoặc `TEST:IDLE`, `OK` |
| lệnh khác | `ERROR` |

Kết quả mỗi lệnh phía máy tính: `OK`, `ERROR`, `TIMEOUT` (hết thời gian chờ),
`BAD_RESPONSE` (phản hồi sai cấu trúc). Toàn bộ dữ liệu gửi/nhận được ghi vào `session.log`.

## Cấu trúc

- `device_sim.py`: thiết bị giả lập (`DeviceSimulator.handle` xử lý lệnh, tách khỏi phần truyền nhận)
- `host.py`: `SerialClient` gửi lệnh, xử lý timeout, ghi log
- `gui.py`: giao diện Tkinter
- `tests/`: unit test bằng pytest
