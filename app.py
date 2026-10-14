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
        # 优化：保持小巧紧凑的精致比例
        self.root.geometry("600x420")
        
        # 锁死默认浏览器启动地址
        self.chrome_exe_path = r"C:\Users\Administrator\Desktop\GoogleChromePortable\GoogleChromePortable.exe"
        
        self.cache_root = os.path.join(os.getcwd(), "whatsapp_runtime_env")
        if not os.path.exists(self.cache_root):
            os.makedirs(self.cache_root)
            
        # 🟢 优化1：顶部提示语，加黑加粗
        bold_font = ("Microsoft YaHei", 9, "bold")
        self.tip_label = ttk.Label(root, text="提示：点击下方按钮可批量选择多个文件，程序将自动解压状态。", font=bold_font, foreground="black")
        self.tip_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # 🟢 优化2：新增大按钮，支持 Ctrl 键多选、批量一次性导入文件！
        btn_frame = ttk.Frame(root, padding=5)
        btn_frame.pack(fill=tk.X)
        self.import_btn = ttk.Button(btn_frame, text="➕ 批量导入备份文件 (支持多选)", command=self.batch_import_files)
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
        
        # 依然保留拖拽，作为辅助双保险
        self.setup_windows_drag_and_drop()

    # 🟢 核心新功能：弹出系统窗口，支持批量狂选多个文件导入！
    def batch_import_files(self):
        # filetypes 限制只允许选择 zip 和 bin，multiple=True 开启多选支持
        file_paths = filedialog.askopenfilenames(
            title="选择 WhatsApp 备份文件 (可按住Ctrl多选)", 
            filetypes=[("Backup Files", "*.zip *.bin")]
        )
        if not file_paths:
            return
            
        # 自动循环排队处理选择上来的每一个备份文件
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

    # 单个备份文件解压甄别核心流
    def process_single_backup_file(self, file_path):
        item_id = self.table.insert("", tk.END, values=(file_path, "正在解压...", "等待中"))
        self.root.update()
        
        try:
            filename = os.path.basename(file_path).replace('.', '_')
        except:
            filename = "archive"
            
        safe_item_name = item_id.replace('.', '_')
        target_env_dir = os.path.join(self.cache_root, f"env_{filename}_{safe_item_name}")
        
        try:
            if os.path.exists(target_env_dir):
                shutil.rmtree(target_env_dir, ignore_errors=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_env_dir)
            
            # 三层深度特征比对甄别
            has_session = False
            for dirpath, dirnames, filenames in os.walk(target_env_dir):
                if "Local Storage" in dirpath or "Default" in dirnames:
                    has_session = True
                    break
                if any("cookies" in f.lower() or "manifest" in f.lower() or "lock" in f.lower() for f in filenames):
                    has_session = True
                    break
            
            if has_session:
                # 获取成功，刷新显示本地成功的解压环境地址！
                self.table.item(item_id, values=(target_env_dir, "获取成功（已就绪）", "双击此行打开浏览器"))
                self.env_map[item_id] = target_env_dir
            else:
                self.table.item(item_id, values=(file_path, "失败：未检测到登录数据", "无"))
                shutil.rmtree(target_env_dir, ignore_errors=True)
        except:
            self.table.item(item_id, values=(file_path, "失败：解压损坏", "无"))
        
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
            cmd = f'start "" "{self.chrome_exe_path}" --user-data-dir="{env_dir}" --no-first-run --no-default-browser-check "https://whatsapp.com"'
            os.system(cmd)

if __name__ == "__main__":
    root = tk.Tk()
    app = WhatsAppManagerApp(root)
    root.mainloop()
