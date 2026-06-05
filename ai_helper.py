"""
ai_helper.py - Gemini API ile metin iyileştirme + Güncelleme Yöneticisi

KlavyeMacro'nun AI metin yeniden yazma ve iyileştirme özelliği.
Gemini API key ayarlardan girilir, internete bağlantı gerektirir.

Güncelleme mekanizması:
  - GitHub releases API ile yeni sürüm kontrolü
  - Yeni EXE'yi indirip geçici klasöre kaydeder
  - Updater bat script oluşturur: uygulama kapanınca çalışır,
    yeni EXE'yi yerine koyar ve yeniden başlatır.
"""

import json
import os
import sys
import tempfile
import urllib.request
import urllib.error

# Frozen (PyInstaller EXE) modda sys.executable'in klasorunu kullan,
# boylece ai_config.json guncelleme sonrasi kaybolmaz.
if getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_CONFIG_FILE = os.path.join(_BASE_DIR, "ai_config.json")

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

# ─── GitHub repo ayarı ───────────────────────────────────────────────────────
# Kendi GitHub hesabına göre değiştir (kullanıcı/repo)
GITHUB_REPO = "Xecutloner/klavyemacro"
# EXE asset adı (GitHub Release'deki dosya adı)
ASSET_NAME  = "KlavyeMacro.exe"


# ─── API Key ─────────────────────────────────────────────────────────────────

def load_api_key() -> str:
    """Kayıtlı API anahtarını döndürür."""
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("gemini_api_key", "")
    except Exception:
        return ""


def save_api_key(key: str):
    """API anahtarını kaydeder."""
    data = {}
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        pass
    data["gemini_api_key"] = key
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── AI Metin İyileştirici ───────────────────────────────────────────────────

def improve_text(text: str, instruction: str = "Bu metni daha profesyonel ve akıcı hale getir.",
                 api_key: str = "") -> str:
    """
    Verilen metni Gemini API ile iyileştirir.
    Hata durumunda RuntimeError fırlatır.

    instruction örnekleri:
      - "Bu metni daha profesyonel yap"
      - "Daha samimi ve sıcak bir dil kullan"
      - "Kısalt, öz ve net hale getir"
      - "Türkçe yazım kurallarına göre düzelt"
    """
    key = api_key or load_api_key()
    if not key:
        raise RuntimeError("Gemini API anahtarı ayarlanmamış.\nAyarlar → AI Ayarları bölümünden girin.")

    prompt = (
        f"Görev: {instruction}\n\n"
        f"Metin:\n{text}\n\n"
        "Sadece iyileştirilmiş metni döndür, açıklama ekleme."
    )

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
    }).encode("utf-8")

    url = f"{GEMINI_ENDPOINT}?key={key}"
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API hatası ({e.code}): {body[:300]}")
    except Exception as e:
        raise RuntimeError(f"AI isteği başarısız: {e}")


# ─── Güncelleme Kontrolü ─────────────────────────────────────────────────────

def check_update(current_version: str = "1.0.0") -> dict:
    """
    GitHub releases API'den son sürümü kontrol eder.

    Returns:
        {
            "latest": "1.2.0",
            "current": "1.0.0",
            "update_available": True,
            "url": "https://github.com/.../releases/tag/v1.2.0",
            "download_url": "https://github.com/.../releases/download/v1.2.0/KlavyeMacro.exe",
            "release_notes": "...",
            "asset_size": 84000000,
        }
    """
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "KlavyeMacro-Updater/1.0", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        latest = data.get("tag_name", "").lstrip("v")
        html_url = data.get("html_url", "")
        release_notes = data.get("body", "")

        # EXE asset'ini bul
        download_url = ""
        asset_size = 0
        for asset in data.get("assets", []):
            if asset.get("name", "").lower() == ASSET_NAME.lower():
                download_url = asset.get("browser_download_url", "")
                asset_size = asset.get("size", 0)
                break

        update_available = _version_gt(latest, current_version)
        return {
            "latest": latest,
            "current": current_version,
            "update_available": update_available,
            "url": html_url,
            "download_url": download_url,
            "release_notes": release_notes,
            "asset_size": asset_size,
        }
    except Exception as e:
        return {
            "latest": "?",
            "current": current_version,
            "update_available": False,
            "error": str(e),
            "download_url": "",
        }


def _version_gt(a: str, b: str) -> bool:
    """a > b mi? (semver karşılaştırma)"""
    def parts(v):
        try:
            return tuple(int(x) for x in v.split(".")[:3])
        except Exception:
            return (0, 0, 0)
    return parts(a) > parts(b)


