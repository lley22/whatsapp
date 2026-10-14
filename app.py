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
        self.resize(850, 420)
        self.setAcceptDrops(True) # 启用系统级多文件拖拽
        
        # 内置固定的便携版浏览器地址与替换目标路径
        self.chrome_exe_path = r"C:\Users\Administrator\Desktop\GoogleChromePortable\GoogleChromePortable.exe"
        self.target_replace_dir = r"C:\Users\Administrator\Desktop\GoogleChromePortable\Data\profile\Default"
        
        self.cache_root = os.path.join(os.getcwd(), "whatsapp_runtime_env")
        if not os.path.exists(self.cache_root):
            os.makedirs(self.cache_root)
            
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 提示文本保持一致
        self.tip_label = QLabel("将 .bin（或 .zip）打包文件拖放到本窗口，左键点击文件可刷新右侧子页面数据。")
        self.tip_label.setStyleSheet("color: #000000; font-family: 'Microsoft YaHei'; font-size: 13px; padding-bottom: 5px;")
        main_layout.addWidget(self.tip_label)
        
        # --- 🟢 核心重构：左右双屏无缝联动架构（100%防止排版错乱挤压） ---
        tables_layout = QHBoxLayout()
        tables_layout.setSpacing(5) # 紧凑贴合
        
        # 1. 左侧表格：文件父页面 (占 25% 宽度分屏比例)
        self.left_table = QTableWidget(0, 1)
        self.left_table.setHorizontalHeaderLabels(["文件"])
        self.left_table.setShowGrid(True)
        self.left_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.left_table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #eaeaea; font-weight: bold; }")
        # 限制最大横向宽度占整体的 25% 大约 210 像素
        self.left_table.setFixedWidth(210) 
        
        # 2. 右侧表格：子页面数据、状态、操作联合展区 (占 75% 宽度分屏比例)
        self.right_table = QTableWidget(0, 3)
        self.right_table.setHorizontalHeaderLabels(["数据", "状态", "操作"])
        self.right_table.setShowGrid(True)
        self.right_table.setAlternatingRowColors(True)
        # 让右侧的三栏完全均分等宽（每栏各占 25% 比例位置）
        self.right_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.right_table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #eaeaea; font-weight: bold; }")
        
        # 将两个表格塞入主窗口布局
        tables_layout.addWidget(self.left_table)
        tables_layout.addWidget(self.right_table)
        main_layout.addLayout(tables_layout)
        
        # 监听左侧表格的左键点击切换联动信号
        self.left_table.itemClicked.connect(self.on_left_item_clicked)
        
        # 开启左侧表格的右键菜单策略
        self.left_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.left_table.customContextMenuRequested.connect(self.show_left_context_menu)
        
        # 全局留档缓存映射数据结构
        self.archive_data_map = {}

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        # 循环依次处理拉入的每一个包文件
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.zip') or file_path.lower().endswith('.bin'):
                self.process_backup_file(file_path)

    # 深度拷贝覆盖函数
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

    # 处理拉入包：第一栏显示纯文件名，并在后台静默离线检索多Profile特征
    def process_backup_file(self, file_path):
        pure_filename = os.path.basename(file_path)
        safe_name = pure_filename.replace('.', '_')
        
        row = self.left_table.rowCount()
        temp_extract_dir = os.path.join(self.cache_root, f"env_{safe_name}_{row}")
        
        try:
            # 1. 解压过渡
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            
            # 101种文件夹名字特征匹配集
            valid_profile_names = {"default"}
            for i in range(1, 101):
                valid_profile_names.add(f"profile {i}")
            
            # 2. 深度深挖里面所有的 Profile 目录
            found_profiles_list = []
            for dirpath, dirnames, filenames in os.walk(temp_extract_dir):
                current_folder_name = os.path.basename(dirpath).lower()
                if current_folder_name in valid_profile_names:
                    found_profiles_list.append(dirpath)
            
            if not found_profiles_list:
                found_profiles_list.append(temp_extract_dir)

            # 3. 依次对里面的每一个独立子环境执行底层 leveldb 离线数据翻阅
            profile_data_list = []
            for profile_path in found_profiles_list:
                env_name = os.path.basename(profile_path)
                if env_name == os.path.basename(temp_extract_dir):
                    env_name = "Default"
                
                is_valid = False
                for dirpath, dirnames, filenames in os.walk(profile_path):
                    if "local storage" in dirpath.lower() and "leveldb" in dirpath.lower():
                        for f in filenames:
                            if f.lower().endswith('.log') or f.lower().endswith('.ldb') or f.lower().endswith('.localstorage'):
                                try:
                                    with open(os.path.join(dirpath, f), 'rb') as db_file:
                                        if b'whatsapp' in db_file.read() or b'://whatsapp.com' in db_file.read():
                                            is_valid = True
                                            break
                                except:
                                    pass
                    if is_valid: break
                
                status_str = "已导入打开" if is_valid else "失败：未甄别到登录数据"
                profile_data_list.append({
                    "name": env_name,
                    "path": profile_path,
                    "status": status_str,
                    "valid": is_valid
                })

            # 4. 在左侧表格写入干净的文件名
            self.left_table.insertRow(row)
            file_item = QTableWidgetItem(pure_filename)
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
            self.left_table.setItem(row, 0, file_item)
            
            # 5. 将解析出来的信息完好留档
            self.archive_data_map[row] = {
                "profiles": profile_data_list,
                "temp_dir": temp_extract_dir
            }
            
            # 🟢 自动用左键高亮点击当前刚拉入的这一行，让右侧子页面首次联动刷新
            self.left_table.setCurrentItem(file_item)
            self.on_left_item_clicked(file_item)

        except Exception as e:
            print(f"解压异常: {e}")
        
        QApplication.processEvents()

    # 🟢 核心联动交互：左键点击左侧的文件，右侧三列子页面瞬间清空并重组展现！
    def on_left_item_clicked(self, item):
        clicked_row = item.row()
        if clicked_row not in self.archive_data_map:
            return
            
        # 清空右侧表格旧数据
        self.right_table.setRowCount(0)
        
        # 获取该包留档存储的所有子 Profile 环境列表
        profiles = self.archive_data_map[clicked_row]["profiles"]
        
        # 🟢 疯狂吐出：有多少环境就在右侧等宽生成多少行！
        for idx, pf in enumerate(profiles):
            self.right_table.insertRow(idx)
            
            # 第二栏 数据
            data_item = QTableWidgetItem(pf["name"])
            data_item.setFlags(data_item.flags() & ~Qt.ItemIsEditable)
            self.right_table.setItem(idx, 0, data_item)
            
            # 第三栏 状态
            status_item = QTableWidgetItem(pf["status"])
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            if pf["valid"]:
                status_item.setForeground(Qt.darkGreen)
            else:
                status_item.setForeground(Qt.red)
            self.right_table.setItem(idx, 1, status_item)
            
            # 第四栏 操作（成功亮起进入按钮）
            if pf["valid"]:
                enter_btn = QPushButton("进入")
                enter_btn.setStyleSheet("padding: 2px 5px; font-weight: bold; background-color: #107c41; color: white;")
                enter_btn.clicked.connect(lambda checked=False, p=pf["path"]: self.launch_chrome(p))
                self.right_table.setCellWidget(idx, 2, enter_btn)
            else:
                fail_action = QTableWidgetItem("无")
                fail_action.setTextAlignment(Qt.AlignCenter)
                fail_action.setFlags(fail_action.flags() & ~Qt.ItemIsEditable)
                fail_action.setForeground(Qt.gray)
                self.right_table.setItem(idx, 2, fail_action)

    # 左侧表格右键菜单（支持删除整个包）
    def show_left_context_menu(self, pos: QPoint):
        item = self.left_table.itemAt(pos)
        if item is None: return
        row = item.row()
        
        menu = QMenu(self)
        delete_action = QAction("❌ 删除整个包并清理缓存", self)
        delete_action.triggered.connect(lambda: self.delete_archive_package(row))
        menu.addAction(delete_action)
        menu.exec(self.left_table.viewport().mapToGlobal(pos))

    # 物理执行包卸载
    def delete_archive_package(self, row):
