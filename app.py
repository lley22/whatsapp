import sys
import os
import zipfile
import shutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QLabel, QPushButton, QHeaderView, QFileDialog, QLineEdit, QMenu)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction

class WhatsAppManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WhatsApp 备份环境管理工具")
        self.resize(600, 450)
        self.setAcceptDrops(True)
        
        self.chrome_exe_path = ""
        self.cache_root = os.path.join(os.getcwd(), "whatsapp_runtime_env")
        if not os.path.exists(self.cache_root):
            os.makedirs(self.cache_root)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        browser_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("请选择或直接拖入 chrome.exe 的路径...")
        browser_layout.addWidget(self.path_input)
        
        self.btn_select_chrome = QPushButton("选择浏览器")
        self.btn_select_chrome.clicked.connect(self.select_chrome_dialog)
        browser_layout.addWidget(self.btn_select_chrome)
        main_layout.addLayout(browser_layout)
        
        self.tip_label = QLabel("提示：将 .bin 或 .zip 备份文件直接拖放到下方表格中。程序将自动解压状态。")
        self.tip_label.setStyleSheet("color: #666; font-size: 12px; padding: 2px;")
        main_layout.addWidget(self.tip_label)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["备份文件路径", "状态", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        main_layout.addWidget(self.table)
        
        self.row_env_mapping = {}

    def select_chrome_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择免安装 Chrome.exe", "", "Executable (*.exe)")
        if file_path:
            self.chrome_exe_path = file_path
            self.path_input.setText(file_path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith("chrome.exe"):
                self.chrome_exe_path = file_path
                self.path_input.setText(file_path)
                continue
            if file_path.lower().endswith('.zip') or file_path.lower().endswith('.bin'):
                self.process_backup_file(file_path)

    def process_backup_file(self, file_path):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        path_item = QTableWidgetItem(file_path)
        path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, path_item)
        
        status_item = QTableWidgetItem("正在解压...")
        status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 1, status_item)
        
        try:
            filename = os.path.basename(file_path).split('.')[0]
        except:
            filename = "archive"
            
        target_env_dir = os.path.join(self.cache_root, f"env_{filename}_{row}")
        
        if not self.extract_archive(file_path, target_env_dir):
            status_item.setText("失败：解压文件损坏")
            status_item.setForeground(Qt.red)
            return

        if self.verify_whatsapp_session(target_env_dir):
            status_item.setText("获取成功（已就绪）")
            status_item.setForeground(Qt.darkGreen)
            
            open_btn = QPushButton("打开浏览器进入")
            open_btn.clicked.connect(lambda checked=False, d=target_env_dir: self.launch_chrome(d))
            self.table.setCellWidget(row, 2, open_btn)
            self.row_env_mapping[row] = target_env_dir
        else:
            status_item.setText("失败：未检测到登录数据")
            status_item.setForeground(Qt.red)
            try:
                shutil.rmtree(target_env_dir, ignore_errors=True)
            except:
                pass

    def extract_archive(self, source, target):
        try:
            if os.path.exists(target):
                shutil.rmtree(target, ignore_errors=True)
            with zipfile.ZipFile(source, 'r') as zip_ref:
                zip_ref.extractall(target)
            return True
        except:
            return False

    def verify_whatsapp_session(self, root_dir):
        has_local_storage = False
        has_network_data = False
        for dirpath, dirnames, filenames in os.walk(root_dir):
            if "Local Storage" in dirpath or "Default" in dirnames:
                has_local_storage = True
            for f in filenames:
                if "manifest" in f.lower() or "lock" in f.lower() or "cookies" in f.lower():
                    has_network_data = True
        return has_local_storage or has_network_data

    def show_context_menu(self, pos: QPoint):
        item = self.table.itemAt(pos)
        if item is None:
            return
        row = item.row()
        menu = QMenu(self)
        delete_action = QAction("❌ 删除此项并清理缓存", self)
        delete_action.triggered.connect(lambda: self.delete_row(row))
        menu.addAction(delete_action)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def delete_row(self, row):
        if row in self.row_env_mapping:
            env_dir = self.row_env_mapping[row]
            shutil.rmtree(env_dir, ignore_errors=True)
            del self.row_env_mapping[row]
        self.table.removeRow(row)
        new_mapping = {}
        for old_row, path in self.row_env_mapping.items():
            if old_row > row:
                new_mapping[old_row - 1] = path
            else:
                new_mapping[old_row] = path
        self.row_env_mapping = new_mapping

    def launch_chrome(self, env_dir):
        chrome_exe = self.path_input.text().strip()
        if not chrome_exe or not os.path.exists(chrome_exe):
            self.tip_label.setText("【错误】请先在顶部指定或拖入有效的‘免安装 Chrome.exe’路径！")
            return
        cmd = f'start "" "{chrome_exe}" --user-data-dir="{env_dir}" --no-first-run --no-default-browser-check "https://whatsapp.com"'
        os.system(cmd)
        self.tip_label.setText("浏览器已成功拉起，正在进入 WhatsApp...")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WhatsAppManagerApp()
    window.show()
    sys.exit(app.exec())
