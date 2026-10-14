import sys
import os
import zipfile
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class WhatsAppManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WhatsApp 备份环境管理工具")
        self.root.geometry("850x450")
        
        self.chrome_exe_path = ""
        self.cache_root = os.path.join(os.getcwd(), "whatsapp_runtime_env")
        os.makedirs(self.cache_root, exist_ok=True)
        
        # --- 顶部：浏览器路径 ---
        top_frame = ttk.Frame(root, padding=10)
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="免安装Chrome路径:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(top_frame, textvariable=self.path_var, width=60)
        self.path_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(top_frame, text="选择浏览器", command=self.select_chrome).pack(side=tk.LEFT)
        
        # 提示
        ttk.Label(root, text="说明：请选择免安装浏览器。点击下方添加备份按钮引入 zip 或 bin 格式的登录备份。", foreground="gray").pack(anchor=tk.W, padx=10)
        
        # --- 中部：数据表格和添加按钮 ---
        btn_frame = ttk.Frame(root, padding=5)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="+ 添加并甄别备份文件", command=self.add_backup_file).pack(side=tk.LEFT, padx=10)
        
        # 表格
        self.table = ttk.Treeview(root, columns=("path", "status", "action"), show="headings")
        self.table.heading("path", text="备份文件路径")
        self.table.heading("status", text="甄别状态")
        self.table.heading("action", text="操作")
        self.table.column("path", width=400)
        self.table.column("status", width=200)
        self.table.column("action", width=150)
        self.table.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 绑定点击表格事件
        self.table.bind("<Double-1>", self.on_table_click)
        self.env_map = {}

    def select_chrome(self):
        file_path = filedialog.askopenfilename(title="选择免安装 Chrome.exe", filetypes=[("Executable", "*.exe")])
        if file_path:
            self.chrome_exe_path = file_path
            self.path_var.set(file_path)

    def add_backup_file(self):
        file_path = filedialog.askopenfilename(title="选择 WhatsApp 备份文件", filetypes=[("Backup Files", "*.zip *.bin")])
        if not file_path:
            return
            
        item_id = self.table.insert("", tk.END, values=(file_path, "正在甄别...", "等待中"))
        self.root.update()
        
        filename = os.path.basename(file_path).replace('.', '_')
        target_env_dir = os.path.join(self.cache_root, f"env_{filename}_{item_id}")
        
        # 解压
        try:
            if os.path.exists(target_env_dir):
                shutil.rmtree(target_env_dir)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_env_dir)
            
            # 甄别
            has_session = False
            for dirpath, dirnames, filenames in os.walk(target_env_dir):
                if "Local Storage" in dirpath or "Default" in dirnames or any("cookies" in f.lower() for f in filenames):
                    has_session = True
                    break
            
            if has_session:
                self.table.item(item_id, values=(file_path, "获取成功（已就绪）", "双击此行打开浏览器"))
                self.env_map[item_id] = target_env_dir
            else:
                self.table.item(item_id, values=(file_path, "失败：未甄别到登录备份", "无"))
                shutil.rmtree(target_env_dir, ignore_errors=True)
        except:
            self.table.item(item_id, values=(file_path, "失败：解压损坏", "无"))

    def on_table_click(self, event):
        item_id = self.table.focus()
        if item_id in self.env_map:
            chrome_exe = self.path_var.get().strip()
            if not chrome_exe or not os.path.exists(chrome_exe):
                messagebox.showerror("错误", "请先在顶部指定有效的‘免安装 Chrome.exe’路径！")
                return
            env_dir = self.env_map[item_id]
            cmd = f'start "" "{chrome_exe}" --user-data-dir="{env_dir}" --no-first-run --no-default-browser-check "https://whatsapp.com"'
            os.system(cmd)

if __name__ == "__main__":
    root = tk.Tk()
    app = WhatsAppManagerApp(root)
    root.mainloop()
