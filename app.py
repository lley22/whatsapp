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
        self.root.geometry("600x400")
        
        # 内置固定的便携版浏览器地址
        self.chrome_exe_path = r"C:\Users\Administrator\Desktop\GoogleChromePortable\GoogleChromePortable.exe"
        
        self.cache_root = os.path.join(os.getcwd(), "whatsapp_runtime_env")
        if not os.path.exists(self.cache_root):
            os.makedirs(self.cache_root)
            
        # 提示语黑体加粗保持不变
        bold_font = ("Microsoft YaHei", 9, "bold")
        self.tip_label = ttk.Label(root, text="提示：将 .bin 或 .zip 备份文件直接拖放到下方表格中。程序将自动解压状态。", font=bold_font, foreground="black")
        self.tip_label.pack(anchor=tk.W, padx=10, pady=10)
        
        # --- 🟢 下方核心数据表格区与滚动条容器 ---
        table_frame = ttk.Frame(root)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 🟢 优化：加入标准表格网格线样式（show="headings" 配合样式树开启 gridlines）
        style = ttk.Style()
        style.configure("Treeview", rowheight=25) # 提高行高，让横线更好看
        style.map("Treeview", background=[('selected', '#107c41')]) # 选中变绿
        
        # “备份文件路径”正式改为“备份文件”
        self.table = ttk.Treeview(table_frame, columns=("path", "status", "action"), show="headings")
        self.table.heading("path", text="备份文件")
        self.table.heading("status", text="状态")
        self.table.heading("action", text="操作")
        
        # 🟢 开启显示类似表格的横线和竖线
        self.table.configure(style="Treeview")
        # 通过 tkinter 底层强制显示网格线
        root.option_add('*Treeview.Gridlines', 'both') 
        
        # 🟢 优化：均分宽度。窗口宽度600，去掉两边边距后，各占30%位置（大约175像素）
        self.table.column("path", width=175, minwidth=100, anchor=tk.W)
        self.table.column("status", width=175, minwidth=100, anchor=tk.CENTER)
        self.table.column("action", width=175, minwidth=100, anchor=tk.CENTER)
        
        # 🟢 优化：右侧无缝对接垂直滚动条，文件再多也可以完美下拉
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        
        # 布局表格和滚动条
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.table.bind("<Double-1>", self.on_table_double_click)
        self.table.bind("<Button-3>", self.show_context_menu)
        
        self.env_map = {}
        
        # 控件级精准拖拽拦截内核
        self.setup_table_drag_and_drop()

    def setup_table_drag_and_drop(self):
        try:
            import ctypes
            from ctypes import windll
            windll.shell32.DragAcceptFiles(self.table.winfo_id(), True)
            self.root.tk.createcommand("::tk::mac::OpenDocument", self.handle_table_drop)
            self.table.bind("<Drop>", self.handle_table_drop)
        except Exception as e:
            print(f"拖拽绑定失败: {e}")

    def handle_table_drop(self, *args):
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
        
        item_id = self.table.insert("", tk.END, values=(pure_filename, "正在解压...", "等待中"))
        self.root.update()
        
        safe_name = pure_filename.replace('.', '_')
        target_env_dir = os.path.join(self.cache_root, f"env_{safe_name}_{item_id.replace('.', '_')}")
        
        try:
            if os.path.exists(target_env_dir):
                shutil.rmtree(target_env_dir, ignore_errors=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_env_dir)
            
            # 宽松通关模式：保持显示纯文件名
            self.table.item(item_id, values=(pure_filename, "获取成功（已就绪）", "双击此行打开浏览器"))
            self.env_map[item_id] = target_env_dir
            
        except:
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
            
            sub_dirs = [os.path.join(env_dir, d) for d in os.listdir(env_dir) if os.path.isdir(os.path.join(env_dir, d))]
            if len(sub_dirs) == 1 and len(os.listdir(env_dir)) == 1:
                env_dir = sub_dirs[0]
                
            cmd = f'start "" "{self.chrome_exe_path}" --user-data-dir="{env_dir}" --no-first-run --no-default-browser-check "https://whatsapp.com"'
            os.system(cmd)

if __name__ == "__main__":
    root = tk.Tk()
    app = WhatsAppManagerApp(root)
    root.mainloop()
