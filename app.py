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
        # 窗口标题完美保持不变
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
        
        # 左右分屏联动布局：四栏格子线分明，横向完美均分 25% 比例
        tables_layout = QHBoxLayout()
        tables_layout.setSpacing(5)
        
        # 1. 左侧表格：文件栏 (占整体宽度的 25% 左右)
        self.left_table = QTableWidget(0, 1)
        self.left_table.setHorizontalHeaderLabels(["文件"])
        self.left_table.setShowGrid(True)
        self.left_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.left_table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #eaeaea; font-weight: bold; }")
        self.left_table.setFixedWidth(210) 
        
        # 2. 右侧表格：数据、状态、操作联合子展区 (各栏目占 25% 的等宽比例位置)
        self.right_table = QTableWidget(0, 3)
        self.right_table.setHorizontalHeaderLabels(["数据", "状态", "操作"])
        self.right_table.setShowGrid(True)
        self.right_table.setAlternatingRowColors(True)
        self.right_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.right_table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #eaeaea; font-weight: bold; }")
        
        tables_layout.addWidget(self.left_table)
        tables_layout.addWidget(self.right_table)
        main_layout.addLayout(tables_layout)
        
        # 🟢 联动核心：左键点击左侧行，触发右侧子页面刷新
        self.left_table.itemClicked.connect(self.on_left_item_clicked)
        
        # 🟢 严格限定：右键删除菜单只在左侧【文件】这一栏生效
        self.left_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.left_table.customContextMenuRequested.connect(self.show_left_context_menu)
        
        self.archive_data_map = {}

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        # 支持同时圈选、批量将多个包拉入下面窗口中排队处理
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.zip', '.bin')):
                row = self.left_table.rowCount()
                res = core.analyze_zip(file_path, row)
                if res:
                    self.left_table.insertRow(row)
                    # 写入第一栏：保持展现纯文件名
                    item = QTableWidgetItem(res["pure_name"])
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.left_table.setItem(row, 0, item)
                    self.archive_data_map[row] = res
                    
                    # 自动高亮选中当前拉入的行并联动刷新右侧
                    self.left_table.setCurrentItem(item)
                    self.on_left_item_clicked(item)

    # 🟢 左键联动刷新右侧子页面数据
    def on_left_item_clicked(self, item):
        clicked_row = item.row()
        if clicked_row not in self.archive_data_map: return
        self.right_table.setRowCount(0)
        
        profiles = self.archive_data_map[clicked_row]["profiles"]
        for idx, pf in enumerate(profiles):
            self.right_table.insertRow(idx)
            
            # 第二栏 数据 (显示 Default 或 Profile 1-100 有多少显示多少)
            data_item = QTableWidgetItem(pf["name"])
            data_item.setFlags(data_item.flags() & ~Qt.ItemIsEditable)
            self.right_table.setItem(idx, 0, data_item)
            
            # 第三栏 状态 (只显示“成功”或“失败”)
            status_item = QTableWidgetItem(pf["status"])
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            status_item.setForeground(Qt.darkGreen if pf["valid"] else Qt.red)
            self.right_table.setItem(idx, 1, status_item)
            
            # 第四栏 操作 (显示进入按钮)
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

    # 🟢 右键菜单只绑定在【文件】这一栏生效
    def show_left_context_menu(self, pos: QPoint):
        item = self.left_table.itemAt(pos)
        if item is None: return
        row = item.row()
        
        menu = QMenu(self)
        delete_action = QAction("❌ 删除整个包并清理缓存", self)
        delete_action.triggered.connect(lambda: self.delete_archive_package(row))
        menu.addAction(delete_action)
        menu.exec(self.left_table.viewport().mapToGlobal(pos))

    # 一键删除整包，并在后台同步进行临时缓存物理销毁
    def delete_archive_package(self, row):
        if row in self.archive_data_map:
            shutil.rmtree(self.archive_data_map[row]["temp_dir"], ignore_errors=True)
            del self.archive_data_map[row]
            
        self.left_table.removeRow(row)
        self.right_table.setRowCount(0) # 同步将右边区域数据清空
        
        # 重排内存里的轨道索引关系
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
