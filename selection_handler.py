import time
import win32clipboard
import win32con
import win32api
import win32gui

from config import DEFAULT_CONFIDENCE


class SelectionHandler:
    def __init__(self, window_manager, image_recognition, auto_clicker):
        self.window_manager = window_manager
        self.image_recognition = image_recognition
        self.auto_clicker = auto_clicker

        self.search_button_pos = None
        self.search_input_pos = None
        self.first_card_pos = None
        self.drag_target_y_ratio = 0.45

    def _copy_to_clipboard(self, text):
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            win32clipboard.CloseClipboard()
            return True
        except:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
            return False

    def _paste_clipboard(self):
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(ord('V'), 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.2)

    def _press_enter(self):
        win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.3)

    def _find_search_button(self, screen):
        result = self.image_recognition.find_template(
            screen, 'search_button', confidence=0.7
        )
        if result:
            self.search_button_pos = (result['x'], result['y'])
            return True
        return False

    def _click_search_button(self, screen):
        if self.search_button_pos:
            self.auto_clicker.click(self.search_button_pos[0], self.search_button_pos[1])
            return True

        if self._find_search_button(screen):
            self.auto_clicker.click(self.search_button_pos[0], self.search_button_pos[1])
            return True

        w, h = self.window_manager.get_window_size()
        search_x = int(w * 0.05)
        search_y = int(h * 0.78)
        self.auto_clicker.click(search_x, search_y)
        self.search_button_pos = (search_x, search_y)
        return True

    def _input_text(self, text):
        if not self._copy_to_clipboard(text):
            return False
        self._paste_clipboard()
        return True

    def _get_first_card_position(self, screen):
        w, h = self.window_manager.get_window_size()
        card_x = int(w * 0.18)
        card_y = int(h * 0.82)
        return card_x, card_y

    def _get_drag_target(self, screen):
        w, h = self.window_manager.get_window_size()
        target_y = int(h * self.drag_target_y_ratio)
        return target_y

    def select_shikigami(self, name, screen):
        if not name:
            return True

        self._click_search_button(screen)
        time.sleep(0.3)

        screen = self.window_manager.screenshot()
        if screen is None:
            return False

        self._input_text(name)
        time.sleep(0.5)

        screen = self.window_manager.screenshot()
        if screen is None:
            return False

        card_x, card_y = self._get_first_card_position(screen)
        target_y = self._get_drag_target(screen)

        self.auto_clicker.drag_up(card_x, card_y, distance=card_y - target_y, duration=0.6)
        time.sleep(0.5)

        return True

    def select_onmyouji(self, name, screen):
        if not name:
            return False

        self._click_search_button(screen)
        time.sleep(0.3)

        screen = self.window_manager.screenshot()
        if screen is None:
            return False

        self._input_text(name)
        time.sleep(0.5)

        screen = self.window_manager.screenshot()
        if screen is None:
            return False

        card_x, card_y = self._get_first_card_position(screen)
        target_y = self._get_drag_target(screen)

        self.auto_clicker.drag_up(card_x, card_y, distance=card_y - target_y, duration=0.6)
        time.sleep(0.5)

        return True

    def select_team(self, team, log_callback=None):
        shikigami_list = team.get('shikigami', [])
        onmyouji = team.get('onmyouji', '')

        def log(msg):
            if log_callback:
                log_callback(msg)

        screen = self.window_manager.screenshot()
        if screen is None:
            log("截图失败，无法选人")
            return False

        count = 0
        for name in shikigami_list:
            if not name:
                continue
            log(f"正在选择式神: {name}")
            success = self.select_shikigami(name, screen)
            if success:
                count += 1
            time.sleep(0.8)
            screen = self.window_manager.screenshot()

        log(f"已选择 {count} 个式神")

        if onmyouji:
            log(f"正在选择阴阳师: {onmyouji}")
            self.select_onmyouji(onmyouji, screen)
            time.sleep(0.8)

        return True
