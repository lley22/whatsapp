import sys
import os
import zipfile
import shutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QLabel, QPushButton, QHeaderView, QFileDialog, QLineEdit)
from PySide6.QtCore import Qt

class WhatsAppManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WhatsApp 备份环境管理工具")
        self.resize(850, 450)
        self.setAcceptDrops(True) # 启用拖拽
        
        # 默认便携版浏览器路径（可由用户选择更改）
        self.chrome_exe_path = ""
        # 自动解压释放的缓存根目录
        self.cache_root = os.path.join(os.getcwd(), "whatsapp_runtime_env")
        os.makedirs(self.cache_root, exist_ok=True)
        
        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # --- 顶部：免安装浏览器路径选择区域 ---
        browser_layout = QHBoxLayout()
        browser_layout.addWidget(QLabel("免安装Chrome路径:"))
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("请选择或拖入 chrome.exe 的路径...")
        browser_layout.addWidget(self.path_input)
        
        self.btn_select_chrome = QPushButton("选择浏览器")
        self.btn_select_chrome.clicked.connect(self.select_chrome_dialog)
        browser_layout.addWidget(self.btn_select_chrome)
        main_layout.addLayout(browser_layout)
        
        # 提示标签
        self.tip_label = QLabel("提示：将 .bin 或 .zip 备份文件直接拖放到下方表格中。程序将自动解压并甄别登录状态。")
        self.tip_label.setStyleSheet("color: #666; font-size: 12px; padding: 2px;")
        main_layout.addWidget(self.tip_label)
        
        # --- 中部：数据表格 ---
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["备份文件路径", "甄别状态", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        main_layout.addWidget(self.table)

    # 选择免安装谷歌浏览器路径
    def select_chrome_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择免安装 Chrome.exe", "", "Executable (*.exe)")
        if file_path:
            self.chrome_exe_path = file_path
            self.path_input.setText(file_path)

    # 拖入文件事件处理
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    # 放开鼠标事件：甄别是浏览器还是备份包
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            
            # 逻辑判定1：如果是直接拖入 chrome.exe
            if file_path.lower().endswith("chrome.exe"):
                self.chrome_exe_path = file_path
                self.path_input.setText(file_path)
                continue
                
            # 逻辑判定2：如果是拖入备份压缩包
            if file_path.lower().endswith('.zip') or file_path.lower().endswith('.bin'):
                self.process_backup_file(file_path)

    # 核心：处理并甄别备份文件
    def process_backup_file(self, file_path):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(file_path))
        
        status_item = QTableWidgetItem("正在甄别...")
        self.table.setItem(row, 1, status_item)
        
        # 为该文件创建独立的解压运行目录
        filename = os.path.basename(file_path).split('.')[0]
        target_env_dir = os.path.join(self.cache_root, f"env_{filename}_{row}")
        
        # 1. 执行解压
        if not self.extract_archive(file_path, target_env_dir):
            status_item.setText("失败：解压文件损坏")
            status_item.setForeground(Qt.red)
            return

        # 2. 甄别是否包含有效的 WhatsApp 登录缓存文件（检查常见特征目录）
        if self.verify_whatsapp_session(target_env_dir):
            status_item.setText("获取成功（已就绪）")
            status_item.setForeground(Qt.darkGreen)
            
            # 3. 获取成功后，动态在右侧生成“打开”按钮
            open_btn = QPushButton("打开浏览器进入")
            open_btn.clicked.connect(lambda: self.launch_chrome(target_env_dir))
            self.table.setCellWidget(row, 2, open_btn)
        else:
            status_item.setText("失败：未甄别到登录备份")
            status_item.setForeground(Qt.red)
            # 清理无效解压目录
            shutil.rmtree(target_env_dir, ignore_errors=True)

    # 解压算法（兼容 zip 与伪装成 bin 的 zip）
    def extract_archive(self, source, target):
        try:
            if os.path.exists(target):
                shutil.rmtree(target)
            with zipfile.ZipFile(source, 'r') as zip_ref:
                zip_ref.extractall(target)
            return True
        except:
            return False

    # 甄别算法：递归查找解压后目录里有没有存放 Session 或 Local Storage 的底层痕迹
    def verify_whatsapp_session(self, root_dir):
        has_local_storage = False
        has_network_data = False
        
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # 检查谷歌浏览器特有的缓存文件夹或特征文件
            if "Local Storage" in dirpath or "Default" in dirnames:
                has_local_storage = True
            # WhatsApp 网页版常驻特征数据文件
            for f in filenames:
                if "manifest" in f.lower() or "lock" in f.lower() or "cookies" in f.lower():
                    has_network_data = True
                    
        # 只要满足结构特征，即认为检测到了本地登录备份
        return has_local_storage or has_network_data

    # 启动免安装浏览器并挂载该环境
    def launch_chrome(self, env_dir):
        # 检查是否配置了免安装浏览器
        chrome_exe = self.path_input.text().strip()
        if not chrome_exe or not os.path.exists(chrome_exe):
            self.tip_label.setText("【错误】请先在顶部指定或拖入有效的‘免安装 Chrome.exe’路径！")
            return
            
        # 组装 Windows 底层启动命令：
        # --user-data-dir 强制让这个免安装浏览器读取我们刚刚解压出来的独立 WhatsApp 环境
        cmd = f'start "" "{chrome_exe}" --user-data-dir="{env_dir}" --no-first-run --no-default-browser-check "https://whatsapp.com"'
        os.system(cmd)
        self.tip_label.setText("浏览器已成功拉起，正在进入 WhatsApp...")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WhatsAppManagerApp()
    window.show()
    sys.exit(app.exec())
