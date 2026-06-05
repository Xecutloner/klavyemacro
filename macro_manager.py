"""
macro_manager.py - Macro kayıt ve yükleme yöneticisi
"""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional

import sys

if getattr(sys, 'frozen', False):
    # PyInstaller bundle icindeyken (.exe)
    application_path = os.path.dirname(sys.executable)
else:
    # Normal Python script olarak calisirken
    application_path = os.path.dirname(os.path.abspath(__file__))

MACROS_FILE = os.path.join(application_path, "macros.json")


@dataclass
class Macro:
    name: str
    hotkey: str
    text: str
    target_apps: List[str] = field(default_factory=list)
    enabled: bool = True
    delay_before: float = 0.0
    delay_after: float = 0.0
    image_path: str = ""
    image_paths: List[str] = field(default_factory=list)
    raw_clipboard_data: str = ""   # Pano birebir kopyası (base64)
    send_mode: str = "caption"
    # send_mode değerler:
    #   "text_only" = sadece metin (clipboard+Ctrl+V)
    #   "caption"   = görsel + metin birlikte (clipboard+Ctrl+V)
    #   "separate"  = önce görsel, sonra metin (clipboard+Ctrl+V)
    #   "api"       = Telethon API ile gönder (hyperlink, premium emoji, görsel tam destekli)
    #   "raw"       = Telegram'dan kopyalanani 1:1 yapistir (en iyi yontem)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    # İstatistikler
    use_count: int = 0
    last_used: str = ""            # ISO format tarih/saat
    # Metin genişletme (text expansion)
    expansion_trigger: str = ""    # Ör: "!gm" yazinca bu makro aktive olur

    # ── Sprint 2 Alanları ──────────────────────────────────────────────────
    # Auto-repeat: ilk basışta başlar, ikinci basışta durur
    auto_repeat: bool = False
    repeat_interval: float = 30.0  # saniye (0 = devre dışı)

    # Zamanlanmış gönderim
    schedule_time: str = ""          # "HH:MM" formatı, boş = kapalı
    schedule_days: List[str] = field(default_factory=list)
    # Günler: "Mon","Tue","Wed","Thu","Fri","Sat","Sun"
    # Boş liste = her gün

    # Broadcast: birden fazla sohbete gönder (API modunda)
    broadcast_targets: List[str] = field(default_factory=list)
    # Sohbet adları listesi — boş = aktif pencereye gönder

    # Retry on failure
    retry_count: int = 0             # 0 = retry yok, max 5

    # Makro Zinciri (chain): bu makro bittikten sonra tetiklenecek makro id'leri
    chain_macro_ids: List[str] = field(default_factory=list)

    # ── Sprint 4 Alanları ──────────────────────────────────────────────────
    # Kategori & Etiket
    category: str = "Genel"            # Örn: "Satiş", "Destek", "Sabah"
    tags: List[str] = field(default_factory=list)  # Serbest etiketler
    favorite: bool = False             # Favorilere eklenmiş mi?

    def __post_init__(self):
        # Eski versiyon uyumlulugu
        if self.image_path and not self.image_paths:
            self.image_paths = [self.image_path]

    def matches_app(self, active_app_title: str) -> bool:
        """Macro'nun belirli bir uygulamaya özel olup olmadığını kontrol eder."""
        if not self.target_apps:
            return True  # Hedef uygulama yoksa her yerde çalışır
        app_lower = active_app_title.lower()
        return any(app.lower() in app_lower for app in self.target_apps)

    def increment_use(self):
        """Kullanım sayısını ve son kullanım zamanını günceller."""
        from datetime import datetime
        self.use_count = (self.use_count or 0) + 1
        self.last_used = datetime.now().strftime("%d.%m.%Y %H:%M")


# ---------------------------------------------------------------------------
# Değişken (variable) çözümleyici
# ---------------------------------------------------------------------------
def resolve_variables(text: str) -> str:
    """
    Makro metnindeki değişkenleri çözer.
    Desteklenen değişkenler:
      {{tarih}}                  -> 05.06.2026
      {{saat}}                   -> 14:36
      {{tarih_saat}}             -> 05.06.2026 14:36
      {{gun}}                    -> Perşembe
      {{rastgele:A|B|C}}         -> A, B veya C'den birini rastgele seçer
    """
    import re
    import random
    from datetime import datetime

    GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    now = datetime.now()

    # Sabit değişkenler
    replacements = {
        "{{tarih}}": now.strftime("%d.%m.%Y"),
        "{{saat}}": now.strftime("%H:%M"),
        "{{tarih_saat}}": now.strftime("%d.%m.%Y %H:%M"),
        "{{gun}}": GUNLER[now.weekday()],
        "{{yil}}": now.strftime("%Y"),
        "{{ay}}": now.strftime("%m"),
        "{{dakika}}": now.strftime("%M"),
    }

    for key, val in replacements.items():
        text = text.replace(key, val)

    # Dinamik: {{rastgele:A|B|C}}
    def pick_random(m):
        opts = [o.strip() for o in m.group(1).split("|")] 
        return random.choice(opts) if opts else ""

    text = re.sub(r"\{\{rastgele:([^}]+)\}\}", pick_random, text)

    return text


