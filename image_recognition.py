import cv2
import numpy as np
import os

from config import TEMPLATE_DIR, DEFAULT_CONFIDENCE


class ImageRecognition:
    def __init__(self):
        self.templates = {}
        self.load_templates()

    def load_templates(self):
        from config import TEMPLATES
        for name, filename in TEMPLATES.items():
            filepath = os.path.join(TEMPLATE_DIR, filename)
            if os.path.exists(filepath):
                template = cv2.imread(filepath, cv2.IMREAD_COLOR)
                if template is not None:
                    self.templates[name] = template

    def find_template(self, screen_img, template_name, confidence=DEFAULT_CONFIDENCE, region=None):
        if template_name not in self.templates:
            return None

        template = self.templates[template_name]

        if region:
            x, y, w, h = region
            screen_img = screen_img[y:y+h, x:x+w]
        else:
            x, y = 0, 0

        if screen_img is None or screen_img.size == 0:
            return None

        th, tw = template.shape[:2]
        sh, sw = screen_img.shape[:2]

        if th > sh or tw > sw:
            return None

        result = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= confidence:
            center_x = max_loc[0] + tw // 2 + x
            center_y = max_loc[1] + th // 2 + y
            return {
                'confidence': max_val,
                'x': center_x,
                'y': center_y,
                'width': tw,
                'height': th,
                'top_left': (max_loc[0] + x, max_loc[1] + y),
                'bottom_right': (max_loc[0] + tw + x, max_loc[1] + th + y)
            }

        return None

    def find_all_templates(self, screen_img, template_name, confidence=DEFAULT_CONFIDENCE, region=None):
        if template_name not in self.templates:
            return []

        template = self.templates[template_name]

        if region:
            x, y, w, h = region
            screen_img = screen_img[y:y+h, x:x+w]
        else:
            x, y = 0, 0

        if screen_img is None or screen_img.size == 0:
            return []

        th, tw = template.shape[:2]
        sh, sw = screen_img.shape[:2]

        if th > sh or tw > sw:
            return []

        result = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= confidence)

        matches = []
        for pt in zip(*locations[::-1]):
            center_x = pt[0] + tw // 2 + x
            center_y = pt[1] + th // 2 + y
            matches.append({
                'confidence': result[pt[1]][pt[0]],
                'x': center_x,
                'y': center_y,
                'width': tw,
                'height': th,
                'top_left': (pt[0] + x, pt[1] + y),
                'bottom_right': (pt[0] + tw + x, pt[1] + th + y)
            })

        return matches

    def has_template(self, template_name):
        return template_name in self.templates
