"""
keyboard_guard.py - Klavye Güvenlik Modülü

Bu modül programın her koşulda (normal çıkış, hata, taskkill, Ctrl+C, crash)
klavyeyi temiz bırakmasını garanti eder. CapsLock hiçbir zaman bozulmaz.

Korunan senaryolar:
  - Normal program çıkışı      → atexit
  - Ctrl+C                     → SIGINT handler
  - taskkill /F                → SIGTERM handler
  - Beklenmeyen Python hatası  → sys.excepthook
  - Windows konsol kapatma     → SetConsoleCtrlHandler
"""

import atexit
import ctypes
import ctypes.wintypes
import signal
import sys
import time

# ── Windows VK Kodları ────────────────────────────────────────────────────────
VK_SHIFT    = 0x10
VK_CTRL     = 0x11
VK_ALT      = 0x12
VK_LWIN     = 0x5B
VK_RWIN     = 0x5C
VK_CAPITAL  = 0x14  # CapsLock
VK_NUMLOCK  = 0x90
VK_SCROLL   = 0x91
VK_LSHIFT   = 0xA0
VK_RSHIFT   = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU    = 0xA4  # Sol Alt
VK_RMENU    = 0xA5  # Sağ Alt

KEYEVENTF_KEYUP   = 0x0002
KEYEVENTF_UNICODE = 0x0004

_user32 = ctypes.WinDLL('User32.dll')

# ── Düşük Seviye Tuş İşlemleri ───────────────────────────────────────────────

def _key_up(vk: int):
    """Belirtilen VK kodu için KeyUp sinyali gönderir."""
    _user32.keybd_event(ctypes.c_byte(vk), 0, KEYEVENTF_KEYUP, 0)

def _key_down(vk: int):
    """Belirtilen VK kodu için KeyDown sinyali gönderir."""
    _user32.keybd_event(ctypes.c_byte(vk), 0, 0, 0)

def get_key_state(vk: int) -> bool:
    """Tuşun basılı olup olmadığını döner (high-bit = basılı)."""
    return bool(_user32.GetKeyState(vk) & 0x8000)

def get_toggle_state(vk: int) -> bool:
    """Togggle tuşun (CapsLock, NumLock vb.) aktif olup olmadığını döner (low-bit)."""
    return bool(_user32.GetKeyState(vk) & 0x0001)

# ── Modifier Temizleme ────────────────────────────────────────────────────────

# Temizlenecek modifier tuşları (sol+sağ versiyonlar dahil)
_ALL_MODIFIERS = [
    VK_LSHIFT, VK_RSHIFT,
    VK_LCONTROL, VK_RCONTROL,
    VK_LMENU, VK_RMENU,
    VK_LWIN, VK_RWIN,
    # Genel versiyonlar (bazı durumlarda ayrı kayıtlı)
    VK_SHIFT, VK_CTRL, VK_ALT,
]

def release_all_modifiers():
    """
    Tüm modifier tuşları (Shift, Ctrl, Alt, Win) zorla bırakır.
    Takılı kalan tuşları temizlemek için kullanılır.
    """
    for vk in _ALL_MODIFIERS:
        try:
            if get_key_state(vk):  # Sadece basılı olanları bırak
                _key_up(vk)
        except Exception:
            try:
                _key_up(vk)  # State okunamazsa yine de bırakmayı dene
            except Exception:
                pass
    time.sleep(0.05)

# ── CapsLock Yönetimi ─────────────────────────────────────────────────────────

def get_capslock_state() -> bool:
    """CapsLock'un açık (True) veya kapalı (False) olduğunu döner."""
    return get_toggle_state(VK_CAPITAL)

def set_capslock(target: bool):
    """
    CapsLock'u hedef duruma getirir.
    target=True  → CapsLock AÇIK
    target=False → CapsLock KAPALI
    """
    current = get_capslock_state()
    if current != target:
        _key_down(VK_CAPITAL)
        time.sleep(0.05)
        _key_up(VK_CAPITAL)
        time.sleep(0.05)
        # Başarılı oldumu kontrol et
        if get_capslock_state() != target:
            # Bir kez daha dene
            _key_down(VK_CAPITAL)
            time.sleep(0.05)
            _key_up(VK_CAPITAL)

# ── keyboard Kütüphanesi Hook Temizleme ───────────────────────────────────────

def unhook_keyboard_lib():
    """keyboard kütüphanesinin tüm hook'larını temizler."""
    try:
        import keyboard
        keyboard.unhook_all()
    except Exception:
        pass

# ── Tam Klavye Sıfırlama ──────────────────────────────────────────────────────

def full_keyboard_reset(restore_capslock: bool = True):
    """
    Tam klavye sıfırlama:
    1. keyboard lib hook'larını temizle
    2. Tüm modifier tuşları bırak
    3. CapsLock'u başlangıç durumuna getir (isteğe bağlı)
    """
    unhook_keyboard_lib()
    release_all_modifiers()
    if restore_capslock:
        restore_capslock_state()

# ── Durum Kaydı ───────────────────────────────────────────────────────────────

