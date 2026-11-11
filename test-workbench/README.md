# Test Automation Workbench

Phần mềm desktop (PyQt5) nạp danh sách Test Case từ file JSON, chạy lần lượt và hiển thị
trạng thái WAITING / RUNNING / PASS / FAIL theo thời gian thực, xuất kết quả ra CSV.

## Cách chạy

```
pip install -r requirements.txt
python workbench.py sample_tests.json
pytest
```

Chạy không cần giao diện:

```
python runner.py sample_tests.json --csv result.csv
```

File mẫu có 5 test, trong đó 2 test cố ý FAIL (sai mã thoát và timeout) để minh hoạ.

## Định dạng Test Case

```json
{
  "id": "TC001",
  "name": "Kiểm tra phiên bản firmware",
  "command": "{python} -c \"print('FW:1.2.3')\"",
  "expect_exit_code": 0,
  "expect_regex": "FW:\d+\.\d+\.\d+",
  "timeout": 5.0
}
```

- `command`: lệnh cần chạy (chạy trực tiếp, không qua shell); `{python}` được thay bằng Python đang dùng
- `expect_exit_code`: mã thoát mong đợi, mặc định 0
- `expect_regex`: nếu có, output phải khớp biểu thức này
- `timeout`: số giây tối đa, mặc định 5

## Cấu trúc

- `runner.py`: đọc JSON, chạy test, xuất CSV (không phụ thuộc giao diện)
- `workbench.py`: giao diện PyQt5, chạy test trong `QThread` để không treo giao diện
- `tests/`: unit test bằng pytest
