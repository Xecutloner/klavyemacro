"""
hotkey_listener.py - Güvenilir makro kısayol dinleyici.
keyboard kütüphanesi kullanır (geniş tuş desteği).
Proaktif watchdog ile hook ölüm sorunu engellenir.
"""

import os
import struct
import time
import threading
from typing import Callable, Dict, Optional, Tuple

import keyboard
import psutil
import pyautogui
import win32clipboard
import win32con
import win32gui
import win32process

from macro_manager import MacroManager, Macro, resolve_variables

try:
    import telethon_sender as tg_api
    _TELETHON_OK = True
except ImportError:
    _TELETHON_OK = False


# ─── Pencere Yardımcıları ─────────────────────────────────────────────────────
def get_active_window_info() -> Tuple[str, str]:
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid).name()
        return title, proc
    except Exception:
        return "", ""


# ─── Clipboard Yardımcıları ──────────────────────────────────────────────────
def _clipboard_get() -> str:
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT) or ""
        return ""
    except Exception:
        return ""
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass


def _clipboard_set(text: str):
    for _ in range(10):
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            win32clipboard.CloseClipboard()
            return
        except Exception:
            time.sleep(0.05)
    print("[Clipboard] Yazma başarısız (10 deneme).")


def _clipboard_set_files(file_paths: list) -> bool:
    valid = [p for p in file_paths if os.path.exists(p)]
    if not valid:
        return False
    try:
        buf = b""
        for path in valid:
            buf += os.path.abspath(path).encode("utf-16le") + b"\0\0"
        buf += b"\0\0"
        dropfiles = struct.pack("IIII", 20, 0, 0, 1)
        for _ in range(10):
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_HDROP, dropfiles + buf)
                win32clipboard.CloseClipboard()
                return True
            except Exception:
                time.sleep(0.05)
        return False
    except Exception as e:
        print(f"[Clipboard] Dosya hatası: {e}")
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
        return False


def paste_text_safe(text: str, restore_clipboard: bool = True,
                    delay_before: float = 0, delay_after: float = 0):
    if delay_before > 0:
        time.sleep(delay_before)
    old = _clipboard_get() if restore_clipboard else ""
    try:
        _clipboard_set(text)
        time.sleep(0.08)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.05)
    finally:
        if restore_clipboard and old:
            threading.Thread(
                target=lambda: (time.sleep(0.4), _clipboard_set(old)),
                daemon=True
            ).start()
    if delay_after > 0:
        time.sleep(delay_after)


def _release_modifiers():
    for key in ['ctrl', 'alt', 'shift']:
        try:
            pyautogui.keyUp(key)
        except Exception:
            pass
    time.sleep(0.1)


def _bring_window_to_front(hwnd: int):
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.15)
    except Exception:
        pass


def _dismiss_link_preview():
    """Telegram Desktop'taki link ön izleme kartını kapatmaya çalışır."""
    try:
        time.sleep(0.35)
        hwnd = win32gui.GetForegroundWindow()
        if 'Telegram' not in win32gui.GetWindowText(hwnd):
            return
        rect = win32gui.GetWindowRect(hwnd)
        btn_x = rect[2] - 20
        btn_y = rect[3] - 55 - 32
        if rect[0] < btn_x < rect[2] and rect[1] < btn_y < rect[3]:
            pyautogui.click(btn_x, btn_y)
            time.sleep(0.1)
    except Exception:
        pass


