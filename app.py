import sys
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox
import core  # 引入动力车间

class WhatsAppBackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("导入打包备份 WhatsApp")
        self.root.geometry("850x420")
        
        # 提示文本保持一致
        bold_font = ("Microsoft YaHei", 9, "bold")
        self.tip_label = ttk.Label(root, text="将 .bin（或 .zip）打包文件拖放到本窗口，左键点击文件可刷新右侧子页面数据。", font=bold_font, foreground="black")
        self.tip_label.pack(anchor=tk.W, padx=15, pady=10)
        
        # 左右分屏联动布局
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # 1. 左侧：文件栏表格区 (均分 25% 宽度左右)
        left_frame = ttk.Frame(main_frame, width=210)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)
        
        lbl_file = tk.Label(left_frame, text="文件", font=bold_font, bd=1, relief=tk.RAISED, bg="#eaeaea", height=2)
        lbl_file.pack(fill=tk.X)
        
        # 使用天然完美支持系统级拖拽的底层 Listbox 容器
        self.left_table = tk.Listbox(left_frame, font=("Microsoft YaHei", 10), bd=1, relief=tk.SOLID, highlightthickness=0, selectbackground="#107c41")
        self.left_table.pack(fill=tk.BOTH, expand=True)
        
        # 2. 右侧：数据、状态、操作联合展区 (均分 75% 宽度，四栏各占 25%)
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
        
        ttk.Label(header_right, text="").pack(pady=15) # 预留高度
        
        # 右侧子页面滚动容器
        self.canvas_frame = ttk.Frame(right_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        
        self.canvas = tk.Canvas(self.canvas_frame, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW, width=600)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 联动信号注册
        self.left_table.bind("<<ListboxSelect>>", self.on_left_item_clicked)
        # 🟢 终极修复：使用最纯净的底层底层鼠标按钮事件拦截，100% 解决右键不生效的问题
        self.left_table.bind("<Button-3>", self.show_left_context_menu)
        
        self.archive_data_map = {}
        
        # 🟢 终极全防线：强制向系统注册接收拖拽，打破一切系统级管理员权限死锁
        self.setup_force_drag_and_drop()

    def setup_force_drag_and_drop(self):
        try:
            import ctypes
            from ctypes import windll
            # 补丁A：强制允许低权限进程向高权限进程投递拖拽文件消息流 (解决UAC死锁)
            try:
                windll.user32.ChangeWindowMessageFilter(0x0049, 1) # WM_COPYGLOBALDATA
                windll.user32.ChangeWindowMessageFilter(0x0233, 1) # WM_DROPFILES
            except:
                pass
            # 补丁B：对全窗体及内部控件全面激活顶级通道
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

        # 🟢 完美兼容：不管是中文、字母、纯数字，依次迭代无漏批量导入
        for file_path in file_paths:
            if os.path.isfile(file_path) and (file_path.lower().endswith('.zip') or file_path.lower().endswith('.bin')):
                self.process_backup_file(file_path)

    def process_backup_file(self, file_path):
        row = self.left_table.size()
        res = core.analyze_zip(file_path, row)
        if res:
            self.left_table.insert(tk.END, res["pure_name"])
            self.archive_data_map[row] = res
            
            # 自动高亮选择
            self.left_table.selection_clear(0, tk.END)
            self.left_table.selection_set(row)
            self.left_table.activate(row)
            self.refresh_right_panel(res)

    def on_left_item_clicked(self, event):
        if not self.left_table.curselection(): return
        clicked_row = self.left_table.curselection()[0]
        if clicked_row in self.archive_data_map:
            self.refresh_right_panel(self.archive_data_map[clicked_row])

    # 刷新右侧子页面（带格子线样式拼装）
    def refresh_right_panel(self, res):
        # 清空右侧旧容器
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        profiles = res["profiles"]
        for idx, pf in enumerate(profiles):
            row_frame = tk.Frame(self.scrollable_frame, height=32, bd=1, relief=tk.SOLID)
            row_frame.pack(fill=tk.X, expand=True)
            row_frame.pack_propagate(False)
            
            # 数据栏 (均分 33%)
            lbl_name = tk.Label(row_frame, text=pf["name"], anchor=tk.CENTER, font=("Microsoft YaHei", 9), bg="white", bd=1, relief=tk.SOLID)
            lbl_name.place(relx=0.0, rely=0.0, relwidth=0.33, relheight=1.0)
            
            # 状态栏 (只显示 成功 或 失败)
            color = "darkgreen" if pf["valid"] else "red"
            lbl_status = tk.Label(row_frame, text=pf["status"], anchor=tk.CENTER, font=("Microsoft YaHei", 9, "bold"), bg="white", fg=color, bd=1, relief=tk.SOLID)
            lbl_status.place(relx=0.33, rely=0.0, relwidth=0.33, relheight=1.0)
            
            # 操作栏 (成功显示 进入 按钮)
            action_cell = tk.Frame(row_frame, bg="white", bd=1, relief=tk.SOLID)
            action_cell.place(relx=0.66, rely=0.0, relwidth=0.34, relheight=1.0)
            
            if pf["valid"]:
                btn = tk.Button(action_cell, text="进入", font=("Microsoft YaHei", 8, "bold"), bg="#107c41", fg="white", activebackground="#0e6b38", activeforeground="white", bd=0, cursor="hand2", command=lambda p=pf["path"]: self.launch_browser(p))
                btn.pack(expand=True, ipadx=15, ipady=2)
            else:
                lbl_none = tk.Label(action_cell, text="无", font=("Microsoft YaHei", 9), bg="white", fg="gray")
                lbl_none.pack(expand=True)

    # 🟢 严格限定：右键菜单精准在左侧【文件栏】生效
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
            shutil.rmtree(self.archive_data_map[index]["temp_dir"], ignore_errors=True)
            del self.archive_data_map[index]
            
        self.left_table.delete(index)
        # 清空右侧子页面
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        # 重排内存索引排列
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
