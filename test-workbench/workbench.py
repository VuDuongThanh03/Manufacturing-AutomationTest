"""Giao diện PyQt5: nạp file Test Case, bấm Run Test, xem trạng thái từng test.

Cách chạy:
    python workbench.py
"""
import sys

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
                             QMainWindow, QMessageBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from runner import PASS, TestResult, export_csv, load_test_cases, run_test_case

COLORS = {"PASS": "#c8f7c5", "FAIL": "#f7c5c5", "RUNNING": "#fff3b0", "WAITING": "#ffffff"}
COLUMNS = ["ID", "Tên test", "Trạng thái", "Thời gian (s)", "Ghi chú"]


class RunnerThread(QThread):
    """Chạy test ở luồng riêng để giao diện không bị treo."""
    started_case = pyqtSignal(int)
    finished_case = pyqtSignal(int, object)

    def __init__(self, cases):
        super().__init__()
        self.cases = cases

    def run(self):
        for row, case in enumerate(self.cases):
            self.started_case.emit(row)
            self.finished_case.emit(row, run_test_case(case))


class Workbench(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Automation Workbench")
        self.resize(860, 480)
        self.cases = []
        self.results: list[TestResult] = []
        self.thread = None

        self.load_btn = QPushButton("Nạp Test Case...")
        self.run_btn = QPushButton("Run Test")
        self.export_btn = QPushButton("Xuất kết quả CSV...")
        self.run_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.summary = QLabel("Chưa nạp test case")
        self.load_btn.clicked.connect(self.choose_file)
        self.run_btn.clicked.connect(self.run_tests)
        self.export_btn.clicked.connect(self.export)

        buttons = QHBoxLayout()
        for widget in (self.load_btn, self.run_btn, self.export_btn):
            buttons.addWidget(widget)
        buttons.addStretch()
        buttons.addWidget(self.summary)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout = QVBoxLayout()
        layout.addLayout(buttons)
        layout.addWidget(self.table)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file Test Case", "", "JSON (*.json)")
        if path:
            self.load_file(path)

    def load_file(self, path):
        try:
            self.cases = load_test_cases(path)
        except Exception as exc:  # file hỏng, thiếu trường, trùng ID...
            QMessageBox.critical(self, "Không đọc được file", str(exc))
            return
        self.table.setRowCount(len(self.cases))
        for row, case in enumerate(self.cases):
            self.table.setItem(row, 0, QTableWidgetItem(case.id))
            self.table.setItem(row, 1, QTableWidgetItem(case.name))
            self.set_status(row, "WAITING")
        self.run_btn.setEnabled(bool(self.cases))
        self.export_btn.setEnabled(False)
        self.summary.setText(f"{len(self.cases)} test case")

    def set_status(self, row, status, duration="", message=""):
        for col, text in ((2, status), (3, str(duration)), (4, message)):
            self.table.setItem(row, col, QTableWidgetItem(text))
        self.table.item(row, 2).setBackground(QColor(COLORS[status]))

    def run_tests(self):
        self.results = []
        for row in range(len(self.cases)):
            self.set_status(row, "WAITING")
        self.run_btn.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.thread = RunnerThread(self.cases)
        self.thread.started_case.connect(lambda row: self.set_status(row, "RUNNING"))
        self.thread.finished_case.connect(self.on_case_finished)
        self.thread.finished.connect(self.on_all_finished)
        self.thread.start()

    def on_case_finished(self, row, result):
        self.results.append(result)
        self.set_status(row, result.status, result.duration_s, result.message)

    def on_all_finished(self):
        passed = sum(r.status == PASS for r in self.results)
        self.summary.setText(f"Kết quả: {passed}/{len(self.results)} PASS")
        self.run_btn.setEnabled(True)
        self.load_btn.setEnabled(True)
        self.export_btn.setEnabled(True)

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Lưu kết quả", "result.csv", "CSV (*.csv)")
        if path:
            export_csv(self.results, path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Workbench()
    if len(sys.argv) > 1:  # cho phép: python workbench.py sample_tests.json
        window.load_file(sys.argv[1])
    window.show()
    sys.exit(app.exec_())