# ─── Ana Dinleyici Sınıfı ────────────────────────────────────────────────────
class HotkeyListener:
    """
    Makro kısayol dinleyici.
    - keyboard kütüphanesi ile geniş tuş kombinasyon desteği
    - Per-makro bağımsız kilit (bir makro diğerini bloke etmez)
    - Proaktif watchdog: her 20 sn'de hook tamamen yenilenir
    """

    _WATCHDOG_INTERVAL = 20   # saniye

    def __init__(self, macro_manager: MacroManager,
                 on_macro_triggered: Optional[Callable] = None):
        self.macro_manager = macro_manager
        self.on_macro_triggered = on_macro_triggered

        self._running = False
        self._registered: Dict[str, str] = {}    # hotkey → macro_id
        self._macro_executing: Dict[str, bool] = {}
        self._lock = threading.Lock()
        self._watchdog_stop = threading.Event()
        self._watchdog_thread: Optional[threading.Thread] = None

        # Text expansion
        self._typed_buffer = ""          # Son 64 karakter
        self._expansion_hooks = []       # keyboard hooks listesi
        self._kb_hook = None             # Genel tuş hook'u

        # Auto-repeat: makro_id → stop Event
        self._repeat_events: Dict[str, threading.Event] = {}

        # Scheduler
        self._scheduler_stop = threading.Event()
        self._scheduler_thread: Optional[threading.Thread] = None

    # ── Yaşam Döngüsü ─────────────────────────────────────────────────────────────
    def start(self):
        self._running = True
        self._do_register_all()
        self._register_expansion()
        self._start_scheduler()
        self._start_watchdog()
        print("[HotkeyListener] Başlatıldı.")

    def stop(self):
        self._running = False
        self._watchdog_stop.set()
        self._scheduler_stop.set()
        # Tüm auto-repeat döngülerini durdur
        for ev in self._repeat_events.values():
            ev.set()
        self._repeat_events.clear()
        self._do_unregister_all()
        self._unregister_expansion()
        print("[HotkeyListener] Durduruldu.")

    def refresh(self):
        """Makro listesi değişince hotkey'leri yeniler."""
        with self._lock:
            self._do_unregister_all()
            self._do_register_all()
        self._unregister_expansion()
        self._register_expansion()

    def force_restart(self):
        """Hook'u tamamen sıfırlayıp yeniden başlatır."""
        print("[HotkeyListener] Yeniden başlatılıyor...")
        with self._lock:
            try:
                keyboard.unhook_all()
            except Exception:
                pass
            self._registered.clear()
            # Takılı kalan execution bayraklarını temizle
            for k in self._macro_executing:
                self._macro_executing[k] = False
            time.sleep(0.05)
            if self._running:
                self._do_register_all()
        self._unregister_expansion()
        self._register_expansion()
        print("[HotkeyListener] Yeniden başlatıldı.")

    # ── Text Expansion ──────────────────────────────────────────────────────────
    def _register_expansion(self):
        """expansion_trigger’ı olan makrolar için tuş izleyicisi başlatır."""
        triggers = [
            m for m in self.macro_manager.get_all_enabled()
            if m.expansion_trigger.strip()
        ]
        if not triggers:
            return

        self._typed_buffer = ""

        def _on_key(event):
            if not self._running:
                return
            if event.event_type != "down":
                return

            ch = event.name
            if ch == "backspace":
                self._typed_buffer = self._typed_buffer[:-1]
                return
            if ch == "space":
                ch = " "
            elif len(ch) > 1:  # shift, ctrl, enter vb. — sıfırla
                self._typed_buffer = ""
                return

            self._typed_buffer += ch
            self._typed_buffer = self._typed_buffer[-64:]

            for macro in triggers:
                trig = macro.expansion_trigger.strip()
                if self._typed_buffer.endswith(trig):
                    self._typed_buffer = ""
                    threading.Thread(
                        target=self._expand_text,
                        args=(macro, len(trig)),
                        daemon=True
                    ).start()
                    break

        self._kb_hook = keyboard.hook(_on_key, suppress=False)
        print(f"[TextExpansion] {len(triggers)} kısaltma aktif.")

    def _unregister_expansion(self):
        if self._kb_hook is not None:
            try:
                keyboard.unhook(self._kb_hook)
            except Exception:
                pass
            self._kb_hook = None

    def _expand_text(self, macro: Macro, trigger_len: int):
        """Kısaltmayı siler ve makro metnini yazar."""
        try:
            time.sleep(0.05)
            # Kısaltmayı geri sil
            for _ in range(trigger_len):
                pyautogui.press("backspace")
                time.sleep(0.015)
            time.sleep(0.05)
            restore = self.macro_manager.settings.get("restore_clipboard", True)
            resolved = resolve_variables(macro.text)
            paste_text_safe(resolved, restore_clipboard=restore)
            macro.increment_use()
            if self.on_macro_triggered:
                self.on_macro_triggered(macro.name)
            print(f"[TextExpansion] '{macro.expansion_trigger}' → '{macro.name}'")
        except Exception as e:
            print(f"[TextExpansion] Hata: {e}")

    # ── Watchdog ────────────────────────────────────────────────────────────
    def _start_watchdog(self):
        """Her N saniyede hook'u proaktif olarak yeniler."""
        self._watchdog_stop.clear()

        def _loop():
            while not self._watchdog_stop.wait(self._WATCHDOG_INTERVAL):
                if not self._running:
                    break
                try:
                    self.force_restart()
                except Exception as e:
                    print(f"[Watchdog] Hata: {e}")

        self._watchdog_thread = threading.Thread(
            target=_loop, daemon=True, name="HotkeyWatchdog"
        )
        self._watchdog_thread.start()

    # ── Kayıt / İptal ──────────────────────────────────────────────────────
    def _do_register_all(self):
        """Tüm aktif makroları kaydeder. Lock dışarıdan alınabilir."""
        for macro in self.macro_manager.get_all_enabled():
            self._do_register_one(macro)

    def _do_register_one(self, macro: Macro):
        hotkey = macro.hotkey.lower().strip()
        if not hotkey or hotkey in self._registered:
            return
        try:
            keyboard.add_hotkey(
                hotkey,
                self._make_callback(macro),
                suppress=True,
                trigger_on_release=False
            )
            self._registered[hotkey] = macro.id
            self._macro_executing.setdefault(macro.id, False)
            print(f"[HotkeyListener] Kayıt: {hotkey} → {macro.name}")
        except Exception as e:
            print(f"[HotkeyListener] Kayıt başarısız ({hotkey}): {e}")

    def _do_unregister_all(self):
        """Tüm hook'ları temizler."""
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self._registered.clear()

    # ── Callback Fabrikası ─────────────────────────────────────────────────
    def _make_callback(self, macro: Macro):
        def callback():
            if not self._running:
                return
            macro_id = macro.id
            title, proc = get_active_window_info()
            if not (macro.matches_app(title) or macro.matches_app(proc)):
                return

            # ── Auto-repeat toggle ─────────────────────────────
            if macro.auto_repeat and macro.repeat_interval > 0:
                if macro_id in self._repeat_events:
                    # İkinci basış → durdur
                    self._repeat_events[macro_id].set()
                    del self._repeat_events[macro_id]
                    print(f"[AutoRepeat] Durduruldu: {macro.name}")
                    if self.on_macro_triggered:
                        self.on_macro_triggered(f"⏹ {macro.name} (durduruldu)")
                    return
                else:
                    # İlk basış → döngü başlat
                    stop_ev = threading.Event()
                    self._repeat_events[macro_id] = stop_ev
                    threading.Thread(
                        target=self._repeat_loop,
                        args=(macro, stop_ev),
                        daemon=True
                    ).start()
                    if self.on_macro_triggered:
                        self.on_macro_triggered(f"🔁 {macro.name} (tekrar)")
                    return

            # ── Normal tek çalıştırma ──────────────────────────
            if self._macro_executing.get(macro_id, False):
                return
            print(f"[HotkeyListener] Tetiklendi: {macro.name}")
            macro.increment_use()
            threading.Thread(target=self._play_beep, daemon=True).start()
            self._macro_executing[macro_id] = True
            threading.Thread(
                target=self._execute_macro,
                args=(macro,),
                daemon=True
            ).start()
            if self.on_macro_triggered:
                self.on_macro_triggered(macro.name)
        return callback

    def _repeat_loop(self, macro: Macro, stop_ev: threading.Event):
        """Auto-repeat döngüsü — stop_ev set edilene kadar çalışır."""
        while not stop_ev.is_set():
            if not self._running:
                break
            try:
                self._execute_macro(macro)
            except Exception as e:
                print(f"[AutoRepeat] Hata: {e}")
            stop_ev.wait(timeout=macro.repeat_interval)

    @staticmethod
    def _play_beep():
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass

    # ── Scheduler ─────────────────────────────────────────────────────────
    def _start_scheduler(self):
        """Zamanlanmış makroları dakikada bir kontrol eder."""
        self._scheduler_stop.clear()

        def _loop():
            from datetime import datetime
            DAY_MAP = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3,
                       "Fri": 4, "Sat": 5, "Sun": 6}
            last_fired: Dict[str, str] = {}  # macro_id → "HH:MM DD"

            while not self._scheduler_stop.wait(30):  # 30sn'de bir kontrol
                if not self._running:
                    break
                now = datetime.now()
                now_hhmm = now.strftime("%H:%M")
                now_day = now.weekday()
                now_key = f"{now_hhmm} {now.strftime('%d')}"

                for macro in self.macro_manager.get_all_enabled():
                    if not macro.schedule_time:
                        continue
                    if macro.schedule_time != now_hhmm:
                        continue
                    # Gün kontrolü
                    if macro.schedule_days:
                        allowed = [DAY_MAP.get(d, -1) for d in macro.schedule_days]
                        if now_day not in allowed:
                            continue
                    # Bugün bu dakikada zaten tetiklendi mi?
                    if last_fired.get(macro.id) == now_key:
                        continue
                    last_fired[macro.id] = now_key
                    print(f"[Scheduler] Zamanlanmış tetikleme: {macro.name}")
                    threading.Thread(target=self._play_beep, daemon=True).start()
                    macro.increment_use()
                    threading.Thread(
                        target=self._execute_macro,
                        args=(macro,),
                        daemon=True
                    ).start()
                    if self.on_macro_triggered:
                        self.on_macro_triggered(f"⏰ {macro.name}")

        self._scheduler_thread = threading.Thread(
            target=_loop, daemon=True, name="MacroScheduler"
        )
        self._scheduler_thread.start()

    # ── Makro Çalıştırma ──────────────────────────────────────────────────
    def _execute_macro(self, macro: Macro):
        macro_id = macro.id
        max_retries = max(0, min(int(macro.retry_count), 5))

        for attempt in range(max_retries + 1):
            try:
                self._do_execute(macro)
                # Başarılı → Makro Zinciri (Chain)
                if macro.chain_macro_ids:
                    for cid in macro.chain_macro_ids:
                        chained = next(
                            (m for m in self.macro_manager.macros
                             if m.id == cid and m.enabled), None
                        )
                        if chained:
                            time.sleep(0.3)
                            print(f"[Chain] Zincir: {macro.name} → {chained.name}")
                            self._do_execute(chained)
                            if self.on_macro_triggered:
                                self.on_macro_triggered(f"⛓ {chained.name}")
                break  # Başarılı, retry döngüsünden çık

            except Exception as e:
                print(f"[HotkeyListener] Makro hatası ({macro.name}) "
                      f"[deneme {attempt+1}/{max_retries+1}]: {e}")
                if attempt < max_retries:
                    time.sleep(1.5 * (attempt + 1))  # Artan bekleme
                else:
                    print(f"[HotkeyListener] {macro.name} tüm denemeler başarısız.")
        self._macro_executing[macro_id] = False

    def _do_execute(self, macro: Macro):
        """Makroyu tek seferlik çalıştırır. Hata raise eder."""
        _release_modifiers()

        restore = self.macro_manager.settings.get("restore_clipboard", True)
        has_images = bool(macro.image_paths)
        mode = macro.send_mode

        resolved_text = resolve_variables(macro.text)

        if mode not in ("api", "raw") and not has_images:
            mode = "text_only"

        if macro.delay_before > 0:
            time.sleep(macro.delay_before)

        # ── RAW modu ──────────────────────────────────────────────────────
        if mode == "raw":
            if not macro.raw_clipboard_data:
                raise RuntimeError("RAW verisi yok!")
            import clipboard_utils
            old_cb = clipboard_utils.dump_raw_clipboard()
            hwnd = win32gui.GetForegroundWindow()
            _bring_window_to_front(hwnd)

            if has_images:
                ok_img = _clipboard_set_files(macro.image_paths)
                if ok_img:
                    time.sleep(0.15)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.6)

            ok_raw = clipboard_utils.restore_raw_clipboard(macro.raw_clipboard_data)
            if ok_raw:
                time.sleep(0.15)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.5)
                _dismiss_link_preview()
                pyautogui.press('enter')
            else:
                raise RuntimeError("RAW pano yüklenemedi!")

            if restore and old_cb:
                threading.Thread(
                    target=lambda: (time.sleep(0.6),
                                    clipboard_utils.restore_raw_clipboard(old_cb)),
                    daemon=True
                ).start()

        # ── API modu ──────────────────────────────────────────────────────
        elif mode == "api":
            if not _TELETHON_OK:
                raise RuntimeError("Telethon yüklü değil!")

            # Broadcast: birden fazla sohbete gönder
            targets = macro.broadcast_targets if macro.broadcast_targets else [None]
            for target in targets:
                try:
                    if target:
                        # Belirli sohbete gönder
                        tg_api.send_to(
                            target_name=target,
                            text=resolved_text,
                            image_path=macro.image_paths[0] if has_images else ""
                        )
                    else:
                        tg_api.send(
                            text=resolved_text,
                            image_path=macro.image_paths[0] if has_images else ""
                        )
                    if len(targets) > 1:
                        time.sleep(1.0)  # Sohbetler arası bekleme
                except Exception as e:
                    print(f"[Broadcast] '{target}' hedefine gönderilemedi: {e}")
                    raise

        # ── Sadece metin ──────────────────────────────────────────────────
        elif mode == "text_only":
            has_link = any(s in resolved_text
                           for s in ('http://', 'https://', 'www.'))
            paste_text_safe(resolved_text, restore_clipboard=restore)
            if has_link:
                _dismiss_link_preview()

        # ── Görsel + Caption birlikte ──────────────────────────────────────
        elif mode == "caption":
            hwnd = win32gui.GetForegroundWindow()
            ok = _clipboard_set_files(macro.image_paths)
            if not ok:
                paste_text_safe(resolved_text, restore_clipboard=restore)
                return
            _bring_window_to_front(hwnd)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1.0)
            old_cb = _clipboard_get()
            _clipboard_set(resolved_text)
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)
            _dismiss_link_preview()
            pyautogui.press('enter')
            if restore and old_cb:
                threading.Thread(
                    target=lambda: (time.sleep(0.5), _clipboard_set(old_cb)),
                    daemon=True
                ).start()

        # ── Önce görsel, sonra metin ───────────────────────────────────────
        elif mode == "separate":
            hwnd = win32gui.GetForegroundWindow()
            ok = _clipboard_set_files(macro.image_paths)
            if ok:
                _bring_window_to_front(hwnd)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.8)
                pyautogui.press('enter')
                time.sleep(0.5)
            _bring_window_to_front(hwnd)
            paste_text_safe(macro.text, restore_clipboard=restore)

        if macro.delay_after > 0:
            time.sleep(macro.delay_after)

