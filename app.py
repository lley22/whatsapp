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
        self.root.geometry("600x450")
        
        self.chrome_exe_path = ""
        self.cache_root = os.path.join(os.getcwd(), "whatsapp_runtime_env")
        if not os.path.exists(self.cache_root):
            os.makedirs(self.cache_root)
            
        # --- 顶部区域：浏览器配置区 ---
        top_frame = ttk.Frame(root, padding=10)
        top_frame.pack(fill=tk.X)
        
        self.path_var = tk.StringVar()
        # 🟢 优化：将 width 从 50 缩减到 25，让这个窗口/输入框的宽度直接短一半！
        self.path_entry = ttk.Entry(top_frame, textvariable=self.path_var, width=25)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.path_var.set("可直接拖入便携浏览器文件夹...")
        
        ttk.Button(top_frame, text="选择浏览器", command=self.select_chrome).pack(side=tk.RIGHT)
        
        # 提示语
        self.tip_label = ttk.Label(root, text="提示：将 .bin 或 .zip 备份文件直接拖放到下方表格中。程序将自动解压状态。", foreground="gray")
        self.tip_label.pack(anchor=tk.W, padx=10, pady=(0, 5))
        
        # --- 中部：数据表格 ---
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
        
        # 🟢 开启全新的 Windows 原生控件拖放精准拦截机制
        self.setup_windows_drag_and_drop()

    def select_chrome(self):
        file_path = filedialog.askopenfilename(title="选择 GoogleChromePortable.exe", filetypes=[("Executable", "*.exe")])
        if file_path:
            self.chrome_exe_path = file_path
            self.path_var.set(file_path)

    # 核心：利用操作系统底层的消息循环，精准拦截松开鼠标的位置
    def setup_windows_drag_and_drop(self):
        try:
            import ctypes
            from ctypes import windll
            windll.shell32.DragAcceptFiles(self.root.winfo_id(), True)
            self.root.tk.createcommand("::tk::mac::OpenDocument", self.handle_global_drop)
            self.root.bind("<Drop>", self.handle_global_drop)
        except Exception as e:
            print(f"安全跳过环境初始化: {e}")

    # 核心重构：彻底弃用容易失灵的相对坐标，改用绝对控件碰撞检测
    def handle_global_drop(self, *args):
        for arg in args:
            if not arg: continue
            raw_path = str(arg).strip('{}')
            
            # 获取当前鼠标放开时，究竟落在了哪一个具体控件的头顶上
            mouse_x = self.root.winfo_pointerx()
            mouse_y = self.root.winfo_pointery()
            target_widget = self.root.winfo_containing(mouse_x, mouse_y)
            
            # 🟢 判定1：如果鼠标在“输入框”或者“顶部工具栏”里放开，100% 判定为配置浏览器
            if target_widget == self.path_entry or mouse_y - self.root.winfo_rooty() < 60:
                self.process_browser_drop(raw_path)
            else:
                # 🟢 判定2：其余地方松开，100% 判定为拖入备份文件
                self.process_backup_drop(raw_path)

    # 处理浏览器拖入
    def process_browser_drop(self, drop_path):
        # 如果是个文件夹
        if os.path.isdir(drop_path):
            found_exe = ""
            for dirpath, _, filenames in os.walk(drop_path):
                for filename in filenames:
                    if filename.lower() == "googlechromeportable.exe":
                        found_exe = os.path.join(dirpath, filename)
                        break
                if found_exe: break
            
            if found_exe:
                self.chrome_exe_path = found_exe
                self.path_var.set(found_exe) # 🟢 实时在界面框内显示成功的地址！
            else:
                # 备用方案：捞取任何带 chrome 名字的可执行程序
                for dirpath, _, filenames in os.walk(drop_path):
                    for filename in filenames:
                        if "chrome" in filename.lower() and filename.lower().endswith(".exe"):
                            found_exe = os.path.join(dirpath, filename)
                            break
                    if found_exe: break
                
                if found_exe:
                    self.chrome_exe_path = found_exe
                    self.path_var.set(found_exe) # 🟢 实时显示成功的地址
                else:
                    messagebox.showwarning("提示", "未在该文件夹内找到 GoogleChromePortable.exe 文件！")
                    
        # 如果直接把 .exe 文件拽了进来
        elif os.path.isfile(drop_path) and drop_path.lower().endswith(".exe"):
            self.chrome_exe_path = drop_path
            self.path_var.set(drop_path) # 🟢 实时在界面框内显示成功的地址！

    # 处理备份拖入
    def process_backup_drop(self, drop_path):
        if os.path.isfile(drop_path) and (drop_path.lower().endswith('.zip') or drop_path.lower().endswith('.bin')):
            item_id = self.table.insert("", tk.END, values=(drop_path, "正在解压...", "等待中"))
            self.root.update()
            
            try:
                filename = os.path.basename(drop_path).replace('.', '_')
            except:
                filename = "archive"
                
            target_env_dir = os.path.join(self.cache_root, f"env_{filename}_{item_id.replace('.', '_')}")
            
            try:
                if os.path.exists(target_env_dir):
                    shutil.rmtree(target_env_dir, ignore_errors=True)
                with zipfile.ZipFile(drop_path, 'r') as zip_ref:
                    zip_ref.extractall(target_env_dir)
                
                has_session = False
                for dirpath, dirnames, filenames in os.walk(target_env_dir):
                    if "Local Storage" in dirpath or "Default" in dirnames or any("cookies" in f.lower() for f in filenames):
                        has_session = True
                        break
                
                if has_session:
                    self.table.item(item_id, values=(drop_path, "获取成功（已就绪）", "双击此行打开浏览器"))
                    self.env_map[item_id] = target_env_dir
                else:
                    self.table.item(item_id, values=(drop_path, "失败：未检测到登录数据", "无"))
                    shutil.rmtree(target_env_dir, ignore_errors=True)
            except:
                self.table.item(item_id, values=(drop_path, "失败：解压损坏", "无"))

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
            chrome_exe = self.path_var.get().strip()
            if not chrome_exe or not os.path.exists(chrome_exe) or "请选择" in chrome_exe or "可直接" in chrome_exe:
                messagebox.showerror("错误", "请先在顶部指定或拖入有效的‘便携浏览器路径’！")
                return
            env_dir = self.env_map[item_id]
            cmd = f'start "" "{chrome_exe}" --user-data-dir="{env_dir}" --no-first-run --no-default-browser-check "https://whatsapp.com"'
            os.system(cmd)

if __name__ == "__main__":
    root = tk.Tk()
    app = WhatsAppManagerApp(root)
    root.mainloop()
