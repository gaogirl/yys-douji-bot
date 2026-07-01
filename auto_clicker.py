import win32api
import win32con
import time
import random
import math

from config import ANTI_DETECT


class AutoClicker:
    def __init__(self, window_manager):
        self.window_manager = window_manager
        self.last_click_time = 0

    def _random_offset(self, x, y):
        offset = ANTI_DETECT['click_offset_range']
        x += random.randint(-offset, offset)
        y += random.randint(-offset, offset)
        return x, y

    def _random_click_duration(self):
        return random.uniform(
            ANTI_DETECT['click_duration_min'],
            ANTI_DETECT['click_duration_max']
        )

    def _random_post_delay(self):
        delay = random.uniform(
            ANTI_DETECT['post_click_delay_min'],
            ANTI_DETECT['post_click_delay_max']
        )
        time.sleep(delay)

    def _move_mouse_smooth(self, target_x, target_y):
        steps = ANTI_DETECT['mouse_move_steps']
        duration = ANTI_DETECT['mouse_move_duration']

        current_x, current_y = win32api.GetCursorPos()

        dx = target_x - current_x
        dy = target_y - current_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 5:
            win32api.SetCursorPos((target_x, target_y))
            return

        for i in range(1, steps + 1):
            t = i / steps
            ease_t = t * t * (3 - 2 * t)

            mid_x = current_x + dx / 2 + random.randint(-10, 10)
            mid_y = current_y + dy / 2 + random.randint(-10, 10)

            x = int((1 - ease_t) * (1 - ease_t) * current_x +
                    2 * (1 - ease_t) * ease_t * mid_x +
                    ease_t * ease_t * target_x)
            y = int((1 - ease_t) * (1 - ease_t) * current_y +
                    2 * (1 - ease_t) * ease_t * mid_y +
                    ease_t * ease_t * target_y)

            win32api.SetCursorPos((x, y))
            time.sleep(duration / steps)

    def click(self, x, y, random_offset=True, smooth_move=True):
        if random_offset:
            x, y = self._random_offset(x, y)

        screen_x, screen_y = self.window_manager.client_to_screen(x, y)

        if smooth_move:
            self._move_mouse_smooth(screen_x, screen_y)
        else:
            win32api.SetCursorPos((screen_x, screen_y))
            time.sleep(0.05)

        duration = self._random_click_duration()

        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, screen_x, screen_y, 0, 0)
        time.sleep(duration)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, screen_x, screen_y, 0, 0)

        self._random_post_delay()
        self.last_click_time = time.time()

        return True

    def click_match_result(self, match_result, smooth_move=True):
        if match_result:
            return self.click(match_result['x'], match_result['y'], smooth_move=smooth_move)
        return False

    def move_to(self, x, y, smooth=True):
        screen_x, screen_y = self.window_manager.client_to_screen(x, y)
        if smooth:
            self._move_mouse_smooth(screen_x, screen_y)
        else:
            win32api.SetCursorPos((screen_x, screen_y))

    def drag(self, from_x, from_y, to_x, to_y, duration=0.5, smooth=True):
        screen_from_x, screen_from_y = self.window_manager.client_to_screen(from_x, from_y)
        screen_to_x, screen_to_y = self.window_manager.client_to_screen(to_x, to_y)

        if smooth:
            self._move_mouse_smooth(screen_from_x, screen_from_y)
        else:
            win32api.SetCursorPos((screen_from_x, screen_from_y))
            time.sleep(0.1)

        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, screen_from_x, screen_from_y, 0, 0)
        time.sleep(0.1)

        steps = 30
        step_delay = duration / steps
        for i in range(1, steps + 1):
            t = i / steps
            ease_t = t * t * (3 - 2 * t)
            x = int(screen_from_x + (screen_to_x - screen_from_x) * ease_t)
            y = int(screen_from_y + (screen_to_y - screen_from_y) * ease_t)
            win32api.SetCursorPos((x, y))
            time.sleep(step_delay)

        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, screen_to_x, screen_to_y, 0, 0)
        self._random_post_delay()
        self.last_click_time = time.time()

        return True

    def drag_up(self, x, y, distance=300, duration=0.5):
        return self.drag(x, y, x, y - distance, duration)
