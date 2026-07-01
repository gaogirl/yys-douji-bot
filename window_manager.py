import win32gui
import win32ui
import win32con
import win32process
from ctypes import windll
import numpy as np
import psutil
import time
import tkinter as tk
from tkinter import ttk

try:
    import dxcam
    DXCAM_AVAILABLE = True
except ImportError:
    DXCAM_AVAILABLE = False

from config import (
    WINDOW_TITLE_KEYWORDS,
    WINDOW_PROCESS_NAMES,
    EMULATOR_TITLE_KEYWORDS,
    EMULATOR_PROCESS_NAMES,
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
)


class WindowManager:
    def __init__(self):
        self.hwnd = None
        self.window_rect = None
        self.window_title = ""
        self.process_name = ""
        self.manual_region = None  # (left, top, width, height) in screen coords
        self._dxcam = None

    def _get_process_name(self, hwnd):
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            return proc.name().lower()
        except:
            return ""

    def _matches_title_keywords(self, title):
        """检查标题是否匹配任何关键词（传统 + 模拟器，任一命中即可）。"""
        title_lower = title.lower()
        keywords = WINDOW_TITLE_KEYWORDS + EMULATOR_TITLE_KEYWORDS
        for kw in keywords:
            if kw.lower() in title_lower:
                return True
        return False

    def _matches_process_keywords(self, proc_name):
        """检查进程名是否匹配任何关键词（传统 + 模拟器，任一命中即可）。"""
        if not proc_name:
            return False
        keywords = WINDOW_PROCESS_NAMES + EMULATOR_PROCESS_NAMES
        for kw in keywords:
            if kw.lower() in proc_name:
                return True
        return False

    def _is_valid_window(self, hwnd):
        if not win32gui.IsWindowVisible(hwnd):
            return False

        title = win32gui.GetWindowText(hwnd)
        if not title:
            return False

        # 标题匹配（宽松：传统或模拟器关键词任一命中）
        if not self._matches_title_keywords(title):
            return False

        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            if width < MIN_WINDOW_WIDTH or height < MIN_WINDOW_HEIGHT:
                return False
        except:
            return False

        # 进程匹配（宽松：传统或模拟器关键词任一命中）
        proc_name = self._get_process_name(hwnd)
        if not self._matches_process_keywords(proc_name):
            return False

        return True

    def find_window(self):
        """查找第一个匹配的窗口（按面积从大到小排序，取最大的）。"""
        def callback(hwnd, windows):
            if self._is_valid_window(hwnd):
                title = win32gui.GetWindowText(hwnd)
                proc_name = self._get_process_name(hwnd)
                windows.append((hwnd, title, proc_name))
            return True

        windows = []
        win32gui.EnumWindows(callback, windows)

        if not windows:
            self.hwnd = None
            self.window_rect = None
            self.window_title = ""
            self.process_name = ""
            return False

        windows.sort(key=lambda x: (
            win32gui.GetWindowRect(x[0])[2] - win32gui.GetWindowRect(x[0])[0]
        ) * (win32gui.GetWindowRect(x[0])[3] - win32gui.GetWindowRect(x[0])[1]),
            reverse=True
        )

        self.hwnd = windows[0][0]
        self.window_title = windows[0][1]
        self.process_name = windows[0][2]
        self.update_window_rect()
        return True

    def set_hwnd_by_selection(self, hwnd, title, proc_name):
        """通过可视化选择器手动设置窗口。"""
        self.hwnd = hwnd
        self.window_title = title
        self.process_name = proc_name
        self.update_window_rect()

    def update_window_rect(self):
        if self.hwnd:
            try:
                self.window_rect = win32gui.GetWindowRect(self.hwnd)
            except:
                pass

    def get_window_size(self):
        if self.window_rect:
            left, top, right, bottom = self.window_rect
            return right - left, bottom - top
        return 0, 0

    def get_window_info(self):
        return {
            'title': self.window_title,
            'process': self.process_name,
            'size': self.get_window_size(),
        }

    def _ensure_dxcam(self):
        """懒初始化 dxcam 对象。"""
        if self._dxcam is None and DXCAM_AVAILABLE:
            try:
                self._dxcam = dxcam.create(device_idx=0, output_idx=0)
            except:
                self._dxcam = False  # 标记为不可用
        return self._dxcam if self._dxcam is not False else None

    def _screenshot_dxcam(self, region=None):
        """使用 DirectX 帧捕获截图。"""
        cam = self._ensure_dxcam()
        if cam is None:
            return None

        try:
            if region:
                # dxcam.grab(region=(x, y, w, h))
                img = cam.grab(region=region)
            else:
                img = cam.grab()

            if img is None:
                return None

            # dxcam 返回 BGR 格式，转为 RGB
            img = img[:, :, ::-1]
            return img
        except:
            return None

    def _screenshot_printwindow(self, region=None):
        """使用 PrintWindow 截图（传统方案，适用于原生窗口）。"""
        if not self.hwnd:
            return None

        try:
            left, top, right, bottom = self.window_rect
            width = right - left
            height = bottom - top

            if region:
                rx, ry, rw, rh = region
                left += rx
                top += ry
                width = rw
                height = rh

            hwndDC = win32gui.GetWindowDC(self.hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            result = windll.user32.PrintWindow(self.hwnd, saveDC.GetSafeHdc(), 2)

            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)

            img = np.frombuffer(bmpstr, dtype='uint8')
            img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
            img = img[:, :, :3]
            img = img[:, :, ::-1].copy()

            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(self.hwnd, hwndDC)

            if result == 0:
                return None

            return img
        except:
            return None

    def screenshot(self, region=None):
        """截图：优先 dxcam → 降级 PrintWindow。

        Args:
            region: 可选的额外裁剪区域 (x, y, w, h)，相对于整个屏幕。
        """
        # 如果用户使用了手动框选模式
        if self.manual_region:
            result = self._screenshot_dxcam(self.manual_region)
            if result is not None:
                return result
            result = self._screenshot_printwindow(self.manual_region)
            if result is not None:
                return result
            return None

        # 正常流程：先尝试 dxcam
        result = self._screenshot_dxcam(region)
        if result is not None:
            return result

        # 降级到 PrintWindow
        if region:
            if not self.window_rect:
                return None
            rx, ry, rw, rh = region
            left, top, right, bottom = self.window_rect
            region = (left + rx, top + ry, rw, rh)
        return self._screenshot_printwindow(region)

    def screen_to_client(self, x, y):
        if not self.window_rect:
            return x, y
        left, top, _, _ = self.window_rect
        return x - left, y - top

    def client_to_screen(self, x, y):
        if not self.window_rect:
            return x, y
        left, top, _, _ = self.window_rect
        return x + left, y + top

    def bring_to_front(self):
        if self.hwnd:
            try:
                win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.hwnd)
                time.sleep(0.3)
            except:
                pass

    # ================================================================
    # 可视化窗口选择器
    # ================================================================

    def show_window_selector_dialog(self, parent):
        """弹出窗口选择器对话框，让用户可视化地选择目标窗口。"""

        dialog = tk.Toplevel(parent)
        dialog.title("选择游戏窗口")
        dialog.geometry("800x500")
        dialog.resizable(True, True)
        dialog.transient(parent)
        dialog.grab_set()

        # 收集所有匹配窗口
        candidates = []

        def callback(hwnd, data):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        proc = psutil.Process(pid)
                        proc_name = proc.name()
                    except:
                        proc_name = ""
                    try:
                        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                        w, h = right - left, bottom - top
                    except:
                        w, h = 0, 0
                    candidates.append((hwnd, title, proc_name, w, h))
            return True

        win32gui.EnumWindows(callback, None)

        # 也收集模拟器关键词匹配的窗口（更宽松的标题匹配）
        emulator_candidates_set = set(c[0] for c in candidates)
        def em_callback(hwnd, data):
            if hwnd in emulator_candidates_set:
                return True
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    title_lower = title.lower()
                    for kw in EMULATOR_TITLE_KEYWORDS:
                        if kw.lower() in title_lower:
                            try:
                                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                                proc = psutil.Process(pid)
                                proc_name = proc.name()
                            except:
                                proc_name = ""
                            try:
                                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                                w, h = right - left, bottom - top
                                if w >= 400 and h >= 300:  # 更宽松的尺寸要求
                                    candidates.append((hwnd, title, proc_name, w, h))
                                    break
                            except:
                                pass
            return True

        win32gui.EnumWindows(em_callback, None)

        # 按面积降序
        candidates.sort(key=lambda x: x[3] * x[4], reverse=True)

        info_label = ttk.Label(dialog, text=f"找到 {len(candidates)} 个候选窗口", font=("Microsoft YaHei", 9))
        info_label.pack(pady=(8, 4))

        # 表格
        tree_frame = ttk.Frame(dialog)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("title", "process", "size")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)
        tree.heading("title", text="窗口标题")
        tree.heading("process", text="进程名")
        tree.heading("size", text="尺寸")
        tree.column("title", width=400)
        tree.column("process", width=120)
        tree.column("size", width=80, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        selected_idx = [0]  # 用列表方便闭包修改

        for i, (hwnd, title, proc_name, w, h) in enumerate(candidates):
            tree.insert("", tk.END, values=(title, proc_name, f"{w}×{h}"), tags=(i,))
            tree.tag_configure(i, font=("Microsoft YaHei", 9))

        def on_select(event):
            selection = tree.selection()
            if selection:
                selected_idx[0] = int(tree.item(selection[0])["tags"][0])

        tree.bind("<<TreeviewSelect>>", on_select)

        # 默认选中第一项（最大窗口）
        if candidates:
            tree.selection_set(0)
            tree.focus(0)
            tree.see(0)

        # 底部按钮
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(8, 10), fill=tk.X, padx=10)

        def on_confirm():
            idx = selected_idx[0]
            if idx < len(candidates):
                hwnd, title, proc_name, w, h = candidates[idx]
                self.set_hwnd_by_selection(hwnd, title, proc_name)
                dialog.destroy()
            else:
                tk.messagebox.showwarning("提示", "未选择有效窗口")

        ttk.Button(btn_frame, text="确认选择", command=on_confirm, width=12).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="手动框选", command=lambda: (_manual_select_and_destroy(dialog, candidates),), width=10).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="取消", command=dialog.destroy, width=8).pack(side=tk.RIGHT)

    def manual_region_select(self, parent):
        """全屏手动框选模式：创建一个覆盖层，用户拖拽选择区域。"""

        # 隐藏主窗口
        parent.withdraw()

        overlay = tk.Toplevel(None)
        overlay.title("")
        overlay.configure(cursor="cross")

        # 全屏
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", 0.3)
        overlay.configure(bg="#000000")

        # 半透明效果
        overlay.attributes("-transparentcolor", "#000000")

        # 绘制选区的 Canvas
        canvas = tk.Canvas(overlay, highlightthickness=0, bg="#000000")
        canvas.pack(fill=tk.BOTH, expand=True)

        rect_ref = [None]
        drag_start = [None, None]
        current_pos = [None, None]
        done = [False]
        result_region = [None]

        def on_press(event):
            drag_start[0] = event.x
            drag_start[1] = event.y
            if rect_ref[0]:
                canvas.delete(rect_ref[0])
            rect_ref[0] = canvas.create_rectangle(
                event.x, event.y, event.x, event.y,
                outline="#00ff00", fill="#00ff0022", width=2
            )

        def on_drag(event):
            if rect_ref[0]:
                canvas.coords(rect_ref[0], drag_start[0], drag_start[1], event.x, event.y)
            current_pos[0] = event.x
            current_pos[1] = event.y

        def on_release(event):
            end_x = event.x
            end_y = event.y
            # 规范化坐标
            x1 = min(drag_start[0], end_x)
            y1 = min(drag_start[1], end_y)
            x2 = max(drag_start[0], end_x)
            y2 = max(drag_start[1], end_y)
            w = x2 - x1
            h = y2 - y1

            if w < 100 or h < 100:
                tk.messagebox.showwarning("提示", "选区太小，请重新选择")
                done[0] = False
                overlay.destroy()
                parent.deiconify()
                return

            result_region[0] = (x1, y1, w, h)
            done[0] = True
            overlay.destroy()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)

        # 提示文字
        canvas.create_text(
            overlay.winfo_width() // 2, 30,
            text="拖拽鼠标选择游戏窗口区域，释放确认",
            fill="white", font=("Microsoft YaHei", 12)
        )

        overlay.update()
        # 更新提示位置到中心
        canvas.coords(rect_ref[0] if rect_ref[0] else 0, 0, 0, 0)

        # 等待用户操作
        overlay.wait_window()

        # 恢复主窗口
        parent.deiconify()

        if done[0] and result_region[0]:
            self.manual_region = result_region[0]
            self.hwnd = None  # 清除 hwnd，因为使用的是手动区域
            self.window_rect = (self.manual_region[0], self.manual_region[1],
                               self.manual_region[0] + self.manual_region[2],
                               self.manual_region[1] + self.manual_region[3])
            self.window_title = "(手动框选)"
            self.process_name = ""
            return True
        return False