class MacroManager:
    def __init__(self):
        self.macros: List[Macro] = []
        self.settings: dict = {
            "paste_method": "clipboard",
            "restore_clipboard": True,
            "startup_with_windows": False,
            "minimize_to_tray": True
        }
        self.load()

    def load(self):
        """JSON dosyasından macro'ları yükler."""
        if not os.path.exists(MACROS_FILE):
            self.save()
            return
        try:
            with open(MACROS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Bilinmeyen alanları filtrele (eski/yeni versiyon uyumu)
            valid_fields = {f.name for f in Macro.__dataclass_fields__.values()}
            macros = []
            for m in data.get("macros", []):
                filtered = {k: v for k, v in m.items() if k in valid_fields}
                try:
                    macros.append(Macro(**filtered))
                except Exception as e:
                    print(f"[MacroManager] Macro yüklenemedi, atlanıyor: {e}")
            self.macros = macros
            self.settings.update(data.get("settings", {}))
        except Exception as e:
            print(f"[MacroManager] Yükleme hatası: {e}")
            self.macros = []

    def save(self):
        """Macro'ları JSON dosyasına kaydeder."""
        data = {
            "macros": [asdict(m) for m in self.macros],
            "settings": self.settings
        }
        try:
            with open(MACROS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[MacroManager] Kayıt hatası: {e}")

    def add_macro(self, macro: Macro):
        self.macros.append(macro)
        self.save()

    def update_macro(self, macro_id: str, updated: Macro):
        for i, m in enumerate(self.macros):
            if m.id == macro_id:
                updated.id = macro_id
                self.macros[i] = updated
                self.save()
                return True
        return False

    def delete_macro(self, macro_id: str):
        self.macros = [m for m in self.macros if m.id != macro_id]
        self.save()

    def move_macro(self, macro_id: str, direction: int) -> bool:
        """Macroyu yukari (-1) veya asagi (1) tasir."""
        idx = next((i for i, m in enumerate(self.macros) if m.id == macro_id), -1)
        if idx == -1: return False
        
        new_idx = idx + direction
        if 0 <= new_idx < len(self.macros):
            # Swap
            self.macros[idx], self.macros[new_idx] = self.macros[new_idx], self.macros[idx]
            self.save()
            return True
        return False

    def get_by_hotkey(self, hotkey: str) -> Optional[Macro]:
        for m in self.macros:
            if m.enabled and m.hotkey.lower() == hotkey.lower():
                return m
        return None

    def get_all_enabled(self) -> List[Macro]:
        return [m for m in self.macros if m.enabled]

    def export_macros(self, filepath: str) -> bool:
        """Macroları ve içerdikleri medyaları tek bir .kmd (zip) dosyasına kaydeder."""
        import zipfile
        import shutil
        import tempfile
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                media_dir = os.path.join(temp_dir, "media")
                os.makedirs(media_dir, exist_ok=True)
                
                export_data = {
                    "macros": [asdict(m) for m in self.macros],
                    "settings": self.settings
                }
                
                # Resimleri media klasörüne kopyala ve yolları güncelle
                for macro_dict in export_data["macros"]:
                    new_image_paths = []
                    for img_path in macro_dict.get("image_paths", []):
                        if img_path and os.path.exists(img_path):
                            filename = os.path.basename(img_path)
                            # Çakışmaları önlemek için benzersiz isim
                            unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
                            dest_path = os.path.join(media_dir, unique_filename)
                            shutil.copy2(img_path, dest_path)
                            new_image_paths.append(f"media/{unique_filename}")
                    macro_dict["image_paths"] = new_image_paths
                    macro_dict["image_path"] = "" # Eski alanı temizle
                
                # macros.json oluştur
                json_path = os.path.join(temp_dir, "macros.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                # Zip oluştur
                with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(json_path, "macros.json")
                    for root, _, files in os.walk(media_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = f"media/{file}"
                            zf.write(file_path, arcname)
                            
            return True
        except Exception as e:
            print(f"[Export Error] {e}")
            return False

    def import_macros(self, filepath: str) -> bool:
        """Bir .kmd dosyasını okuyup, medyaları uygulama dizinine kopyalar ve makroları yükler."""
        import zipfile
        import shutil
        import tempfile
        
        try:
            with zipfile.ZipFile(filepath, 'r') as zf:
                with tempfile.TemporaryDirectory() as temp_dir:
                    zf.extractall(temp_dir)
                    
                    json_path = os.path.join(temp_dir, "macros.json")
                    if not os.path.exists(json_path):
                        return False
                        
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        
                    # Medyaları asıl yere taşı
                    app_media_dir = os.path.join(application_path, "media")
                    os.makedirs(app_media_dir, exist_ok=True)
                    
                    # Makrolardaki media/ yollarını absolute path'lere çevir
                    for macro_dict in data.get("macros", []):
                        new_image_paths = []
                        for img_path in macro_dict.get("image_paths", []):
                            if img_path.startswith("media/"):
                                filename = os.path.basename(img_path)
                                source_path = os.path.join(temp_dir, "media", filename)
                                dest_path = os.path.join(app_media_dir, filename)
                                if os.path.exists(source_path):
                                    shutil.copy2(source_path, dest_path)
                                    new_image_paths.append(dest_path)
                            else:
                                if os.path.exists(img_path):
                                    new_image_paths.append(img_path)
                        macro_dict["image_paths"] = new_image_paths
                        macro_dict["image_path"] = ""  # Eski alanı temizle

                    # Bilinmeyen alanları filtrele
                    valid_fields = {f for f in Macro.__dataclass_fields__}
                    macros = []
                    for m in data.get("macros", []):
                        filtered = {k: v for k, v in m.items() if k in valid_fields}
                        try:
                            macros.append(Macro(**filtered))
                        except Exception as e:
                            print(f"[Import] Macro atlandı: {e}")
                    self.macros = macros
                    self.settings.update(data.get("settings", {}))
                    self.save()
            return True
        except Exception as e:
            print(f"[Import Error] {e}")
            return False

    def set_startup(self, enabled: bool):
        """Windows başlangıcında otomatik çalıştır."""
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "KlavyeMacro"

        # .exe olarak çalışıyorsa sys.executable'ı kullan, yoksa python script yolunu
        if getattr(sys, 'frozen', False):
            exe_path = f'"{sys.executable}"'
        else:
            # Geliştirme modunda - script yolunu kullan
            exe_path = f'"{sys.executable}" "{os.path.abspath(__file__).replace("macro_manager.py", "main.py")}"'

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            self.settings["startup_with_windows"] = enabled
            self.save()
        except Exception as e:
            print(f"[Startup] Hata: {e}")

    # ── Sprint 4: Profil Sistemi ──────────────────────────────────────────
    @property
    def _profiles_dir(self) -> str:
        d = os.path.join(application_path, "profiles")
        os.makedirs(d, exist_ok=True)
        return d

    def list_profiles(self) -> List[str]:
        """Kaydetli profil adlarini listeler."""
        return [
            os.path.splitext(f)[0]
            for f in os.listdir(self._profiles_dir)
            if f.endswith(".kmd")
        ]

    def save_as_profile(self, profile_name: str) -> bool:
        """Mevcut makro setini profil olarak kaydeder."""
        path = os.path.join(self._profiles_dir, f"{profile_name}.kmd")
        return self.export_macros(path)

    def load_profile(self, profile_name: str) -> bool:
        """Profili yükler (mevcut makroların yerini alır)."""
        path = os.path.join(self._profiles_dir, f"{profile_name}.kmd")
        if not os.path.exists(path):
            return False
        return self.import_macros(path)

    def delete_profile(self, profile_name: str) -> bool:
        path = os.path.join(self._profiles_dir, f"{profile_name}.kmd")
        try:
            os.remove(path)
            return True
        except Exception:
            return False

    # ── Sprint 4: Toplu İşlemler ─────────────────────────────────────────
    def enable_all(self):
        for m in self.macros:
            m.enabled = True
        self.save()

    def disable_all(self):
        for m in self.macros:
            m.enabled = False
        self.save()

    def get_categories(self) -> List[str]:
        seen = []
        for m in self.macros:
            if m.category not in seen:
                seen.append(m.category)
        return seen

    def enable_by_category(self, category: str):
        for m in self.macros:
            if m.category == category:
                m.enabled = True
        self.save()

    def disable_by_category(self, category: str):
        for m in self.macros:
            if m.category == category:
                m.enabled = False
        self.save()

    def delete_by_category(self, category: str):
        self.macros = [m for m in self.macros if m.category != category]
        self.save()

    def get_favorites(self) -> List[Macro]:
        return [m for m in self.macros if m.favorite]

