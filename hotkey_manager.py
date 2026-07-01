import threading
import win32api
import win32con
import time


class GlobalHotkey:
    def __init__(self):
        self.callbacks = {}
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()
        self._key_states = {}

    def register(self, key_name, callback):
        vk = self._get_vk_code(key_name)
        if vk is not None:
            self.callbacks[vk] = {
                'callback': callback,
                'last_press': 0,
            }

    def _get_vk_code(self, key_name):
        key_map = {
            'f1': win32con.VK_F1,
            'f2': win32con.VK_F2,
            'f3': win32con.VK_F3,
            'f4': win32con.VK_F4,
            'f5': win32con.VK_F5,
            'f6': win32con.VK_F6,
            'f7': win32con.VK_F7,
            'f8': win32con.VK_F8,
            'f9': win32con.VK_F9,
            'f10': win32con.VK_F10,
            'f11': win32con.VK_F11,
            'f12': win32con.VK_F12,
        }
        return key_map.get(key_name.lower())

    def start(self):
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.stop_event.set()

    def _poll_loop(self):
        while not self.stop_event.is_set():
            for vk, info in self.callbacks.items():
                state = win32api.GetAsyncKeyState(vk)
                if state & 0x8000:
                    now = time.time()
                    if now - info['last_press'] > 0.5:
                        info['last_press'] = now
                        try:
                            info['callback']()
                        except:
                            pass
            time.sleep(0.05)
