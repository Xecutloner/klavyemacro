"""
main.py - KlavyeMacro Ana Giris Noktasi

AutoHotkey alternatifi, Telegram uyumlu klavye macro yöneticisi.
Clipboard tabanlı yapıştırma kullanır - link preview ve görsel silme sorunu yaşatmaz.
"""

import sys
import io
import threading
import ctypes

# Windows terminal UTF-8 sorunu
# Windows terminal UTF-8 sorunu
if sys.stdout is not None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr is not None:
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from macro_manager import MacroManager
from hotkey_listener import HotkeyListener
from gui import MacroGUI, HotkeyHelpPopup, UpdateCheckDialog
from tray import SystemTray
from webhook_server import WebhookServer
import keyboard_guard as _kg


def is_admin():
    """Yönetici yetkisi var mı kontrol eder."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def request_admin():
    """Yönetici olarak yeniden başlatır (global hotkey için gerekli olabilir)."""
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)


def main():
    # ─── Klavye Korumasını İLK ŞİMDİ Aktif Et ─────────────────────
    # atexit, SIGINT, SIGTERM, crash hook, konsol X butonu
    # tüm senaryolarda klavye temiz bırakılır
    _kg.register_guards()

    # ─── Bileşenleri Oluştur ─────────────────────────────
    manager = MacroManager()

    listener = HotkeyListener(manager)

    # GUI (ana pencere)
    gui = MacroGUI(manager, listener)

    # ─── Sprint 6: PIN Kilidi ────────────────────────────────
    from gui import PinLockDialog
    _pin = manager.settings.get("pin", "").strip()
    if _pin:
        _unlocked = [False]

        def _on_pin_success():
            _unlocked[0] = True

        def _on_pin_fail():
            import sys
            gui.root.after(0, gui.root.destroy)

        PinLockDialog(gui.root, _pin,
                      on_success=_on_pin_success,
                      on_fail=_on_pin_fail)
        gui.root.withdraw()  # Ana pencereyi PIN doğrulanana kadar gizle
        gui.root.wait_window()   # PinLockDialog kapanana kadar bekle
        if _unlocked[0]:
            gui.root.deiconify()
        else:
            import sys
            sys.exit(0)

    # Sistem tepsisi
    tray = SystemTray(
        on_show=lambda: gui.root.after(0, gui.show),
        on_quit=lambda: quit_app()
    )

    # ─── Bağlantılar ─────────────────────────────────────────
    # Macro tetiklenince GUI'yi güncelle
    def on_macro_triggered(name: str):
        gui.root.after(0, lambda: gui.notify_trigger(name))

    listener.on_macro_triggered = on_macro_triggered

    # Makro hatası → kullanıcıya popup göster
    def on_macro_error(title: str, message: str):
        import threading, ctypes
        def _show():
            ctypes.windll.user32.MessageBoxW(
                0,
                message,
                title,
                0x10 | 0x1000  # MB_ICONERROR | MB_SYSTEMMODAL
            )
        threading.Thread(target=_show, daemon=True).start()

    listener.on_error = on_macro_error

    # Pencere kapatılınca tepsiye küçülme
    gui.on_close_to_tray = lambda: None  # Tray zaten çalışıyor

    def quit_app():
        listener.stop()  # stop() içinde full_keyboard_reset çağrılıyor
        # Ek güvence: tüm hookları ve modifier'ları temizle
        try:
            _kg.full_keyboard_reset(restore_capslock=True)
        except Exception:
            pass
        tray.stop()
        try:
            gui.root.after(0, gui.root.destroy)
        except Exception:
            pass

    # ─── Başlat ───────────────────────────────────────────────
    tray.start()
    listener.start()

    # ─── Webhook Sunucusu ─────────────────────────────────────
    webhook = WebhookServer(manager, listener, port=7474)
    webhook.start()

    print("[KlavyeMacro] Başlatıldı. Sistem tepsisinde çalışıyor.")
    print(f"[KlavyeMacro] {len(manager.macros)} macro yüklendi.")
    for m in manager.macros:
        print(f"  - {m.hotkey:20s} -> {m.name}")
    print(f"[Webhook] http://127.0.0.1:7474 aktif")

    # ─── Quick-Send Overlay (Ctrl+Shift+Q) ─────────────────
    from gui import QuickSendOverlay
    import keyboard as _kb

    _overlay_ref = [None]  # mutable ref

    def _toggle_overlay():
        def _ui():
            if _overlay_ref[0] and _overlay_ref[0].winfo_exists():
                _overlay_ref[0].destroy()
                _overlay_ref[0] = None
            else:
                ov = QuickSendOverlay(gui.root, manager, listener)
                _overlay_ref[0] = ov
        gui.root.after(0, _ui)

    _kb.add_hotkey("ctrl+shift+q", _toggle_overlay, suppress=False)

    # ─── F1 Kısayol Özet Popup ────────────────────────────────
    def _show_help():
        gui.root.after(0, lambda: HotkeyHelpPopup(gui.root, manager))
    _kb.add_hotkey("f1", _show_help, suppress=False)

    # Tkinter main loop (ana thread'de çalışmalı)
    gui.run()

    # Çıkışta temizlik (normal kapanma)
    listener.stop()  # stop() içinde full_keyboard_reset çağrılıyor
    # Son güvence turu
    try:
        _kg.full_keyboard_reset(restore_capslock=True)
    except Exception:
        pass
    webhook.stop()
    tray.stop()


if __name__ == "__main__":
    main()
