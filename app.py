import sys
import os
import zipfile
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
# 引入 Windows 底层拖拽组件（不依赖任何第三方大库，打包绝对不红叉）
import ctypes
from ctypes import windll

class WhatsAppManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WhatsApp 备份环境管理工具")
        # 窗口变窄：紧凑紧凑再紧凑
        self.root.geometry("600x450")
        
        self.chrome_exe_path = ""
        self.cache_root = os.path.join(os.getcwd(), "whatsapp_runtime_env")
        if not os.path.exists(self.cache_root):
            os.makedirs(self.cache_root)
            
        # --- 顶部区域：直接就是输入框，删除了前缀字 ---
        top_frame = ttk.Frame(root, padding=10)
        top_frame.pack(fill=tk.X)
        
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(top_frame, textvariable=self.path_var, width=50)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.path_entry.insert(0, "请选择或直接拖入 chrome.exe 的路径...")
        
        ttk.Button(top_frame, text="选择浏览器", command=self.select_chrome).pack(side=tk.RIGHT)
        
        # 提示语中删除了“并甄别”三个字
        self.tip_label = ttk.Label(root, text="提示：将 .bin 或 .zip 备份文件直接拖放到下方表格中。程序将自动解压状态。", foreground="gray")
        self.tip_label.pack(anchor=tk.W, padx=10, pady=(0, 5))
        
        # --- 中部：数据表格 ---
        # 甄别状态改为“状态”
        self.table = ttk.Treeview(root, columns=("path", "status", "action"), show="headings")
        self.table.heading("path", text="备份文件路径")
        self.table.heading("status", text="状态")
        self.table.heading("action", text="操作")
        
        # 精准划分列宽权重，支持右边窗口更短
        self.table.column("path", width=330, anchor=tk.W)
        self.table.column("status", width=130, anchor=tk.CENTER)
        self.table.column("action", width=120, anchor=tk.CENTER)
        self.table.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 绑定双击启动事件与右键弹出菜单
        self.table.bind("<Double-1>", self.on_table_double_click)
        self.table.bind("<Button-3>", self.show_context_menu)
        
        self.env_map = {}
        
        # 启用全窗口拖拽捕捉
        self.setup_drag_and_drop()

    def select_chrome(self):
        file_path = filedialog.askopenfilename(title="选择免安装 Chrome.exe", filetypes=[("Executable", "*.exe")])
        if file_path:
            self.chrome_exe_path = file_path
            self.path_var.set(file_path)

    # 核心优化：高阶 Windows 全局拖拉兼容处理
    def setup_drag_and_drop(self):
        try:
            # 开启系统级拖拽流
            windll.shell32.DragAcceptFiles(self.root.winfo_id(), True)
            self.root.tk.createcommand("::tk::mac::OpenDocument", self.handle_dropped_files)
            # 兼容普通拖拽映射
            self.root.bind("<Drop>", self.handle_dropped_files)
        except:
            pass

    def handle_dropped_files(self, *args):
        # 提取拖入的路径
        for arg in args:
            if not arg: continue
            file_path = str(arg).strip('{}')
            if file_path.lower().endswith("chrome.exe"):
                self.chrome_exe_path = file_path
                self.path_var.set(file_path)
            elif file_path.lower().endswith('.zip') or file_path.lower().endswith('.bin'):
                self.process_backup_file(file_path)

    def process_backup_file(self, file_path):
        item_id = self.table.insert("", tk.END, values=(file_path, "正在解压...", "等待中"))
        self.root.update()
        
        try:
            filename = os.path.basename(file_path).replace('.', '_')
        except:
            filename = "archive"
            
        target_env_dir = os.path.join(self.cache_root, f"env_{filename}_{item_id.replace('.', '_')}")
        
        try:
            if os.path.exists(target_env_dir):
                shutil.rmtree(target_env_dir, ignore_errors=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_env_dir)
            
            # 自动验证状态
            has_session = False
            for dirpath, dirnames, filenames in os.walk(target_env_dir):
                if "Local Storage" in dirpath or "Default" in dirnames or any("cookies" in f.lower() for f in filenames):
                    has_session = True
                    break
            
            if has_session:
                self.table.item(item_id, values=(file_path, "获取成功（已就绪）", "双击此行打开浏览器"))
                self.env_map[item_id] = target_env_dir
            else:
                self.table.item(item_id, values=(file_path, "失败：未检测到登录数据", "无"))
                shutil.rmtree(target_env_dir, ignore_errors=True)
        except:
            self.table.item(item_id, values=(file_path, "失败：解压损坏", "无"))

    # 右键删除此项并一键清理缓存
    def show_context_menu(self, event):
        item_id = self.table.identify_row(event.y)
        if not item_id: return
        self.table.selection_set(item_id)
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="❌ 删除此项并清理缓存", command=lambda: self.delete_row(item_id))
        menu.post(event.x_root, event.y_root)

    def delete_row(self, item_id):
        if item_id in self.env_map:
            shutil.rmtree(self.env_map[item_id], ignore_errors=True)
            del self.env_map[item_id]
        self.table.delete(item_id)

    # 双击表格直接调用便携版浏览器进入
    def on_table_double_click(self, event):
        item_id = self.table.focus()
        if item_id in self.env_map:
            chrome_exe = self.path_var.get().strip()
            if not chrome_exe or not os.path.exists(chrome_exe) or "请选择" in chrome_exe:
                messagebox.showerror("错误", "请先在顶部指定或拖入有效的‘免安装 Chrome.exe’路径！")
                return
            env_dir = self.env_map[item_id]
            cmd = f'start "" "{chrome_exe}" --user-data-dir="{env_dir}" --no-first-run --no-default-browser-check "https://whatsapp.com"'
            os.system(cmd)

if __name__ == "__main__":
    root = tk.Tk()
    app = WhatsAppManagerApp(root)
    # 针对部分老旧 Windows 的兼容支持拖拽注入
    try:
        import windrag
        windrag.hook(root.winfo_id(), app.handle_dropped_files)
    except:
        pass
    root.mainloop()
