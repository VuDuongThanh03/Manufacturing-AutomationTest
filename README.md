
| Thư mục | Nội dung |
|---|---|
| `log-analyzer/` | Đọc hàng loạt file log kiểm tra thiết bị, thống kê mã lỗi, xuất Excel và biểu đồ |
| `serial-simulator/` | Mô phỏng giao tiếp máy tính - thiết bị qua cổng Serial/COM bằng lệnh AT |
| `test-workbench/` | Phần mềm desktop nạp danh sách Test Case, chạy và hiển thị PASS/FAIL |

Yêu cầu: Python 3.10+. Mỗi thư mục có `requirements.txt` và README riêng.

```
cd log-analyzer
pip install -r requirements.txt
pytest
```