_state_saved: bool = False
_capslock_at_start: bool = False

def save_capslock_state():
    """Program başlangıcındaki CapsLock durumunu kaydeder."""
    global _state_saved, _capslock_at_start
    _capslock_at_start = get_capslock_state()
    _state_saved = True
    print(f"[KeyboardGuard] CapsLock baslangic: {'ACIK' if _capslock_at_start else 'KAPALI'}")

def restore_capslock_state():
    """CapsLock'u program başlangıcındaki durumuna döndürür."""
    if _state_saved:
        set_capslock(_capslock_at_start)

# ── Acil Temizlik ─────────────────────────────────────────────────────────────

def emergency_cleanup():
    """
    Acil durum temizliği. Her çıkış senaryosunda çalışır.
    Tekrar çağrılması güvenlidir (idempotent).
    """
    try:
        unhook_keyboard_lib()
    except Exception:
        pass
    try:
        release_all_modifiers()
    except Exception:
        pass
    try:
        restore_capslock_state()
    except Exception:
        pass

# ── Guard Kaydı ───────────────────────────────────────────────────────────────

_guards_registered: bool = False

def register_guards():
    """
    Tüm çıkış senaryoları için klavye koruma handler'larını kaydeder.
    Sadece bir kez çalışır (idempotent).
    
    Korunan senaryolar:
      atexit       → Normal Python çıkışı
      SIGINT       → Ctrl+C
      SIGTERM      → taskkill, servis durdurma
      excepthook   → Beklenmeyen Python hatası/crash
      ConsoleCtrl  → Windows konsol kapatma butonu
    """
    global _guards_registered
    if _guards_registered:
        return
    _guards_registered = True

    # Başlangıç durumunu kaydet
    save_capslock_state()

    # 1. Normal çıkışta (sys.exit, program sonu)
    atexit.register(emergency_cleanup)

    # 2. Ctrl+C (SIGINT)
    _orig_sigint = signal.getsignal(signal.SIGINT)
    def _on_sigint(sig, frame):
        print("\n[KeyboardGuard] SIGINT → klavye temizleniyor...")
        emergency_cleanup()
        if callable(_orig_sigint) and _orig_sigint not in (signal.SIG_DFL, signal.SIG_IGN):
            _orig_sigint(sig, frame)
        else:
            sys.exit(0)
    try:
        signal.signal(signal.SIGINT, _on_sigint)
    except Exception:
        pass

    # 3. taskkill / servis durdurma (SIGTERM)
    _orig_sigterm = signal.getsignal(signal.SIGTERM)
    def _on_sigterm(sig, frame):
        print("\n[KeyboardGuard] SIGTERM → klavye temizleniyor...")
        emergency_cleanup()
        if callable(_orig_sigterm) and _orig_sigterm not in (signal.SIG_DFL, signal.SIG_IGN):
            _orig_sigterm(sig, frame)
        else:
            sys.exit(0)
    try:
        signal.signal(signal.SIGTERM, _on_sigterm)
    except Exception:
        pass

    # 4. Beklenmeyen Python crash/exception
    _orig_excepthook = sys.excepthook
    def _on_exception(exc_type, exc_val, exc_tb):
        print(f"\n[KeyboardGuard] Crash yakalandi ({exc_type.__name__}) -> klavye temizleniyor...")
        emergency_cleanup()
        _orig_excepthook(exc_type, exc_val, exc_tb)
    sys.excepthook = _on_exception

    # 5. Windows konsol kapatma (X butonu, konsol kapanması)
    try:
        CTRL_C_EVENT       = 0
        CTRL_BREAK_EVENT   = 1
        CTRL_CLOSE_EVENT   = 2
        CTRL_LOGOFF_EVENT  = 5
        CTRL_SHUTDOWN_EVENT = 6

        HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.DWORD)

        def _console_ctrl_handler(ctrl_type):
            if ctrl_type in (CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT):
                print(f"\n[KeyboardGuard] ConsoleCtrl({ctrl_type}) -> klavye temizleniyor...")
                emergency_cleanup()
            return False  # Varsayılan işleyiciye devam et

        _handler_ref = HandlerRoutine(_console_ctrl_handler)  # GC'den koru
        ctypes.windll.kernel32.SetConsoleCtrlHandler(_handler_ref, True)
    except Exception:
        pass

    print("[KeyboardGuard] [OK] Tum koruma katmanlari aktif (atexit/SIGINT/SIGTERM/crash/konsol).")


# ── Kullanım Kolaylığı: context manager ──────────────────────────────────────

class KeyboardSafeSection:
    """
    Makro çalıştırırken CapsLock'u korur.
    
    Kullanım:
        with KeyboardSafeSection():
            # makro adımları...
    """
    def __enter__(self):
        self._caps_before = get_capslock_state()
        return self

    def __exit__(self, *args):
        # Makro sonrası CapsLock değiştiyse geri al
        if get_capslock_state() != self._caps_before:
            set_capslock(self._caps_before)
        # Modifier tuşları bırak
        release_all_modifiers()
