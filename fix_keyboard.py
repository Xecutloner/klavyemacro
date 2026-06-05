"""
fix_keyboard.py - Takili kalan keyboard hook'larini temizler ve klavyeyi sifirlar.
"""
import ctypes
import time

# 1. keyboard kutuphanesi hook'larini temizle
try:
    import keyboard
    keyboard.unhook_all()
    print("[OK] keyboard kutuphanesi hook'lari temizlendi")
except Exception as e:
    print(f"[!] keyboard hook temizleme: {e}")

# 2. Modifier tuslarini birak (Shift, Ctrl, Alt)
try:
    import pyautogui
    for key in ['shift', 'ctrl', 'alt', 'win']:
        try:
            pyautogui.keyUp(key)
        except Exception:
            pass
    print("[OK] Modifier tuslar biraktirildi")
except Exception as e:
    print(f"[!] pyautogui: {e}")

# 3. CapsLock durumunu kontrol et ve duzelt
VK_CAPITAL = 0x14
user32 = ctypes.WinDLL('User32.dll')
caps_state = user32.GetKeyState(VK_CAPITAL) & 1

if caps_state:
    print(f"[!] CapsLock ACIK - kapatiliyor...")
    # CapsLock'u toggle et (kapat)
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
        ]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("ki", KEYBDINPUT), ("padding", ctypes.c_ubyte * 8)]

    def send_key(vk, flags=0):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ki.wVk = vk
        inp.ki.dwFlags = flags
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

    send_key(VK_CAPITAL)
    time.sleep(0.05)
    send_key(VK_CAPITAL, KEYEVENTF_KEYUP)
    time.sleep(0.05)

    new_state = user32.GetKeyState(VK_CAPITAL) & 1
    print(f"[OK] CapsLock yeni durum: {'ACIK' if new_state else 'KAPALI'}")
else:
    print("[OK] CapsLock zaten KAPALI - sorun baska bir seyde")

# 4. pynput varsa onu da temizle
try:
    from pynput import keyboard as pk
    print("[OK] pynput mevcut - eger listener varsa durdurmak icin programi kapatmak gerekiyor")
except ImportError:
    pass

print("\n[TAMAM] Klavye sifirlama tamamlandi!")
print("Hala sorun varsa bilgisayari yeniden baslatin.")
