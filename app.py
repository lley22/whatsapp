import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QPushButton, QHeaderView, QMenu)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction
import core  # 🟢 引入动力车间

class WhatsAppBackupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("导入打包备份 WhatsApp")
        self.resize(850, 450)
        self.setAcceptDrops(True)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.tip_label = QLabel("将 .bin（或 .zip）打包文件拖放到本窗口，选中后右侧子页面将自动展开各 Profile 登录状态。")
        self.tip_label.setStyleSheet("color: #000000; font-family: 'Microsoft YaHei'; font-size: 13px; padding-bottom: 5px;")
        main_layout.addWidget(self.tip_label)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["文件", "数据", "状态", "操作"])
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #eaeaea; font-weight: bold; }")
        
        self.table.itemClicked.connect(self.on_item_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        main_layout.addWidget(self.table)
        self.archive_map = {}
        self.row_bindings = {}

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.zip', '.bin')): self.add_new_archive(file_path)

    def add_new_archive(self, file_path):
        archive_id = len(self.archive_map)
        res = core.analyze_zip(file_path, archive_id)
        if not res: return
        
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        file_item = QTableWidgetItem(res["pure_name"])
        file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, file_item)
        
        for col in (1, 2, 3):
            empty_item = QTableWidgetItem("")
            empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, col, empty_item)
            
        self.archive_map[row] = {"data": res, "is_open": False, "rows_count": 0}
        self.rebuild_row_bindings()

    def on_item_clicked(self, item):
        if item.column() != 0: return
        grid_row = item.row()
        if grid_row not in self.row_bindings: return
        
        parent_row = self.row_bindings[grid_row]["parent"]
        if grid_row != parent_row: return
        
        info = self.archive_map[parent_row]
        if info["is_open"]:
            for _ in range(info["rows_count"]): self.table.removeRow(parent_row + 1)
            info["is_open"] = False
            info["rows_count"] = 0
            self.rebuild_row_bindings()
            return
            
        profiles = info["data"]["profiles"]
        for idx, pf in enumerate(profiles):
            target_row = parent_row + 1 + idx
            self.table.insertRow(target_row)
            
            b_item = QTableWidgetItem("")
            b_item.setFlags(b_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(target_row, 0, b_item)
            
            data_item = QTableWidgetItem(pf["name"])
            data_item.setFlags(data_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(target_row, 1, data_item)
            
            status_item = QTableWidgetItem(pf["status"])
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            status_item.setForeground(Qt.darkGreen if pf["valid"] else Qt.red)
            self.table.setItem(target_row, 2, status_item)
            
            if pf["valid"]:
                btn = QPushButton("进入")
                btn.setStyleSheet("padding: 2px 5px; font-weight: bold; background-color: #107c41; color: white;")
                btn.clicked.connect(lambda checked=False, p=pf["path"]: self.launch_browser(p))
                self.table.setCellWidget(target_row, 3, btn)
            else:
                none_item = QTableWidgetItem("无")
                none_item.setTextAlignment(Qt.AlignCenter)
                none_item.setFlags(none_item.flags() & ~Qt.ItemIsEditable)
                none_item.setForeground(Qt.gray)
                self.table.setItem(target_row, 3, none_item)
                
        info["is_open"] = True
        info["rows_count"] = len(profiles)
        self.rebuild_row_bindings()

    def rebuild_row_bindings(self):
        self.row_bindings.clear()
        current_grid_row = 0
        for p_row, info in list(self.archive_map.items()):
            self.row_bindings[current_grid_row] = {"type": "parent", "parent": current_grid_row}
            parent_mapped = current_grid_row
            current_grid_row += 1
            if info["is_open"]:
                for _ in range(info["rows_count"]):
                    self.row_bindings[current_grid_row] = {"type": "child", "parent": parent_mapped}
                    current_grid_row += 1

    def show_context_menu(self, pos: QPoint):
        item = self.table.itemAt(pos)
        if item is None or item.column() != 0: return
        grid_row = item.row()
        if grid_row not in self.row_bindings: return
        
        parent_row = self.row_bindings[grid_row]["parent"]
        if grid_row != parent_row: return
        
        menu = QMenu(self)
        delete_action = QAction("❌ 删除整个包并清理缓存", self)
        delete_action.triggered.connect(lambda: self.delete_package(parent_row))
        menu.addAction(delete_action)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def delete_package(self, parent_row):
        info = self.archive_map[parent_row]
        core.shutil.rmtree(info["data"]["temp_dir"], ignore_errors=True)
        total_rows_to_del = 1 + (info["rows_count"] if info["is_open"] else 0)
        for _ in range(total_rows_to_del): self.table.removeRow(parent_row)
        del self.archive_map[parent_row]
        new_map = {}
        for idx, (k, v) in enumerate(self.archive_map.items()): new_map[idx] = v
        self.archive_map = new_map
        self.rebuild_row_bindings()

    def launch_browser(self, p_path):
        if not core.run_chrome(p_path):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"未找到浏览器，请检查桌面是否存在：\n{core.CHROME_EXE}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WhatsAppBackupApp()
    window.show()
    sys.exit(app.exec())
