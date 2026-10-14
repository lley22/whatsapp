import sys
import os
import re
import urllib.parse
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import core  # 引入动力车间

class WhatsAppBackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("导入打包备份 WhatsApp")
        self.root.geometry("850x420")
        
        # 提示文本与参考图保持高度黑色加粗一致
        bold_font = ("Microsoft YaHei", 9, "bold")
        self.tip_label = ttk.Label(root, text="将 .bin（或 .zip）打包文件拖放到本窗口，选中后点执行自动解压并登录。", font=bold_font, foreground="black")
        self.tip_label.pack(anchor=tk.W, padx=15, pady=10)
        
        # 左右分屏联动布局：确保四栏各占完美的 25% 比例位置
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # 1. 左侧：文件父栏目展区 (等宽占 25% 宽度比例)
        left_frame = ttk.Frame(main_frame, width=220)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)
        
        lbl_file = tk.Label(left_frame, text="文件", font=bold_font, bd=1, relief=tk.RAISED, bg="#eaeaea", height=2)
        lbl_file.pack(fill=tk.X)
        
        # 导入按钮双保险
        self.btn_import = tk.Button(left_frame, text="➕ 批量选择导入 (支持多选)", font=("Microsoft YaHei", 9, "bold"), bg="#107c41", fg="white", activebackground="#0e6b38", activeforeground="white", bd=0, height=2, cursor="hand2", command=self.batch_import_files)
        self.btn_import.pack(fill=tk.X, pady=(2, 2))
        
        # 左侧文件单列网格框
        self.left_table = tk.Listbox(left_frame, font=("Microsoft YaHei", 10), bd=1, relief=tk.SOLID, highlightthickness=0, selectbackground="#107c41")
        self.left_table.pack(fill=tk.BOTH, expand=True)
        
        # 2. 右侧：数据、状态、操作联合展区 (各栏目占 25% 的等宽比例位置)
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        header_right = ttk.Frame(right_frame)
        header_right.pack(fill=tk.X)
        
        lbl_data = tk.Label(header_right, text="数据", font=bold_font, bd=1, relief=tk.RAISED, bg="#eaeaea", height=2)
        lbl_data.place(relx=0.0, rely=0.0, relwidth=0.33)
        lbl_status = tk.Label(header_right, text="状态", font=bold_font, bd=1, relief=tk.RAISED, bg="#eaeaea", height=2)
        lbl_status.place(relx=0.33, rely=0.0, relwidth=0.33)
        lbl_action = tk.Label(header_right, text="操作", font=bold_font, bd=1, relief=tk.RAISED, bg="#eaeaea", height=2)
        lbl_action.place(relx=0.66, rely=0.0, relwidth=0.34)
        
        ttk.Label(header_right, text="").pack(pady=15) # 预留表头高度
        
        # 右侧子页面滑动内容面板
        self.canvas_frame = ttk.Frame(right_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        
        self.canvas = tk.Canvas(self.canvas_frame, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW, width=590)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 联动信号与精准鼠标事件绑定
        self.left_table.bind("<<ListboxSelect>>", self.on_left_item_clicked)
        self.left_table.bind("<Button-3>", self.show_left_context_menu)
        
        self.archive_data_map = {}
        
        # 激活高级文件拖放流
        try:
            import ctypes
            from ctypes import windll
            windll.shell32.DragAcceptFiles(self.root.winfo_id(), True)
            self.root.tk.createcommand("::tk::mac::OpenDocument", self.handle_global_drop)
            self.root.bind("<Drop>", self.handle_global_drop)
        except:
            pass

    def batch_import_files(self):
        file_paths = filedialog.askopenfilenames(
            title="选择 WhatsApp 备份文件", 
            filetypes=[("Backup Files", "*.zip *.bin")]
        )
        if not file_paths: return
        for file_path in file_paths:
            if os.path.isfile(file_path): self.process_single_file(file_path)

    # 🟢 核心修复：彻底废除容易切断带空格中文包名的 .split()，改用原生大括号边界安全解析提取算法
    def handle_global_drop(self, *args):
        if not args: return
        
        # 将传入的数据转化为包含全部完整空格的原始物理长字符串
        raw_drop_str = " ".join([str(arg) for arg in args if arg])
        
        file_paths = []
        # 利用正则表达式，完美捕捉被 Windows 系统用大括号 {} 包裹起来的含空格/中文的绝对完整路径
        if "{" in raw_drop_str:
            file_paths = re.findall(r'\{([^}]+)\}', raw_drop_str)
            # 过滤掉大括号后，提取出剩下没有空格的干净路径
            remain_str = re.sub(r'\{[^}]+\}', '', raw_drop_str)
            file_paths.extend([p.strip() for p in remain_str.split() if p.strip()])
        else:
            # 针对没有空格的路径，使用安全的系统原生多参数流逐个提取，绝不发生字符串截断
            file_paths = [str(arg).strip('{} ') for arg in args if arg]

        # 循环依次处理拉入的每一个包文件
        for file_path in file_paths:
            # 安全解码可能存在的 URL 网页转义字符
            try:
                file_path = urllib.parse.unquote(file_path)
            except:
                pass
            if os.path.isfile(file_path) and (file_path.lower().endswith('.zip') or file_path.lower().endswith('.bin')):
                self.process_single_file(file_path)

    def process_single_file(self, file_path):
        row = self.left_table.size()
        res = core.analyze_zip(file_path, row)
        if res:
            # 🟢 文件一栏：不论包名叫中文、数字、字母还是带大片空格，100% 完美完整展现包名本身
            self.left_table.insert(tk.END, res["pure_name"])
            self.archive_data_map[row] = res
            
            # 自动高亮并联动刷新右侧
            self.left_table.selection_clear(0, tk.END)
            self.left_table.selection_set(row)
            self.left_table.activate(row)
            self.refresh_right_panel(res)

    def on_left_item_clicked(self, event):
        if not self.left_table.curselection(): return
        clicked_row = self.left_table.curselection()[0]
        if clicked_row in self.archive_data_map:
            self.refresh_right_panel(self.archive_data_map[clicked_row])

    def refresh_right_panel(self, res):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        profiles = res["profiles"]
        for idx, pf in enumerate(profiles):
            row_frame = tk.Frame(self.scrollable_frame, height=32, bd=1, relief=tk.SOLID)
            row_frame.pack(fill=tk.X, expand=True)
            row_frame.pack_propagate(False)
            
            # 数据列
            lbl_name = tk.Label(row_frame, text=pf["name"], anchor=tk.CENTER, font=("Microsoft YaHei", 9), bg="white", bd=1, relief=tk.SOLID)
            lbl_name.place(relx=0.0, rely=0.0, relwidth=0.33, relheight=1.0)
            
            # 状态列 (干净的“成功”或“失败”)
            color = "darkgreen" if pf["valid"] else "red"
            lbl_status = tk.Label(row_frame, text=pf["status"], anchor=tk.CENTER, font=("Microsoft YaHei", 9, "bold"), bg="white", fg=color, bd=1, relief=tk.SOLID)
            lbl_status.place(relx=0.33, rely=0.0, relwidth=0.33, relheight=1.0)
            
            # 操作列 (进入按钮)
            action_cell = tk.Frame(row_frame, bg="white", bd=1, relief=tk.SOLID)
            action_cell.place(relx=0.66, rely=0.0, relwidth=0.34, relheight=1.0)
            
            if pf["valid"]:
                btn = tk.Button(action_cell, text="进入", font=("Microsoft YaHei", 8, "bold"), bg="#107c41", fg="white", activebackground="#0e6b38", activeforeground="white", bd=0, cursor="hand2", command=lambda p=pf["path"]: self.launch_browser(p))
                btn.pack(expand=True, ipadx=15, ipady=2)
            else:
                lbl_none = tk.Label(action_cell, text="无", font=("Microsoft YaHei", 9), bg="white", fg="gray")
                lbl_none.pack(expand=True)

    # 🟢 联动修复：精准在【文件栏】行上绑定并弹现右键删除菜单
    def show_left_context_menu(self, event):
        index = self.left_table.nearest(event.y)
        if index < 0 or index >= self.left_table.size(): return
        
        self.left_table.selection_clear(0, tk.END)
        self.left_table.selection_set(index)
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="❌ 删除整个包并清理缓存", command=lambda: self.delete_archive_package(index))
        menu.post(event.x_root, event.y_root)

    def delete_archive_package(self, index):
        if index in self.archive_data_map:
            core.shutil.rmtree(self.archive_data_map[index]["temp_dir"], ignore_errors=True)
            del self.archive_data_map[index]
            
        self.left_table.delete(index)
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        # 重整内存轨道映射
        new_map = {}
        for idx in range(self.left_table.size()):
            for old_k, old_v in self.archive_data_map.items():
                if idx <= old_k:
                    new_map[idx] = old_v
                    break
        self.archive_data_map = new_map

    def launch_browser(self, p_path):
        if not core.run_chrome(p_path):
            messagebox.showerror("错误", f"未找到浏览器，请检查桌面是否存在：\n{core.CHROME_EXE}")

if __name__ == "__main__":
    root = tk.Tk()
    app = WhatsAppBackupApp(root)
    root.mainloop()
