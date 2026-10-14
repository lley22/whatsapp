import sys
import os
import zipfile
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
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
            
        # 提示语黑体加粗
        bold_font = ("Microsoft YaHei", 9, "bold")
        self.tip_label = ttk.Label(root, text="提示：将 .bin 或 .zip 备份文件直接拖放到下方表格中。程序将自动解压状态。", font=bold_font, foreground="black")
        self.tip_label.pack(anchor=tk.W, padx=10, pady=10)
        
        # --- 核心容器 ---
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 1. 均分30%：顶部表头栏
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X)
        
        # 🟢 彻底修复：将所有表头标签的字体变量统一死锁为 bold_font，彻底根除定义缺失报错！
        lbl1 = tk.Label(header_frame, text="备份文件", font=bold_font, bd=1, relief=tk.RAISED, bg="#eaeaea", height=2)
        lbl1.place(relx=0.0, rely=0.0, relwidth=0.33)
        
        lbl2 = tk.Label(header_frame, text="状态", font=bold_font, bd=1, relief=tk.RAISED, bg="#eaeaea", height=2)
        lbl2.place(relx=0.33, rely=0.0, relwidth=0.33)
        
        lbl3 = tk.Label(header_frame, text="操作", font=bold_font, bd=1, relief=tk.RAISED, bg="#eaeaea", height=2)
        lbl3.place(relx=0.66, rely=0.0, relwidth=0.34)
        
        ttk.Label(header_frame, text="").pack(pady=15) # 预留表头高度

        # 2. 带有画布和滚动条的可滑动表格区
        self.canvas_frame = ttk.Frame(main_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW, width=565)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 数据存储
        self.row_widgets = []
        self.env_map = {}
        self.row_counter = 0
        
        # 彻底解决死锁：对整个窗体及内部画布同时激活顶级拖拽赋能
        self.setup_windows_drag_and_drop()

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

    def process_single_backup_file(self, file_path):
        pure_filename = os.path.basename(file_path)
        current_row = self.row_counter
        self.row_counter += 1
        
        # 创建一行带有完整格子线（横线与竖线）的单元格容器
        row_frame = tk.Frame(self.scrollable_frame, height=30, bd=1, relief=tk.SOLID)
        row_frame.pack(fill=tk.X, expand=True)
        row_frame.pack_propagate(False)
        
        # 第一列：文件名 (等宽占 33%)
        cell_path = tk.Label(row_frame, text=pure_filename, anchor=tk.W, font=("Microsoft YaHei", 9), bg="white", padx=5, bd=1, relief=tk.SOLID)
        cell_path.place(relx=0.0, rely=0.0, relwidth=0.33, relheight=1.0)
        
        # 第二列：状态 (等宽占 33%)
        cell_status = tk.Label(row_frame, text="正在解压...", anchor=tk.CENTER, font=("Microsoft YaHei", 9), bg="white", fg="blue", bd=1, relief=tk.SOLID)
        cell_status.place(relx=0.33, rely=0.0, relwidth=0.33, relheight=1.0)
        
        # 第三列：操作 (等宽占 34%)
        cell_action = tk.Label(row_frame, text="等待中", anchor=tk.CENTER, font=("Microsoft YaHei", 9), bg="white", fg="gray", bd=1, relief=tk.SOLID)
        cell_action.place(relx=0.66, rely=0.0, relwidth=0.34, relheight=1.0)
        
        # 绑定事件
        for widget in (cell_path, cell_status, cell_action):
            widget.bind("<Double-1>", lambda e, r=current_row: self.on_row_double_click(r))
            widget.bind("<Button-3>", lambda e, r=current_row, f=row_frame: self.show_context_menu(e, r, f))
            
        self.row_widgets.append({
            'frame': row_frame,
            'status': cell_status,
            'action': cell_action,
            'pure_name': pure_filename
        })
        self.root.update()
        
        safe_name = pure_filename.replace('.', '_')
        target_env_dir = os.path.join(self.cache_root, f"env_{safe_name}_{current_row}")
        
        try:
            if os.path.exists(target_env_dir):
                shutil.rmtree(target_env_dir, ignore_errors=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_env_dir)
            
            # 解压成功，刷新各列
            cell_status.config(text="获取成功（已就绪）", fg="darkgreen")
            cell_action.config(text="双击此行打开", fg="#107c41")
            self.env_map[current_row] = target_env_dir
        except:
            cell_status.config(text="失败：解压损坏", fg="red")
            cell_action.config(text="无", fg="gray")
            
        self.root.update()

    def show_context_menu(self, event, row_idx, row_frame):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="❌ 删除此项并清理缓存", command=lambda: self.delete_row(row_idx, row_frame))
        menu.post(event.x_root, event.y_root)

    def delete_row(self, row_idx, row_frame):
        if row_idx in self.env_map:
            shutil.rmtree(self.env_map[row_idx], ignore_errors=True)
            del self.env_map[row_idx]
        row_frame.pack_forget()
        row_frame.destroy()

    def on_row_double_click(self, row_idx):
        if row_idx in self.env_map:
            if not os.path.exists(self.chrome_exe_path):
                messagebox.showerror("错误", f"未在路径找到浏览器，请检查桌面是否存在：\n{self.chrome_exe_path}")
                return
                
            env_dir = self.env_map[row_idx]
            sub_dirs = [os.path.join(env_dir, d) for d in os.listdir(env_dir) if os.path.isdir(os.path.join(env_dir, d))]
            if len(sub_dirs) == 1 and len(os.listdir(env_dir)) == 1:
                env_dir = sub_dirs[0] # 🟢 修复微调：确保深挖子目录时语法完全精确
                
            cmd = f'start "" "{self.chrome_exe_path}" --user-data-dir="{env_dir}" --no-first-run --no-default-browser-check "https://whatsapp.com"'
            os.system(cmd)

if __name__ == "__main__":
    root = tk.Tk()
    app = WhatsAppManagerApp(root)
    root.mainloop()
