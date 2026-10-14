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
        # 优化：右边窗口短一半，界面整体非常小巧紧凑
        self.root.geometry("600x400")
        
        # 🟢 锁死默认浏览器启动地址，删除了多余的输入框
        self.chrome_exe_path = r"C:\Users\Administrator\Desktop\GoogleChromePortable\GoogleChromePortable.exe"
        
        self.cache_root = os.path.join(os.getcwd(), "whatsapp_runtime_env")
        if not os.path.exists(self.cache_root):
            os.makedirs(self.cache_root)
            
        # 🟢 优化：提示语字体加黑加粗，和最上面的标题颜色样式完全一致
        bold_font = ("Microsoft YaHei", 9, "bold")
        self.tip_label = ttk.Label(root, text="提示：将 .bin 或 .zip 备份文件直接拖放到下方表格中。程序将自动解压状态。", font=bold_font, foreground="black")
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
        
        # 🟢 启用升级版多文件全局拖放拦截内核
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

    # 核心：精准解析 Windows 批量拖拽时产生的复杂合并路径字符串
    def handle_global_drop(self, *args):
        if not args:
            return
            
        # 将传入的所有参数拼接并标准化
        raw_drop_str = " ".join([str(arg) for arg in args if arg])
        
        # 使用正则表达式精准拆分多路径（兼容带空格、带大括号 {} 的复杂 Windows 批量路径规则）
        file_paths = []
        if "{" in raw_drop_str:
            file_paths = re.findall(r'\{([^}]+)\}', raw_drop_str)
            remain_str = re.sub(r'\{[^}]+\}', '', raw_drop_str)
            file_paths.extend([p.strip() for p in remain_str.split() if p.strip()])
        else:
            file_paths = [p.strip() for p in raw_drop_str.split() if p.strip()]

        # 🟢 循环迭代：像排队一样，依次自动批量处理每一个拖进来的备份文件
        for file_path in file_paths:
            if os.path.isfile(file_path) and (file_path.lower().endswith('.zip') or file_path.lower().endswith('.bin')):
                self.process_single_backup_file(file_path)

    # 处理单个备份文件的核心解压与特征甄别流程
    def process_single_backup_file(self, file_path):
        # 初始插入表格
        item_id = self.table.insert("", tk.END, values=(file_path, "正在解压...", "等待中"))
        self.root.update()
        
        try:
            filename = os.path.basename(file_path).replace('.', '_')
        except:
            filename = "archive"
            
        # 防止批量拖入时发生同名冲突，将 item_id 的微秒后缀融入文件夹名称
        safe_item_name = item_id.replace('.', '_')
        target_env_dir = os.path.join(self.cache_root, f"env_{filename}_{safe_item_name}")
        
        try:
            if os.path.exists(target_env_dir):
                shutil.rmtree(target_env_dir, ignore_errors=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_env_dir)
            
            # 🟢 核心三层深度甄别特征比对算法
            has_session = False
            for dirpath, dirnames, filenames in os.walk(target_env_dir):
                # 判定特征1：存在本地数据持久化层 Local Storage 痕迹
                # 判定特征2：存在官方默认环境数据目录 Default
                if "Local Storage" in dirpath or "Default" in dirnames:
                    has_session = True
                    break
                # 判定特征3：存在常驻网络特征文件
                if any("cookies" in f.lower() or "manifest" in f.lower() or "lock" in f.lower() for f in filenames):
                    has_session = True
                    break
            
            if has_session:
                # 🟢 优化：获取成功后，第一列直接更新展现为获取成功的本地环境存储地址
                self.table.item(item_id, values=(target_env_dir, "获取成功（已就绪）", "双击此行打开浏览器"))
                self.env_map[item_id] = target_env_dir
            else:
                self.table.item(item_id, values=(file_path, "失败：未检测到登录数据", "无"))
                shutil.rmtree(target_env_dir, ignore_errors=True)
        except:
            self.table.item(item_id, values=(file_path, "失败：解压损坏", "无"))
        
        self.root.update()

    # 右键弹出菜单
    def show_context_menu(self, event):
        item_id = self.table.identify_row(event.y)
        if not item_id: return
        self.table.selection_set(item_id)
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="❌ 删除此项并清理缓存", command=lambda: self.delete_row(item_id))
        menu.post(event.x_root, event.y_root)

    # 物理清除对应的解压临时数据文件夹并移除表格
    def delete_row(self, item_id):
        if item_id in self.env_map:
            shutil.rmtree(self.env_map[item_id], ignore_errors=True)
            del self.env_map[item_id]
        self.table.delete(item_id)

    # 双击表格行：拉起桌面上的便携浏览器并强制灌入独立登录会话环境
    def on_table_double_click(self, event):
        item_id = self.table.focus()
        if item_id in self.env_map:
            if not os.path.exists(self.chrome_exe_path):
                messagebox.showerror("错误", f"未在路径找到浏览器，请检查桌面是否存在：\n{self.chrome_exe_path}")
                return
                
            env_dir = self.env_map[item_id]
            # 通过系统指令调用，完美注入 --user-data-dir
            cmd = f'start "" "{self.chrome_exe_path}" --user-data-dir="{env_dir}" --no-first-run --no-default-browser-check "https://whatsapp.com"'
            os.system(cmd)

if __name__ == "__main__":
    root = tk.Tk()
    app = WhatsAppManagerApp(root)
    root.mainloop()
