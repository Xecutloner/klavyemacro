from macro_manager import MacroManager, Macro
from hotkey_listener import HotkeyListener, get_active_window_info

# Macro manager testi
mgr = MacroManager()
print(f"[OK] MacroManager: {len(mgr.macros)} macro yuklendi")

# Hotkey listener olustur
listener = HotkeyListener(mgr)
print("[OK] HotkeyListener olusturuldu")

# Aktif pencere testi
title, proc = get_active_window_info()
print(f"[OK] Aktif pencere: '{title}' | Process: {proc}")

print("[OK] Tum moduller calisiyor!")
