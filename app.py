import sys
import os
import zipfile
import shutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QLabel, QPushButton, QHeaderView, QMenu)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction

class WhatsAppBackupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # 完美锁定原图窗口标题不变
        self.setWindowTitle("导入打包备份 WhatsApp")
        self.resize(750, 420)
        self.setAcceptDrops(True) # 启用系统级拖拽
        
        # 内置固定的便携版浏览器地址
        self.chrome_exe_path = r"C:\Users\Administrator\Desktop\GoogleChromePortable\GoogleChromePortable.exe"
        
        self.cache_root = os.path.join(os.getcwd(), "whatsapp_runtime_env")
        if not os.path.exists(self.cache_root):
            os.makedirs(self.cache_root)
            
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 完美复刻原图的提示文本
        self.tip_label = QLabel("将 .bin（或 .zip）打包文件拖放到本窗口，选中后点执行自动解压并登录。")
        self.tip_label.setStyleSheet("color: #000000; font-family: 'Microsoft YaHei'; font-size: 13px; padding-bottom: 5px;")
        main_layout.addWidget(self.tip_label)
        
        # 完美复刻原图的等宽网格表格
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["备份文件", "状态", "操作"])
        
        # 开启原生浅灰色横竖网格线分割
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        
        # 均分比例：每一列精准占据三分之一，且支持多文件时自动下拉滚动
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #eaeaea; font-weight: bold; }")
        
        # 开启右键菜单策略
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # 双击表格行同样可以触发启动
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        main_layout.addWidget(self.table)
        
        self.env_map = {}

    # 彻底解决死锁的拖拽捕获机制
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        # 循环迭代：支持同时圈选、批量拉入无数个备份文件到下面窗口
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.zip') or file_path.lower().endswith('.bin'):
                self.process_backup_file(file_path)

    # 核心解压与数据渲染
    def process_backup_file(self, file_path):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # 提取纯文件名，隐藏累赘路径，只显示 xx.zip 或 xx.bin
        pure_filename = os.path.basename(file_path)
        
        # 写入第一列
        path_item = QTableWidgetItem(pure_filename)
        path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable) # 禁止手动编辑
        self.table.setItem(row, 0, path_item)
        
        # 写入第二列：正在解压
        status_item = QTableWidgetItem("正在解压...")
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 1, status_item)
        
        safe_name = pure_filename.replace('.', '_')
        target_env_dir = os.path.join(self.cache_root, f"env_{safe_name}_{row}")
        
        try:
            if os.path.exists(target_env_dir):
                shutil.rmtree(target_env_dir, ignore_errors=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_env_dir)
            
            # 完美复刻原图的状态文字：“已导入打开”
            status_item.setText("已导入打开")
            status_item.setForeground(Qt.darkGreen)
            
            # 第三列动态生成操作按钮
            open_btn = QPushButton("打开浏览器进入")
            open_btn.setStyleSheet("padding: 2px 10px; font-family: 'Microsoft YaHei';")
            open_btn.clicked.connect(lambda checked=False, d=target_env_dir: self.launch_chrome(d))
            self.table.setCellWidget(row, 2, open_btn)
            
            # 建立行号映射
            self.env_map[row] = target_env_dir
        except:
            status_item.setText("失败：解压损坏")
            status_item.setForeground(Qt.red)
        
        QApplication.processEvents()

    # 右键菜单弹出
    def show_context_menu(self, pos: QPoint):
        item = self.table.itemAt(pos)
        if item is None: return
        row = item.row()
        
        menu = QMenu(self)
        delete_action = QAction("❌ 删除此项并清理缓存", self)
        delete_action.triggered.connect(lambda: self.delete_row(row))
        menu.addAction(delete_action)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    # 执行行删除与物理本地缓存一键清理
    def delete_row(self, row):
        if row in self.env_map:
            shutil.rmtree(self.env_map[row], ignore_errors=True)
            del self.env_map[row]
        self.table.removeRow(row)
        
        # 重排后续行索引映射
        new_map = {}
        for old_row, path in self.env_map.items():
            if old_row > row:
                new_map[old_row - 1] = path
            else:
                new_map[old_row] = path
        self.env_map = new_map

    # 双击行触发
    def on_item_double_clicked(self, item):
        row = item.row()
        if row in self.env_map:
            self.launch_chrome(self.env_map[row])

    # 启动锁死的便携浏览器环境
    def launch_chrome(self, env_dir):
        if not os.path.exists(self.chrome_exe_path):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"未找到浏览器，请确保桌面路径正确：\n{self.chrome_exe_path}")
            return
            
        # 🟢 核心改动：彻底剔除 --user-data-dir 参数。
        # 这样每次双击或点击按钮唤醒浏览器时，完全不读取旧环境，强制为最开始的纯净白纸状态。
        cmd = f'start "" "{self.chrome_exe_path}" --no-first-run --no-default-browser-check "https://whatsapp.com"'
        os.system(cmd)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WhatsAppBackupApp()
    window.show()
    sys.exit(app.exec())
