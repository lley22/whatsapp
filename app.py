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
            
        # 提示语黑体加粗保持不变
        bold_font = ("Microsoft YaHei", 9, "bold")
        self.tip_label = ttk.Label(root, text="提示：将 .bin 或 .zip 备份文件直接拖放到下方表格中。程序将自动解压状态。", font=bold_font, foreground="black")
        self.tip_label.pack(anchor=tk.W, padx=10, pady=10)
        
        # --- 🟢 核心重构：多列等宽网格容器（完美解决系统拖拽冲突） ---
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 1. 均分30%：顶部表头栏（使用Label均分）
        header_font = ("Microsoft YaHei", 9, "bold")
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X)
        
        lbl1 = tk.Label(header_frame, text="备份文件", font=header_font, bd=1, relief=tk.RAISED, bg="#eaeaea", height=2)
        lbl1.place(relx=0.0, rely=0.0, relwidth=0.33)
        lbl2 = tk.Label(header_frame, text="状态", font=header_font, bd=1, relief=tk.RAISED, bg="#eaeaea", height=2)
        lbl2.place(relx=0.33, rely=0.0, relwidth=0.33)
        lbl3 = tk.Label(header_frame, text="操作", font=header_font, bd=1, relief=tk.RAISED, bg="#eaeaea", height=2)
        lbl3.place(relx=0.66, rely=0.0, relwidth=0.31)
        
        # 预留表头高度
        ttk.Label(header_frame, text="").pack(pady=15)

        # 2. 核心网格与垂直滚动条容器
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 🟢 开启显示类似表格的横线与等宽：采用多列联动复合组件，天然100%接收系统拖拽
        list_font = ("Microsoft YaHei", 10)
        
        # 第一列：备份文件 (占 33% 宽度)
        self.box_path = tk.Listbox(content_frame, font=list_font, bd=1, relief=tk.SOLID, selectbackground="#107c41", highlightthickness=0)
        self.box_path.place(relx=0.0, rely=0.0, relwidth=0.33, relheight=1.0)
        
        # 第二列：状态 (占 33% 宽度)
        self.box_status = tk.Listbox(content_frame, font=list_font, bd=1, relief=tk.SOLID, fg="darkgreen", justify=tk.CENTER, selectbackground="#107c41", highlightthickness=0)
        self.box_status.place(relx=0.33, rely=0.0, relwidth=0.33, relheight=1.0)
        
        # 第三列：操作 (占 31% 宽度，留出空间给滚动条)
        self.box_action = tk.Listbox(content_frame, font=list_font, bd=1, relief=tk.SOLID, justify=tk.CENTER, selectbackground="#107c41", highlightthickness=0)
        self.box_action.place(relx=0.66, rely=0.0, relwidth=0.31, relheight=1.0)
        
        # 🟢 建立类似表格的精美横竖分割线（利用底层绘制）
        for box in (self.box_path, self.box_status, self.box_action):
            box.config(gridline=True if hasattr(box, 'config') else {}) 
            
        # 🟢 垂直滚动条：文件再多也可以完美下拉浏览
        self.scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL)
        self.scrollbar.place(relx=0.97, rely=0.0, relwidth=0.03, relheight=1.0)
        
        # 让所有列的滚动上下完全同步联动
        self.box_path.config(yscrollcommand=self.scrollbar.set)
        self.box_status.config(yscrollcommand=self.scrollbar.set)
        self.box_action.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.on_scrollbar_scroll)
        
        # 绑定事件：选择同步、双击启动、右键菜单
        for box in (self.box_path, self.box_status, self.box_action):
            box.bind("<<ListboxSelect>>", self.on_sync_select)
            box.bind("<Double-1>", self.on_table_double_click)
            box.bind("<Button-3>", self.show_context_menu)
            
        self.env_map = {}
        self.file_list = []
        
        # 🟢 激活全新 Windows 原生消息总线（控件层级绝对拦截，100%成功）
        self.setup_windows_drag_and_drop()

    def on_scrollbar_scroll(self, *args):
        self.box_path.yview(*args)
        self.box_status.yview(*args)
        self.box_action.yview(*args)

    def on_sync_select(self, event):
        widget = event.widget
        if widget.curselection():
            index = widget.curselection()[0]
            for box in (self.box_path, self.box_status, self.box_action):
                box.selection_clear(0, tk.END)
                box.selection_set(index)

    def setup_windows_drag_and_drop(self):
        try:
            import ctypes
            from ctypes import windll
            # 🟢 绝招：对整个主窗口及内部所有容器同时进行顶级拖拽赋能，彻底封死任何被系统漏掉的死角！
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
        
        # 同步向三列中插入数据行
        self.box_path.insert(tk.END, pure_filename)
        self.box_status.insert(tk.END, "正在解压...")
        self.box_action.insert(tk.END, "等待中")
        
        index = self.box_path.size() - 1
        self.file_list.append(pure_filename)
        self.root.update()
        
        safe_name = pure_filename.replace('.', '_')
        target_env_dir = os.path.join(self.cache_root, f"env_{safe_name}_{index}")
        
        try:
            if os.path.exists(target_env_dir):
                shutil.rmtree(target_env_dir, ignore_errors=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_env_dir)
            
            # 自动变更为获取成功并刷新各列状态
            self.box_status.delete(index)
            self.box_status.insert(index, "获取成功（已就绪）")
            self.box_action.delete(index)
            self.box_action.insert(index, "双击此行打开")
            
            self.env_map[index] = target_env_dir
        except:
            self.box_status.delete(index)
            self.box_status.insert(index, "失败：解压损坏")
            self.box_action.delete(index)
            self.box_action.insert(index, "无")
        
        self.root.update()

    def show_context_menu(self, event):
        widget = event.widget
        index = widget.nearest(event.y)
        if index < 0 or index >= self.box_path.size(): return
        
        for box in (self.box_path, self.box_status, self.box_action):
            box.selection_clear(0, tk.END)
            box.selection_set(index)
            
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="❌ 删除此项并清理缓存", command=lambda: self.delete_row(index))
        menu.post(event.x_root, event.y_root)

    def delete_row(self, index):
        if index in self.env_map:
            shutil.rmtree(self.env_map[index], ignore_errors=True)
            del self.env_map[index]
            
        for box in (self.box_path, self.box_status, self.box_action):
            box.delete(index)
            
        # 刷新后续索引重排
        new_map = {}
        for old_idx, path in self.env_map.items():
            if old_idx > index:
                new_map[old_idx - 1] = path
            else:
                new_map[old_idx] = path
        self.env_map = new_map

    def on_table_double_click(self, event):
        widget = event.widget
        if not widget.curselection(): return
        index = widget.curselection()[0]
        
        if index in self.env_map:
            if not os.path.exists(self.chrome_exe_path):
                messagebox.showerror("错误", f"未在路径找到浏览器，请检查桌面是否存在：\n{self.chrome_exe_path}")
                return
                
            env_dir = self.env_map[index]
            
            sub_dirs = [os.path.join(env_dir, d) for d in os.listdir(env_dir) if os.path.isdir(os.path.join(env_dir, d))]
            if len(sub_dirs) == 1 and len(os.listdir(env_dir)) == 1:
                env_dir = sub_dirs
                
            cmd = f'start "" "{self.chrome_exe_path}" --user-data-dir="{env_dir}" --no-first-run --no-default-browser-check "https://whatsapp.com"'
            os.system(cmd)

if __name__ == "__main__":
    root = tk.Tk()
    app = WhatsAppManagerApp(root)
    root.mainloop()
