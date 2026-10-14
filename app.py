import sys
import os
import zipfile
import shutil
import tkinter as tk
from tkinter import ttk, messagebox

class WhatsAppManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WhatsApp 备份环境管理工具")
        # 界面高度也随之微调，变得更加小巧紧凑
        self.root.geometry("600x400")
        
        # 🟢 已经按照要求：在底层直接锁死默认浏览器启动地址，删除了多余的输入框
        self.chrome_exe_path = r"C:\Users\Administrator\Desktop\GoogleChromePortable\GoogleChromePortable.exe"
        
        self.cache_root = os.path.join(os.getcwd(), "whatsapp_runtime_env")
        if not os.path.exists(self.cache_root):
            os.makedirs(self.cache_root)
            
        # 顶部提示栏（增加了对固定路径的额外说明）
        self.tip_label = ttk.Label(root, text="提示：将 .bin 或 .zip 备份文件直接拖放到下方表格中。程序将自动解压状态。", foreground="gray")
        self.tip_label.pack(anchor=tk.W, padx=10, pady=10)
        
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
        
        # 启用底部的备份文件拖拉机制
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

    # 拖入备份包处理
    def handle_global_drop(self, *args):
        for arg in args:
            if not arg: continue
            file_path = str(arg).strip('{}')
            
            if os.path.isfile(file_path) and (file_path.lower().endswith('.zip') or file_path.lower().endswith('.bin')):
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
                    
                    # 检查是否包含有效登录痕迹
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

    # 右键删除
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

    # 双击表格直接调用锁死的桌面便携版浏览器进入
    def on_table_double_click(self, event):
        item_id = self.table.focus()
        if item_id in self.env_map:
            # 校验桌面上的指定文件是否存在
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
