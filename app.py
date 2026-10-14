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
        # 完美锁定窗口标题不变
        self.setWindowTitle("导入打包备份 WhatsApp")
        self.resize(750, 420)
        self.setAcceptDrops(True) # 启用系统级拖拽
        
        # 🟢 锁死默认浏览器启动地址
        self.chrome_exe_path = r"C:\Users\Administrator\Desktop\GoogleChromePortable\GoogleChromePortable.exe"
        # 🟢 锁死需要被全选覆盖替换的目标路径
        self.target_replace_dir = r"C:\Users\Administrator\Desktop\GoogleChromePortable\Data\profile\Default"
        
        self.cache_root = os.path.join(os.getcwd(), "whatsapp_runtime_env")
        if not os.path.exists(self.cache_root):
            os.makedirs(self.cache_root)
            
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 完美复刻原图提示
        self.tip_label = QLabel("将 .bin（或 .zip）打包文件拖放到本窗口，选中后点执行自动解压并登录。")
        self.tip_label.setStyleSheet("color: #000000; font-family: 'Microsoft YaHei'; font-size: 13px; padding-bottom: 5px;")
        main_layout.addWidget(self.tip_label)
        
        # 完美复刻原图等宽网格表格
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["备份文件", "状态", "操作"])
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #eaeaea; font-weight: bold; }")
        
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        main_layout.addWidget(self.table)
        self.env_map = {}

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.zip') or file_path.lower().endswith('.bin'):
                self.process_backup_file(file_path)

    # 深度拷贝覆盖函数：实现将 source 文件夹内的全部子文件和子文件夹全选覆盖到 target 目录
    def copy_folder_contents(self, source_dir, target_dir):
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        for item in os.listdir(source_dir):
            s = os.path.join(source_dir, item)
            d = os.path.join(target_dir, item)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d, ignore_errors=True)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

    # 核心解压、全选替换目标目录与二次离线甄别逻辑
    def process_backup_file(self, file_path):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        pure_filename = os.path.basename(file_path)
        
        path_item = QTableWidgetItem(pure_filename)
        path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, path_item)
        
        status_item = QTableWidgetItem("正在解压...")
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 1, status_item)
        
        safe_name = pure_filename.replace('.', '_')
        temp_extract_dir = os.path.join(self.cache_root, f"env_{safe_name}_{row}")
        
        try:
            # 1. 释放解压到临时过渡缓存目录
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            
            # 🟢 2. 核心重构：深挖包内的 Default 或 Profile 1-100 目录并全选替换到桌面便携浏览器路径
            found_profile_src = ""
            
            # 生成需要匹配的 101 种文件夹名称特征集合
            valid_profile_names = {"default"}
            for i in range(1, 101):
                valid_profile_names.add(f"profile {i}")
            
            # 在解压后的目录中递归查找这 101 种特定目标文件夹
            for dirpath, dirnames, filenames in os.walk(temp_extract_dir):
                current_folder_name = os.path.basename(dirpath).lower()
                if current_folder_name in valid_profile_names:
                    found_profile_src = dirpath
                    break
            
            # 🟢 如果在压缩包里找到了符合特征的文件夹，立刻执行“全选替换”到你的指定桌面路径！
            if found_profile_src:
                # 为了防止文件被浏览器占用引发错误，清空覆盖前强制尝试安全清理旧目标
                try:
                    if os.path.exists(self.target_replace_dir):
                        shutil.rmtree(self.target_replace_dir, ignore_errors=True)
                except:
                    pass
                # 执行无损覆盖替换
                self.copy_folder_contents(found_profile_src, self.target_replace_dir)
            else:
                # 备用兼容：万一别人直接把 Default 内部的文件乱包丢进来，没有外层文件夹，则把根目录视为数据源
                self.copy_folder_contents(temp_extract_dir, self.target_replace_dir)

            # 🟢 3. 二次甄别：在刚刚全选替换过去的桌面标准固定路径上，执行最深层的底层二进制数据翻阅
            is_valid_whatsapp_session = False
            
            for dirpath, dirnames, filenames in os.walk(self.target_replace_dir):
                if "local storage" in dirpath.lower() and "leveldb" in dirpath.lower():
                    for f in filenames:
                        if f.lower().endswith('.log') or f.lower().endswith('.ldb') or f.lower().endswith('.localstorage'):
                            db_file_path = os.path.join(dirpath, f)
                            try:
                                with open(db_file_path, 'rb') as db_file:
                                    content = db_file.read()
                                    if b'whatsapp' in content or b'://whatsapp.com' in content:
                                        is_valid_whatsapp_session = True
                                        break
                            except:
                                pass
                if is_valid_whatsapp_session:
                    break
            
            # 渲染最终的参考图复刻结果
            if is_valid_whatsapp_session:
                status_item.setText("已导入打开")
                status_item.setForeground(Qt.darkGreen)
                
                open_btn = QPushButton("打开浏览器进入")
                open_btn.setStyleSheet("padding: 2px 10px; font-family: 'Microsoft YaHei';")
                open_btn.clicked.connect(self.launch_chrome)
                self.table.setCellWidget(row, 2, open_btn)
                
                self.env_map[row] = self.target_replace_dir
            else:
                status_item.setText("失败：未甄别到登录数据")
                status_item.setForeground(Qt.red)
                
        except Exception as e:
            status_item.setText("失败：解压损坏")
            status_item.setForeground(Qt.red)
        
        QApplication.processEvents()

    def show_context_menu(self, pos: QPoint):
        item = self.table.itemAt(pos)
        if item is None: return
        row = item.row()
        
        menu = QMenu(self)
        delete_action = QAction("❌ 删除此项并清理缓存", self)
        delete_action.triggered.connect(lambda: self.delete_row(row))
        menu.addAction(delete_action)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def delete_row(self, row):
        if row in self.env_map:
            del self.env_map[row]
        self.table.removeRow(row)
        
        new_map = {}
        for old_row, path in self.env_map.items():
            if old_row > row:
                new_map[old_row - 1] = path
            else:
                new_map[old_row] = path
        self.env_map = new_map

    def on_item_double_clicked(self, item):
        row = item.row()
        if row in self.env_map:
            self.launch_chrome()

    # 启动关联的锁死初始便携浏览器
    def launch_chrome(self):
        if not os.path.exists(self.chrome_exe_path):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"未找到浏览器，请确保桌面路径正确：\n{self.chrome_exe_path}")
            return
            
        # 每次被双击或点击按钮唤醒时，完全保持你要求的初始最干净状态启动，并在浏览器中重定向至 WhatsApp 网页版
        cmd = f'start "" "{self.chrome_exe_path}" --no-first-run --no-default-browser-check "https://://whatsapp.com"'
        os.system(cmd)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WhatsAppBackupApp()
    window.show()
    sys.exit(app.exec())
