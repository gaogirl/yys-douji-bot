import threading
from PIL import Image
import pystray
from pystray import MenuItem as Item


class SystemTray:
    def __init__(self, root, on_show=None, on_quit=None):
        self.root = root
        self.on_show = on_show
        self.on_quit = on_quit
        self.tray_icon = None
        self.visible = True

    def _create_image(self):
        width = 64
        height = 64
        color1 = (255, 100, 100)
        color2 = (200, 50, 50)

        image = Image.new('RGB', (width, height), color1)
        pixels = image.load()
        for y in range(height):
            for x in range(width):
                if (x - width//2)**2 + (y - height//2)**2 < (width//3)**2:
                    pixels[x, y] = color2
        return image

    def _on_quit(self, icon, item):
        if self.on_quit:
            self.root.after(0, self.on_quit)

    def _on_show(self, icon, item):
        if self.on_show:
            self.root.after(0, self.on_show)

    def _on_toggle(self, icon, item):
        if self.visible:
            self.root.after(0, self._hide_window)
        else:
            self.root.after(0, self._show_window)

    def _hide_window(self):
        self.root.withdraw()
        self.visible = False

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.visible = True

    def hide_to_tray(self):
        self._hide_window()

    def show_from_tray(self):
        self._show_window()

    def start(self):
        def _run():
            image = self._create_image()
            menu = pystray.Menu(
                Item('显示窗口', self._on_show, default=True),
                Item('退出程序', self._on_quit),
            )
            self.tray_icon = pystray.Icon(
                "yys_douji",
                image,
                "阴阳师斗技自动挂机",
                menu
            )
            self.tray_icon.run()

        threading.Thread(target=_run, daemon=True).start()

    def stop(self):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
