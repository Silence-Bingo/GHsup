"""
GitHub 加速器 - GUI 模块
提供图形界面和系统托盘功能
"""

import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Callable, Dict, List, Optional, Tuple

import pystray
from PIL import Image, ImageDraw


class TextRedirector:
    """将 print 输出重定向到 Text 控件"""

    def __init__(self, text_widget: tk.Text):
        self.text_widget = text_widget

    def write(self, text: str):
        self.text_widget.after(0, self._append, text)

    def _append(self, text: str):
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, text)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass


class GitHubAcceleratorGUI:
    """主界面类"""

    def __init__(
        self,
        on_refresh: Callable[[], None],
        on_disable: Callable[[], None],
        on_enable: Callable[[], None],
    ):
        self.on_refresh = on_refresh
        self.on_disable = on_disable
        self.on_enable = on_enable

        self.root = tk.Tk()
        self.root.title("GitHub 加速器")
        self.root.geometry("600x500")
        self.root.resizable(False, False)

        # 状态变量
        self.status_var = tk.StringVar(value="就绪")
        self.last_update_var = tk.StringVar(value="上次更新: 从未")
        self.auto_refresh_var = tk.BooleanVar(value=True)

        self._setup_ui()
        self._setup_tray()

        # 重定向 print 输出到日志区域
        import sys
        sys.stdout = TextRedirector(self.log_text)

    def _setup_ui(self):
        """设置 UI"""
        # 顶部状态栏
        status_frame = ttk.Frame(self.root, padding="10")
        status_frame.pack(fill=tk.X)

        ttk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Microsoft YaHei", 12, "bold")
        ).pack(side=tk.LEFT)

        ttk.Label(
            status_frame,
            textvariable=self.last_update_var,
            font=("Microsoft YaHei", 9)
        ).pack(side=tk.RIGHT)

        # 按钮区域
        btn_frame = ttk.Frame(self.root, padding="5")
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame,
            text="立即加速",
            command=self._on_refresh_click
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="禁用加速",
            command=self._on_disable_click
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="启用加速",
            command=self._on_enable_click
        ).pack(side=tk.LEFT, padx=5)

        ttk.Checkbutton(
            btn_frame,
            text="每小时自动刷新",
            variable=self.auto_refresh_var,
            command=self._on_auto_refresh_toggle
        ).pack(side=tk.RIGHT, padx=5)

        # 当前 hosts 条目显示
        entries_frame = ttk.LabelFrame(self.root, text="当前加速域名", padding="5")
        entries_frame.pack(fill=tk.X, padx=10, pady=5)

        self.entries_text = scrolledtext.ScrolledText(
            entries_frame,
            height=8,
            state="disabled",
            font=("Consolas", 9)
        )
        self.entries_text.pack(fill=tk.X)

        # 日志区域
        log_frame = ttk.LabelFrame(self.root, text="运行日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            state="disabled",
            font=("Consolas", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _setup_tray(self):
        """设置系统托盘图标"""
        # 创建一个简单的图标
        icon_image = self._create_icon_image()

        menu = pystray.Menu(
            pystray.MenuItem("显示主窗口", self._show_window),
            pystray.MenuItem("立即刷新", self._tray_refresh),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._quit)
        )

        self.tray_icon = pystray.Icon(
            "GitHub Accelerator",
            icon_image,
            "GitHub 加速器",
            menu
        )

    def _create_icon_image(self) -> Image.Image:
        """创建托盘图标"""
        # 创建一个简单的 64x64 图标
        size = 64
        image = Image.new("RGB", (size, size), (36, 41, 46))
        draw = ImageDraw.Draw(image)

        # 画一个简单的 "G" 字形
        draw.ellipse([8, 8, 56, 56], outline=(88, 166, 255), width=4)
        draw.arc([8, 8, 56, 56], -45, 90, fill=(88, 166, 255), width=4)
        draw.line([32, 32, 48, 32], fill=(88, 166, 255), width=4)

        return image

    def _show_window(self, icon=None, item=None):
        """显示主窗口"""
        self.root.after(0, self._deiconify)

    def _deiconify(self):
        self.root.deiconify()
        self.root.lift()

    def _hide_window(self):
        """隐藏主窗口到托盘"""
        self.root.withdraw()

    def _quit(self, icon=None, item=None):
        """退出应用"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

    def _on_refresh_click(self):
        """刷新按钮点击"""
        threading.Thread(target=self.on_refresh, daemon=True).start()

    def _on_disable_click(self):
        """禁用按钮点击"""
        try:
            self.on_disable()
            self.status_var.set("已禁用")
            messagebox.showinfo("成功", "已移除加速 hosts 条目")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _on_enable_click(self):
        """启用按钮点击"""
        try:
            self.on_enable()
            self.status_var.set("已启用")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _on_auto_refresh_toggle(self):
        """自动刷新开关"""
        # 这个逻辑在主程序中处理
        pass

    def _tray_refresh(self, icon=None, item=None):
        """托盘菜单刷新"""
        threading.Thread(target=self.on_refresh, daemon=True).start()

    def update_status(self, status: str):
        """更新状态文本"""
        self.root.after(0, lambda: self.status_var.set(status))

    def update_last_time(self, time_str: str):
        """更新上次更新时间"""
        self.root.after(0, lambda: self.last_update_var.set(f"上次更新: {time_str}"))

    def update_entries_display(self, entries: Dict[str, str]):
        """更新当前条目显示"""
        def _update():
            self.entries_text.configure(state="normal")
            self.entries_text.delete(1.0, tk.END)
            for domain, ip in entries.items():
                self.entries_text.insert(tk.END, f"{ip}\t{domain}\n")
            self.entries_text.configure(state="disabled")

        self.root.after(0, _update)

    def run(self):
        """运行应用"""
        # 处理窗口关闭事件 - 最小化到托盘
        self.root.protocol("WM_DELETE_WINDOW", self._hide_window)

        # 启动托盘图标（在后台线程）
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

        # 运行主循环
        self.root.mainloop()

    def destroy(self):
        """销毁窗口"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()
