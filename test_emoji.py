# -*- coding: utf-8 -*-
"""
Emoji ve Telegram Premium emoji clipboard testi.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from hotkey_listener import _clipboard_set, _clipboard_get

# Test metni - ekran goruntusu gibi emoji iceren mesaj
test_text = """🔴 GAMDOM YENİ ÜYE KODUNU ALMANIZ İÇİN YAPMANIZ GEREKENLER
⚡ GAMDOM'A BİZİM LİNKİMİZDEN ÜYE OLUN
🌿 1- GAMDOM HESABINIZIN PROFİL ALANINDAN KİŞİSEL BİLGİLERİNİZİ KAYDEDİN
🌿 2- GAMDOM DESTEK EKİPLERİNE BAGLANIN
⚠️ KİMLİK DOGRULAMANIZ BİTMEDEN KODU ALAMAZSINIZ !!
⚡ KOD - CENK20BEDAVA (-10 GÜN 2$ KAZANACAKSINIZ)
🚀 TEST - Telegram Premium emoji desteği"""

print("Test metni clipboard'a yaziliyor...")
_clipboard_set(test_text)

print("Clipboard'dan okunuyor...")
result = _clipboard_get()

# Kontrol
if result == test_text:
    print("[OK] Emoji clipboard testi BASARILI!")
    print(f"[OK] Karakter sayisi: {len(result)}")
else:
    print("[HATA] Eslesme yok!")
    print(f"Beklenen: {len(test_text)} karakter")
    print(f"Alinan: {len(result)} karakter")
    # Farkliliklari goster
    for i, (a, b) in enumerate(zip(test_text, result)):
        if a != b:
            print(f"  Fark pozisyon {i}: '{a}' (U+{ord(a):04X}) != '{b}' (U+{ord(b):04X})")
