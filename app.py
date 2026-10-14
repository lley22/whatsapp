import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QPushButton, QHeaderView, QMenu)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction
import core  # 引入动力车间

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
        
        # 左右分屏联动布局：确保四栏各占完美的 25% 比例位置
        tables_layout = QHBoxLayout()
        tables_layout.setSpacing(5)
        
        # 1. 左侧表格：文件栏 (占整体 25% 宽度左右)
        self.left_table = QTableWidget(0, 1)
        self.left_table.setHorizontalHeaderLabels(["文件"])
        self.left_table.setShowGrid(True)
        self.left_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.left_table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #eaeaea; font-weight: bold; }")
        self.left_table.setFixedWidth(210) 
        
        # 2. 右侧表格：数据、状态、操作 (各占25%等宽比例)
        self.right_table = QTableWidget(0, 3)
        self.right_table.setHorizontalHeaderLabels(["数据", "状态", "操作"])
        self.right_table.setShowGrid(True)
        self.right_table.setAlternatingRowColors(True)
        self.right_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.right_table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #eaeaea; font-weight: bold; }")
        
        tables_layout.addWidget(self.left_table)
        tables_layout.addWidget(self.right_table)
        main_layout.addLayout(tables_layout)
        
        # 注册左键联动刷新信号
        self.left_table.itemClicked.connect(self.on_left_item_clicked)
        
        # 🟢 严格锁定：右键删除菜单只在左侧【文件】这一栏生效
        self.left_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.left_table.customContextMenuRequested.connect(self.show_left_context_menu)
        
        self.archive_data_map = {}

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.zip', '.bin')):
                row = self.left_table.rowCount()
                res = core.analyze_zip(file_path, row)
                if res:
                    self.left_table.insertRow(row)
                    # 🟢 完美渲染带有中文、数字、字母的压缩包名字
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
            # 🟢 状态严格显示：成功（绿字）或 失败（红字）
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

    # 🟢 严格限定：右键菜单绑定在【文件栏】
    def show_left_context_menu(self, pos: QPoint):
        item = self.left_table.itemAt(pos)
        if item is None: return
        row = item.row()
        
        menu = QMenu(self)
        delete_action = QAction("❌ 删除整个包并清理缓存", self)
        delete_action.triggered.connect(lambda: self.delete_archive_package(row))
        menu.addAction(delete_action)
        menu.exec(self.left_table.viewport().mapToGlobal(pos))

    # 一键物理清理本地缓存
    def delete_archive_package(self, row):
        if row in self.archive_data_map:
            shutil.rmtree(self.archive_data_map[row]["temp_dir"], ignore_errors=True)
            del self.archive_data_map[row]
            
        self.left_table.removeRow(row)
        self.right_table.setRowCount(0) # 实时同步清空右侧子页面
        
        # 对内存索引重新进行对轨排列
        new_map = {}
        for idx in range(self.left_table.rowCount()):
            for old_k, old_v in self.archive_data_map.items():
                if idx <= old_k:
                    new_map[idx] = old_v
                    break
        self.archive_data_map = new_map

    def launch_browser(self, p_path):
        if not core.run_chrome(p_path):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"未找到浏览器，请检查桌面是否存在：\n{core.CHROME_EXE}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WhatsAppBackupApp()
    window.show()
    sys.exit(app.exec())
