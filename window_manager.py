import win32gui
import win32ui
import win32con
import win32process
from ctypes import windll
import numpy as np
import psutil
import time

from config import (
    WINDOW_TITLE_KEYWORDS,
    WINDOW_PROCESS_NAMES,
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
)


class WindowManager:
    def __init__(self):
        self.hwnd = None
        self.window_rect = None
        self.window_title = ""
        self.process_name = ""

    def _get_process_name(self, hwnd):
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            return proc.name().lower()
        except:
            return ""

    def _is_valid_window(self, hwnd):
        if not win32gui.IsWindowVisible(hwnd):
            return False

        title = win32gui.GetWindowText(hwnd)
        if not title:
            return False

        title_match = False
        for keyword in WINDOW_TITLE_KEYWORDS:
            if keyword.lower() in title.lower():
                title_match = True
                break

        if not title_match:
            return False

        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            if width < MIN_WINDOW_WIDTH or height < MIN_WINDOW_HEIGHT:
                return False
        except:
            return False

        proc_name = self._get_process_name(hwnd)
        if proc_name:
            proc_match = False
            for proc_keyword in WINDOW_PROCESS_NAMES:
                if proc_keyword.lower() in proc_name:
                    proc_match = True
                    break
            if not proc_match:
                return False

        return True

    def find_window(self):
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

    def screenshot(self, region=None):
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
