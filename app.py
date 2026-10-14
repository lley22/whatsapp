import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QPushButton, QHeaderView)
from PySide6.QtCore import Qt
import core  # 🟢 引入动力车间，实现完美分离

class WhatsAppBackupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("导入打包备份 WhatsApp")
        self.resize(850, 420)
        self.setAcceptDrops(True)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.tip_label = QLabel("将 .bin（或 .zip）打包文件拖放到本窗口，左键点击文件可刷新右侧子页面数据。")
        self.tip_label.setStyleSheet("color: #000000; font-family: 'Microsoft YaHei'; font-size: 13px; padding-bottom: 5px;")
        main_layout.addWidget(self.tip_label)
        
        # 🟢 左右分屏联动：完美实现四栏各占 25% 比例位置，永不挤压串行！
        tables_layout = QHBoxLayout()
        tables_layout.setSpacing(5)
        
        # 左侧表格：文件 (占25%宽度)
        self.left_table = QTableWidget(0, 1)
        self.left_table.setHorizontalHeaderLabels(["文件"])
        self.left_table.setShowGrid(True)
        self.left_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.left_table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #eaeaea; font-weight: bold; }")
        self.left_table.setFixedWidth(210) 
        
        # 右侧表格：数据、状态、操作 (各占25%等宽比例)
        self.right_table = QTableWidget(0, 3)
        self.right_table.setHorizontalHeaderLabels(["数据", "状态", "操作"])
        self.right_table.setShowGrid(True)
        self.right_table.setAlternatingRowColors(True)
        self.right_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.right_table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #eaeaea; font-weight: bold; }")
        
        tables_layout.addWidget(self.left_table)
        tables_layout.addWidget(self.right_table)
        main_layout.addLayout(tables_layout)
        
        self.left_table.itemClicked.connect(self.on_left_item_clicked)
        self.archive_data_map = {}

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.zip', '.bin')):
                row = self.left_table.rowCount()
                res = core.analyze_zip(file_path, row) # 调用动力车间
                if res:
                    self.left_table.insertRow(row)
                    item = QTableWidgetItem(res["pure_name"])
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.left_table.setItem(row, 0, item)
                    self.archive_data_map[row] = res
                    self.left_table.setCurrentItem(item)
                    self.on_left_item_clicked(item)

    def on_left_item_clicked(self, item):
        clicked_row = item.row()
        if clicked_row not in self.archive_data_map: return
        self.right_table.setRowCount(0)
        
        profiles = self.archive_data_map[clicked_row]["profiles"]
        for idx, pf in enumerate(profiles):
            self.right_table.insertRow(idx)
            
            data_item = QTableWidgetItem(pf["name"])
            data_item.setFlags(data_item.flags() & ~Qt.ItemIsEditable)
            self.right_table.setItem(idx, 0, data_item)
            
            status_item = QTableWidgetItem(pf["status"])
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            status_item.setForeground(Qt.darkGreen if pf["valid"] else Qt.red)
            self.right_table.setItem(idx, 1, status_item)
            
            if pf["valid"]:
                btn = QPushButton("进入")
                btn.setStyleSheet("padding: 2px 5px; font-weight: bold; background-color: #107c41; color: white;")
                btn.clicked.connect(lambda checked=False, p=pf["path"]: self.launch_browser(p))
                self.right_table.setCellWidget(idx, 2, btn)
            else:
                fail_item = QTableWidgetItem("无")
                fail_item.setTextAlignment(Qt.AlignCenter)
                fail_item.setFlags(fail_item.flags() & ~Qt.ItemIsEditable)
                fail_item.setForeground(Qt.gray)
                self.right_table.setItem(idx, 2, fail_item)

    def launch_browser(self, p_path):
        if not core.run_chrome(p_path):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"未找到浏览器，请检查桌面是否存在：\n{core.CHROME_EXE}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WhatsAppBackupApp()
    window.show()
    sys.exit(app.exec())
