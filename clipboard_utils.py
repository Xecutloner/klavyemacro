import win32clipboard
import win32con
import pickle
import base64
import time


# Büyük ikili veriler (resim gibi) bazen GetClipboardData'da patlar.
# Bu formatları atlamak için maksimum veri boyutu (10 MB)
_MAX_FORMAT_BYTES = 10 * 1024 * 1024

# Sorun çıkardığı bilinen sistem format ID'leri (bitmap, DIB, meta vb.) - atlanır
_SKIP_FORMATS = {
    win32con.CF_BITMAP,
    win32con.CF_DIB,
    win32con.CF_DIBV5,
    win32con.CF_METAFILEPICT,
    win32con.CF_ENHMETAFILE,
    win32con.CF_DSPBITMAP,
    win32con.CF_PALETTE,
    win32con.CF_OWNERDISPLAY,
    win32con.CF_PENDATA,
}


def _open_clipboard(retries: int = 15, delay: float = 0.05) -> bool:
    """Clipboard'ı kilidi olmadan açmaya çalışır."""
    for _ in range(retries):
        try:
            win32clipboard.OpenClipboard()
            return True
        except Exception:
            time.sleep(delay)
    return False


def _close_clipboard_safe():
    """Clipboard'ı güvenle kapatır."""
    try:
        win32clipboard.CloseClipboard()
    except Exception:
        pass


def dump_raw_clipboard() -> str:
    """
    Panodaki tüm formatları alır (piksel verileri hariç),
    pickle+base64 olarak döndürür. Cihazdan cihaza taşınabilir.
    """
    if not _open_clipboard():
        return ""

    data = {}
    fmt = 0
    try:
        while True:
            fmt = win32clipboard.EnumClipboardFormats(fmt)
            if not fmt:
                break
            # Sorunlu formatları atla
            if fmt in _SKIP_FORMATS:
                continue
            try:
                val = win32clipboard.GetClipboardData(fmt)
                # Çok büyük verileri atla
                if isinstance(val, (bytes, bytearray)) and len(val) > _MAX_FORMAT_BYTES:
                    continue
                # Dinamik formatları (ID >= 0xC000) isimle kaydet (cihazdan cihaza taşınabilir)
                if fmt >= 0xC000:
                    try:
                        name = win32clipboard.GetClipboardFormatName(fmt)
                        data[name] = val
                    except Exception:
                        pass  # İsim alınamazsa atla
                else:
                    data[fmt] = val
            except Exception:
                pass  # Bu format okunamıyorsa atla
    finally:
        _close_clipboard_safe()

    if not data:
        return ""

    try:
        pickled = pickle.dumps(data)
        return base64.b64encode(pickled).decode("utf-8")
    except Exception as e:
        print(f"[clipboard_utils] Serileştirme hatası: {e}")
        return ""


def restore_raw_clipboard(b64_str: str) -> bool:
    """
    base64 verisini çözer ve panoya tam olarak yansıtır.
    Dinamik format isimleri bu bilgisayardaki ID'lere otomatik eşlenir.
    """
    if not b64_str:
        return False

    try:
        pickled = base64.b64decode(b64_str.encode("utf-8"))
        data: dict = pickle.loads(pickled)
    except Exception as e:
        print(f"[clipboard_utils] Deserializasyon hatası: {e}")
        return False

    if not _open_clipboard():
        return False

    try:
        win32clipboard.EmptyClipboard()
        written = 0
        for fmt, val in data.items():
            try:
                # String → bu bilgisayardaki güncel format ID'sine çevir
                if isinstance(fmt, str):
                    actual_fmt = win32clipboard.RegisterClipboardFormat(fmt)
                else:
                    actual_fmt = fmt
                win32clipboard.SetClipboardData(actual_fmt, val)
                written += 1
            except Exception:
                pass  # Tek format yazılamazsa diğerlerine devam et
        return written > 0
    except Exception as e:
        print(f"[clipboard_utils] Pano yazma hatası: {e}")
        return False
    finally:
        _close_clipboard_safe()
