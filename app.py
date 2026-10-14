import sys
import os
import zipfile
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re

class WhatsAppManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WhatsApp 备份环境管理工具")
        self.root.geometry("600x420")
        
        # 内置固定的便携版浏览器地址
        self.chrome_exe_path = r"C:\Users\Administrator\Desktop\GoogleChromePortable\GoogleChromePortable.exe"
        
        self.cache_root = os.path.join(os.getcwd(), "whatsapp_runtime_env")
        if not os.path.exists(self.cache_root):
            os.makedirs(self.cache_root)
            
        # 提示语加黑加粗
        bold_font = ("Microsoft YaHei", 9, "bold")
        self.tip_label = ttk.Label(root, text="提示：点击下方按钮或直接拖放多个文件，程序将自动解压状态。", font=bold_font, foreground="black")
        self.tip_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # 批量选择大按钮
        btn_frame = ttk.Frame(root, padding=5)
        btn_frame.pack(fill=tk.X)
        self.import_btn = ttk.Button(btn_frame, text="➕ 批量导入备份文件 (支持多选 / 可拖放)", command=self.batch_import_files)
        self.import_btn.pack(anchor=tk.W, padx=10, pady=2)
        
        # --- 数据表格区 ---
        self.table = ttk.Treeview(root, columns=("path", "status", "action"), show="headings")
        self.table.heading("path", text="备份文件路径")
        self.table.heading("status", text="状态")
        self.table.heading("action", text="操作")
        
        self.table.column("path", width=330, anchor=tk.W)
        self.table.column("status", width=130, anchor=tk.CENTER)
        self.table.column("action", width=120, anchor=tk.CENTER)
        self.table.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.table.bind("<Double-1>", self.on_table_double_click)
        self.table.bind("<Button-3>", self.show_context_menu)
        
        self.env_map = {}
        
        # 启用双保险拖放拦截内核
        self.setup_windows_drag_and_drop()

    def batch_import_files(self):
        file_paths = filedialog.askopenfilenames(
            title="选择 WhatsApp 备份文件", 
            filetypes=[("Backup Files", "*.zip *.bin")]
        )
        if not file_paths:
            return
        for file_path in file_paths:
            if os.path.isfile(file_path):
                self.process_single_backup_file(file_path)

    def setup_windows_drag_and_drop(self):
        try:
            import ctypes
            from ctypes import windll
            windll.shell32.DragAcceptFiles(self.root.winfo_id(), True)
            self.root.tk.createcommand("::tk::mac::OpenDocument", self.handle_global_drop)
            self.root.bind("<Drop>", self.handle_global_drop)
        except:
            pass

    def handle_global_drop(self, *args):
        if not args: return
        raw_drop_str = " ".join([str(arg) for arg in args if arg])
        file_paths = []
        if "{" in raw_drop_str:
            file_paths = re.findall(r'\{([^}]+)\}', raw_drop_str)
            remain_str = re.sub(r'\{[^}]+\}', '', raw_drop_str)
            file_paths.extend([p.strip() for p in remain_str.split() if p.strip()])
        else:
            file_paths = [p.strip() for p in raw_drop_str.split() if p.strip()]

        for file_path in file_paths:
            if os.path.isfile(file_path) and (file_path.lower().endswith('.zip') or file_path.lower().endswith('.bin')):
                self.process_single_backup_file(file_path)

    # 核心处理流程（全格式宽松模式）
    def process_single_backup_file(self, file_path):
        pure_filename = os.path.basename(file_path)
        
        # 初始插入表格
        item_id = self.table.insert("", tk.END, values=(pure_filename, "正在解压...", "等待中"))
        self.root.update()
        
        safe_name = pure_filename.replace('.', '_')
        target_env_dir = os.path.join(self.cache_root, f"env_{safe_name}_{item_id.replace('.', '_')}")
        
        try:
            if os.path.exists(target_env_dir):
                shutil.rmtree(target_env_dir, ignore_errors=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_env_dir)
            
            # 🟢 不再强制检查内部特征目录，只要能够成功解压缩，一律放行通过！
            self.table.item(item_id, values=(pure_filename, "获取成功（已就绪）", "双击此行打开浏览器"))
            self.env_map[item_id] = target_env_dir
            
        except Exception as e:
            self.table.item(item_id, values=(pure_filename, "失败：解压损坏", "无"))
        
        self.root.update()

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

    def on_table_double_click(self, event):
        item_id = self.table.focus()
        if item_id in self.env_map:
            if not os.path.exists(self.chrome_exe_path):
                messagebox.showerror("错误", f"未在路径找到浏览器，请检查桌面是否存在：\n{self.chrome_exe_path}")
                return
                
            env_dir = self.env_map[item_id]
            
            # 🟢 智能外壳深度适配算法：如果解压后里面只有孤零零的一个多余母文件夹，则自动往下探一级
            sub_dirs = [os.path.join(env_dir, d) for d in os.listdir(env_dir) if os.path.isdir(os.path.join(env_dir, d))]
            if len(sub_dirs) == 1 and len(os.listdir(env_dir)) == 1:
                env_dir = sub_dirs[0]
                
            cmd = f'start "" "{self.chrome_exe_path}" --user-data-dir="{env_dir}" --no-first-run --no-default-browser-check "https://whatsapp.com"'
            os.system(cmd)

if __name__ == "__main__":
    root = tk.Tk()
    app = WhatsAppManagerApp(root)
    root.mainloop()
