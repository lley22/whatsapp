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
        
        # 锁死默认浏览器启动地址
        self.chrome_exe_path = r"C:\Users\Administrator\Desktop\GoogleChromePortable\GoogleChromePortable.exe"
        # 锁死需要被全选覆盖替换的目标路径
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
        
        # 🟢 env_map 现在存储每一行对应的具体文件夹路径，实现分别独立控制
        self.env_map = {}

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
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

    # 🟢 核心重构：支持同一个包内检测到多个 Profile 时，“分别拆分”渲染到表格中
    def process_backup_file(self, file_path):
        pure_filename = os.path.basename(file_path)
        safe_name = pure_filename.replace('.', '_')
        
        # 为了防止批量拖入导致临时目录冲突，每次随机或按行号生成临时解压目录
        temp_id = self.table.rowCount()
        temp_extract_dir = os.path.join(self.cache_root, f"env_{safe_name}_{temp_id}")
        
        try:
            # 1. 先把这个压缩包解压到一个独立的过渡文件夹里
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            
            # 生成需要匹配的 101 种文件夹名称特征集合（小写便于比对）
            valid_profile_names = {"default"}
            for i in range(1, 101):
                valid_profile_names.add(f"profile {i}")
            
            # 🟢 2. 遍历找出解压后目录里“所有”符合这 101 种特征的独立文件夹路径
            found_profiles_list = []
            for dirpath, dirnames, filenames in os.walk(temp_extract_dir):
                current_folder_name = os.path.basename(dirpath).lower()
                if current_folder_name in valid_profile_names:
                    found_profiles_list.append(dirpath)
            
            # 如果包里竟然一个有效的 Profile 文件夹都没找到，则把根目录当作唯一的源（兼容旧格式）
            if not found_profiles_list:
                found_profiles_list.append(temp_extract_dir)

            # 🟢 3. “分别选”逻辑：遍历刚刚捞出来的每一个独立环境，分别在表格里渲染出一行！
            for profile_path in found_profiles_list:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # 获取它具体是哪个环境的名字，比如叫 Default 还是 Profile 1
                env_name = os.path.basename(profile_path)
                # 拼接显示：包名 (对应的环境名)，例如：张三.zip (Profile 1)
                display_name = f"{pure_filename} ({env_name})" if len(found_profiles_list) > 1 or env_name != os.path.basename(temp_extract_dir) else pure_filename
                
                path_item = QTableWidgetItem(display_name)
                path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 0, path_item)
                
                status_item = QTableWidgetItem("正在甄别...")
                status_item.setTextAlignment(Qt.AlignCenter)
                status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 1, status_item)
                
                # 🟢 4. 就地对该环境文件夹的底层 LevelDB 执行离线翻阅甄别
                is_valid_whatsapp_session = False
                for dirpath, dirnames, filenames in os.walk(profile_path):
                    if "local storage" in dirpath.lower() and "leveldb" in dirpath.lower():
                        for f in filenames:
                            if f.lower().endswith('.log') or f.lower().endswith('.ldb') or f.lower().endswith('.localstorage'):
                                db_file_path = os.path.join(dirpath, f)
                                try:
                                    with open(db_file_path, 'rb') as db_file:
                                        if b'whatsapp' in db_file.read() or b'://whatsapp.com' in db_file.read():
                                            is_valid_whatsapp_session = True
                                            break
                                except:
                                    pass
                    if is_valid_whatsapp_session:
                        break
                
                # 根据甄别结果，独立更新这一行的状态和操作按钮
                if is_valid_whatsapp_session:
                    status_item.setText("已导入打开")
                    status_item.setForeground(Qt.darkGreen)
                    
                    open_btn = QPushButton("打开浏览器进入")
                    open_btn.setStyleSheet("padding: 2px 10px; font-family: 'Microsoft YaHei';")
                    # 🟢 将这一行绑定到它专属的 profile_path，实现精准分别替换
                    open_btn.clicked.connect(lambda checked=False, p=profile_path: self.launch_chrome(p))
                    self.table.setCellWidget(row, 2, open_btn)
                    
                    # 记录该行对应的特定独立环境源路径
                    self.env_map[row] = profile_path
                else:
                    status_item.setText("失败：未甄别到登录数据")
                    status_item.setForeground(Qt.red)
                    
        except Exception as e:
            pass
        
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
            self.launch_chrome(self.env_map[row])

    # 🟢 5. 分别激活覆盖替换：只有当你操作某一特定行时，程序才会把该行锁定的独立数据全选替换过去！
    def launch_chrome(self, specific_profile_path):
        if not os.path.exists(self.chrome_exe_path):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"未找到浏览器，请确保桌面路径正确：\n{self.chrome_exe_path}")
            return
            
        try:
            # 强制安全清理旧目标，确保全新无污染
            if os.path.exists(self.target_replace_dir):
                shutil.rmtree(self.target_replace_dir, ignore_errors=True)
        except:
            pass
            
        # 🟢 精准执行当前行的单独全选覆盖替换
        self.copy_folder_contents(specific_profile_path, self.target_replace_dir)
            
        # 启动浏览器，并且完美保持你要求的初始最干净状态启动！
        cmd = f'start "" "{self.chrome_exe_path}" --no-first-run --no-default-browser-check "https://://whatsapp.com"'
        os.system(cmd)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WhatsAppBackupApp()
    window.show()
    sys.exit(app.exec())
