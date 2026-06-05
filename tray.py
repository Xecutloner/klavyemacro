"""
tray.py - Sistem tepsisi entegrasyonu
"""

import threading
import pystray
from PIL import Image, ImageDraw, ImageFont


def _create_icon_image():
    """Bellek içinde basit bir ikon oluşturur."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Arka plan (mor daire)
    draw.ellipse([2, 2, size - 2, size - 2], fill="#7c3aed")

    # Klavye gövdesi (beyaz)
    draw.rounded_rectangle([10, 20, 54, 46], radius=4, fill="white")

    # Tuşlar - satır 1
    for x in [14, 21, 28, 35, 42]:
        draw.rectangle([x, 23, x + 5, 28], fill="#7c3aed")

    # Tuşlar - satır 2
    for x in [14, 21, 28, 35, 42]:
        draw.rectangle([x, 31, x + 5, 36], fill="#7c3aed")

    # Boşluk tuşu
    draw.rectangle([18, 39, 46, 43], fill="#5b21b6")

    return img


class SystemTray:
    def __init__(self, on_show: callable, on_quit: callable):
        self.on_show = on_show
        self.on_quit = on_quit
        self._tray = None
        self._thread = None

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem("⌨  KlavyeMacro Aç", lambda: self.on_show(), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌  Çıkış", lambda: self._quit()),
        )

    def _quit(self):
        if self._tray:
            self._tray.stop()
        self.on_quit()

    def start(self):
        """Sistem tepsisi ikonunu başlatır (ayrı thread'de)."""
        icon_img = _create_icon_image()
        self._tray = pystray.Icon(
            name="KlavyeMacro",
            icon=icon_img,
            title="KlavyeMacro - Makro Yöneticisi",
            menu=self._build_menu()
        )
        self._thread = threading.Thread(target=self._tray.run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass

    def notify(self, title: str, message: str):
        """Bildirim gösterir."""
        if self._tray:
            try:
                self._tray.notify(message, title)
            except Exception:
                pass