# ─── Güncelleme İndirici ─────────────────────────────────────────────────────

def download_update(download_url: str,
                    progress_cb=None,
                    timeout: float = 120) -> str:
    """
    Yeni EXE'yi geçici bir dosyaya indirir.

    Args:
        download_url: GitHub asset download URL'si
        progress_cb: İlerleme callback → (downloaded_bytes, total_bytes)
        timeout: İndirme zaman aşımı (saniye)

    Returns:
        İndirilen geçici dosya yolu (str)

    Raises:
        RuntimeError: İndirme başarısız olursa
    """
    if not download_url:
        raise RuntimeError("İndirilecek URL yok. GitHub'da bu sürüm için EXE asset'i eksik.")

    try:
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "KlavyeMacro-Updater/1.0"}
        )

        # Geçici dosya oluştur
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".exe", prefix="KlavyeMacro_update_")
        os.close(tmp_fd)

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 65536  # 64 KB chunks

            with open(tmp_path, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb:
                        progress_cb(downloaded, total)

        return tmp_path

    except Exception as e:
        raise RuntimeError(f"İndirme başarısız: {e}")


# ─── Self-Updater Script ──────────────────────────────────────────────────────

def get_current_exe() -> str:
    """
    Çalışan uygulamanın EXE yolunu döndürür.
    - PyInstaller EXE'si ise: sys.executable
    - Python scripti ise: yolu bulamaz, boş döner
    """
    if getattr(sys, "frozen", False):
        return sys.executable  # PyInstaller EXE
    return ""  # Kaynak kodu modunda


def create_updater_script(new_exe_path: str, current_exe_path: str = None) -> str:
    """
    Uygulama kapanınca yeni EXE'yi yerine koyan bir .bat script oluşturur.

    Çalışma mantığı:
      1. Uygulama bu bat'ı çalıştırıp kapanır
      2. Bat 3 saniye bekler (process'in tamamen kapanması için)
      3. Yeni EXE'yi eski EXE'nin yerine kopyalar
      4. Yeni EXE'yi başlatır
      5. Bat kendini siler

    Args:
        new_exe_path: İndirilen yeni EXE'nin geçici yolu
        current_exe_path: Mevcut EXE yolu (None = otomatik tespit)

    Returns:
        Oluşturulan bat dosyasının yolu

    Raises:
        RuntimeError: EXE yolu bulunamazsa
    """
    if current_exe_path is None:
        current_exe_path = get_current_exe()

    if not current_exe_path:
        raise RuntimeError(
            "Otomatik güncelleme sadece EXE modunda çalışır.\n"
            "Python scripti olarak çalışıyorsun — manuel güncelleme yap."
        )

    # Bat dosyasını EXE'nin yanına yaz
    bat_dir = os.path.dirname(current_exe_path)
    bat_path = os.path.join(bat_dir, "_klavye_updater.bat")

    # Windows path'lerinde çift tırnak kullan
    bat_content = f"""@echo off
echo KlavyeMacro Guncelleyici baslatildi...
echo Uygulama kapanmayi bekliyor...
timeout /t 3 /nobreak >nul

:retry
tasklist /FI "IMAGENAME eq KlavyeMacro.exe" 2>nul | find /I "KlavyeMacro.exe" >nul
if not errorlevel 1 (
    echo Uygulama hala acik, 2 saniye daha bekleniyor...
    timeout /t 2 /nobreak >nul
    goto retry
)

echo Yeni surum kopyalaniyor...
move /Y "{new_exe_path}" "{current_exe_path}"
if errorlevel 1 (
    echo HATA: Dosya kopyalanamadi! Yetki sorunu olabilir.
    echo Yeni EXE yolu: {new_exe_path}
    pause
    exit /b 1
)

echo Baslatiliyor: {current_exe_path}
start "" "{current_exe_path}"
echo Guncelleme tamamlandi!
timeout /t 1 /nobreak >nul

del "%~f0"
"""

    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    return bat_path


def launch_updater_and_quit(new_exe_path: str, current_exe_path: str = None):
    """
    Updater bat'ı arka planda başlatır ve uygulamayı kapatır.

    Bu fonksiyon RETURN ETMEZ — sys.exit() çağırır.
    """
    import subprocess

    bat_path = create_updater_script(new_exe_path, current_exe_path)

    # Bat'ı yeni bir pencerede (görünmez) başlat
    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
        close_fds=True
    )

    # Uygulamayı kapat
    sys.exit(0)
