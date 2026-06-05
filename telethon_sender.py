"""
telethon_sender.py - Telegram API ile zengin formatlama destekli mesaj gonderici.
Destekler: [text](url) hyperlink, **kalin**, __italic__, gorsel+caption, premium emoji.
"""

import asyncio
import os
import re
import threading
import json
import win32gui
from typing import Optional, Callable

import sys

# ---------------------------------------------------------------------------
# Session & Config
# ---------------------------------------------------------------------------
# PyInstaller EXE'de __file__ geçici temp dizinine işaret eder.
# Bunun yerine sys.executable'ın bulunduğu klasörü kullanıyoruz —
# bu sayede tg_session ve tg_creds.json her zaman EXE'nin yanında kalır,
# güncelleme sonrası silinmez.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)   # dist/KlavyeMacro.exe klasörü
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # geliştirme modu

SESSION    = os.path.join(BASE_DIR, "tg_session")
CREDS_FILE = os.path.join(BASE_DIR, "tg_creds.json")


def load_creds() -> dict:
    """tg_creds.json'dan API bilgilerini yukler."""
    if os.path.exists(CREDS_FILE):
        try:
            with open(CREDS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_creds(api_id: str, api_hash: str, phone: str):
    """API bilgilerini kaydeder."""
    with open(CREDS_FILE, "w", encoding="utf-8") as f:
        json.dump({"api_id": api_id, "api_hash": api_hash, "phone": phone}, f)


# ---------------------------------------------------------------------------
# Event loop (arka planda surekli calisir)
# ---------------------------------------------------------------------------
_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None
_client = None
_client_lock = threading.Lock()


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop, _loop_thread
    if _loop is None or not _loop.is_running():
        _loop = asyncio.new_event_loop()
        _loop_thread = threading.Thread(target=_loop.run_forever, daemon=True, name="TelethonLoop")
        _loop_thread.start()
    return _loop


def _run(coro, timeout=30):
    """Bir coroutine'i arka plan loop'unda calistirir (blocking)."""
    loop = _get_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=timeout)


# ---------------------------------------------------------------------------
# Client management
# ---------------------------------------------------------------------------
def get_client():
    global _client
    creds = load_creds()
    if not creds.get("api_id") or not creds.get("api_hash"):
        raise RuntimeError("API bilgileri eksik. Ayarlar > Telegram API bolumunden girin.")
    from telethon import TelegramClient
    with _client_lock:
        if _client is None:
            _client = TelegramClient(SESSION, int(creds["api_id"]), creds["api_hash"],
                                     loop=_get_loop())
    return _client


async def _async_connect(phone: str, code_cb: Optional[Callable] = None,
                          password_cb: Optional[Callable] = None):
    """Baglanti kurar, gerekirse OTP ve 2FA ister."""
    from telethon.errors import SessionPasswordNeededError
    client = get_client()
    await client.connect()
    if await client.is_user_authorized():
        return True, "Zaten giris yapilmis."
    await client.send_code_request(phone)
    code = code_cb() if code_cb else None
    if not code:
        return False, "Dogrulama kodu girilmedi."
    try:
        await client.sign_in(phone, code)
    except SessionPasswordNeededError:
        pwd = password_cb() if password_cb else None
        if not pwd:
            return False, "2FA sifresi gerekli."
        await client.sign_in(password=pwd)
    return True, "Giris basarili!"


def connect(phone: str, code_cb=None, password_cb=None, timeout=90):
    """Senkron giris - GUI'den cagirilir."""
    return _run(_async_connect(phone, code_cb, password_cb), timeout=timeout)


def is_authorized() -> bool:
    try:
        client = get_client()
        return _run(client.is_user_authorized(), timeout=5)
    except Exception:
        return False


def disconnect():
    global _client
    try:
        if _client:
            _run(_client.disconnect(), timeout=5)
    except Exception:
        pass
    _client = None


# ---------------------------------------------------------------------------
# Markdown -> Telegram entities parser
# ---------------------------------------------------------------------------
def _parse_markdown(text: str):
    """
    Gelişmiş markdown'i parse ederek (plain_text, entities) döndürür.
    Desteklenen formatlar:
      [metin](https://url.com)               -> TextUrl (link)
      [emoji](tg://emoji?id=12345678)        -> CustomEmoji (premium emoji!)
      **kalin metin**                         -> Bold
      __italik metin__                        -> Italic
      `kod metni`                             -> Code (monospace)
      ~~üstü çizili~~                          -> Strikethrough
      ||spoiler metin||                       -> Spoiler
    """
    from telethon.tl import types as tl

    pattern = re.compile(
        r'\[(?P<link_text>[^\]]+)\]\((?P<url>[^)]+)\)'  # [text](url) veya [text](tg://emoji?id=...)
        r'|\*\*(?P<bold>.+?)\*\*'                          # **bold**
        r'|__(?P<italic>.+?)__'                             # __italic__
        r'|`(?P<code>[^`]+)`'                               # `code`
        r'|~~(?P<strike>.+?)~~'                             # ~~strikethrough~~
        r'|\|\|(?P<spoiler>.+?)\|\|',                       # ||spoiler||
        re.DOTALL
    )

    plain = ""
    entities = []
    pos = 0

    for m in pattern.finditer(text):
        plain += text[pos:m.start()]

        if m.group("url") is not None:
            link_text = m.group("link_text")
            url       = m.group("url")
            start  = len(plain.encode("utf-16-le")) // 2
            plain += link_text
            length = len(plain.encode("utf-16-le")) // 2 - start

            # Premium emoji: tg://emoji?id=DOCUMENT_ID
            if url.startswith("tg://emoji?id="):
                try:
                    doc_id = int(url.split("=", 1)[1])
                    entities.append(tl.MessageEntityCustomEmoji(
                        offset=start, length=length, document_id=doc_id
                    ))
                except (ValueError, IndexError):
                    # Parse edilemezse normal link olarak ekle
                    entities.append(tl.MessageEntityTextUrl(
                        offset=start, length=length, url=url
                    ))
            else:
                entities.append(tl.MessageEntityTextUrl(
                    offset=start, length=length, url=url
                ))

        elif m.group("bold") is not None:
            bd = m.group("bold")
            start  = len(plain.encode("utf-16-le")) // 2
            plain += bd
            length = len(plain.encode("utf-16-le")) // 2 - start
            entities.append(tl.MessageEntityBold(offset=start, length=length))

        elif m.group("italic") is not None:
            it = m.group("italic")
            start  = len(plain.encode("utf-16-le")) // 2
            plain += it
            length = len(plain.encode("utf-16-le")) // 2 - start
            entities.append(tl.MessageEntityItalic(offset=start, length=length))

        elif m.group("code") is not None:
            cd = m.group("code")
            start  = len(plain.encode("utf-16-le")) // 2
            plain += cd
            length = len(plain.encode("utf-16-le")) // 2 - start
            entities.append(tl.MessageEntityCode(offset=start, length=length))

        elif m.group("strike") is not None:
            st = m.group("strike")
            start  = len(plain.encode("utf-16-le")) // 2
            plain += st
            length = len(plain.encode("utf-16-le")) // 2 - start
            entities.append(tl.MessageEntityStrike(offset=start, length=length))

        elif m.group("spoiler") is not None:
            sp = m.group("spoiler")
            start  = len(plain.encode("utf-16-le")) // 2
            plain += sp
            length = len(plain.encode("utf-16-le")) // 2 - start
            entities.append(tl.MessageEntitySpoiler(offset=start, length=length))

        pos = m.end()

    plain += text[pos:]
    return plain, entities


# ---------------------------------------------------------------------------
# Emoji ID çıkarıcı (GUI için)
# ---------------------------------------------------------------------------
async def _async_get_emoji_ids(message_link: str) -> list:
    """
    Bir Telegram mesaj linkinden (https://t.me/xxx/123) özel emoji ID'lerini çıkarır.
    Returns: [(emoji_char, document_id), ...]
    """
    from telethon.tl import types as tl
    client = get_client()
    if not client.is_connected():
        await client.connect()

    # Link parse: t.me/chat/msgid veya t.me/c/channel_id/msgid
    parts = message_link.rstrip("/").split("/")
    try:
        msg_id = int(parts[-1])
        chat_part = parts[-2]
        if chat_part == "c":
            # Private supergroup: t.me/c/CHANNEL_ID/MSG_ID
            channel_id = int(parts[-2] if len(parts) > 2 else parts[-1])
            entity = await client.get_entity(int(f"-100{channel_id}"))
        else:
            entity = await client.get_entity(chat_part)
    except Exception as e:
        raise RuntimeError(f"Mesaj linki parse edilemedi: {e}")

    msg = await client.get_messages(entity, ids=msg_id)
    if not msg:
        raise RuntimeError("Mesaj bulunamadı.")

    results = []
    if msg.entities:
        text = msg.message or ""
        for ent in msg.entities:
            if isinstance(ent, tl.MessageEntityCustomEmoji):
                # Entity'nin kapsadığı emoji karakterini al
                chars = text[ent.offset: ent.offset + ent.length]
                results.append((chars, ent.document_id))
    return results


def get_emoji_ids_from_message(message_link: str, timeout: float = 30) -> list:
    """Senkron wrapper — GUI'den çağrılır."""
    return _run(_async_get_emoji_ids(message_link), timeout=timeout)


# ---------------------------------------------------------------------------
# Emoji Paketi İndirici
# ---------------------------------------------------------------------------
async def _async_get_emoji_pack(pack_input: str) -> list:
    """
    Telegram emoji/sticker paketindeki tüm özel emoji'lerin (char, doc_id)
    listesini döner.

    pack_input örnekleri:
      https://t.me/addemoji/PackShortName
      https://t.me/addstickers/PackShortName
      PackShortName   (direkt kısa ad)
    """
    from telethon.tl.functions.messages import GetStickerSetRequest
    from telethon.tl.types import InputStickerSetShortName

    client = get_client()
    if not client.is_connected():
        await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Telegram hesabina giris yapilmamis.")

    # Link'ten kısa adı çıkar
    short_name = pack_input.strip().rstrip("/")
    for prefix in ("https://t.me/addemoji/", "https://t.me/addstickers/",
                   "t.me/addemoji/", "t.me/addstickers/"):
        if short_name.startswith(prefix):
            short_name = short_name[len(prefix):]
            break
    short_name = short_name.split("?")[0].strip()

    result = await client(GetStickerSetRequest(
        stickerset=InputStickerSetShortName(short_name=short_name),
        hash=0
    ))

    # Paket meta bilgisi
    pack_title = getattr(result.set, "title", short_name)
    total = getattr(result.set, "count", 0)

    # Her emoji karakteri → document_id eşlemesi
    emojis = []
    seen = set()
    for pack in result.packs:
        char = pack.emoticon
        for doc_id in pack.documents:
            key = (char, doc_id)
            if key not in seen:
                seen.add(key)
                emojis.append((char, doc_id))

    return {
        "title": pack_title,
        "short_name": short_name,
        "total": total,
        "emojis": emojis,   # [(char, doc_id), ...]
    }


def get_emoji_pack(pack_input: str, timeout: float = 30) -> dict:
    """Senkron wrapper — GUI'den çağrılır."""
    return _run(_async_get_emoji_pack(pack_input), timeout=timeout)



# ---------------------------------------------------------------------------
# Mesajdan Medya İndirici (GUI için)
# ---------------------------------------------------------------------------
def _parse_tg_link(link: str):
    """
    Telegram mesaj linkini parse eder.
    Desteklenen formatlar:
      https://t.me/kanaladi/123
      https://t.me/c/1234567890/123      (özel grup/kanal)
      https://t.me/username/123?single
    Returns: (entity_str_or_int, msg_id_int)
    """
    link = link.strip().rstrip("/").split("?")[0]
    parts = link.split("/")
    # Son eleman mesaj ID'si olmalı
    try:
        msg_id = int(parts[-1])
    except ValueError:
        raise ValueError(f"Geçersiz mesaj linki — sonunda mesaj ID'si olmalı: {link}")

    if len(parts) >= 2 and parts[-2] == "c":
        # t.me/c/CHANNEL_ID/MSG_ID  → private kanal
        if len(parts) < 3:
            raise ValueError("Özel kanal linki eksik.")
        channel_id = int(parts[-3] if len(parts) >= 3 else parts[-2])
        return int(f"-100{channel_id}"), msg_id
    else:
        # t.me/username/MSG_ID
        username = parts[-2]
        return username, msg_id


async def _async_fetch_media(message_link: str, save_dir: str) -> dict:
    """
    Telegram mesaj linkindeki medyayı indirir + premium emoji ID'lerini çıkarır.

    Returns:
        {
            "files": ["/path/to/file1.jpg", ...],  # indirilen dosya yolları
            "text": "mesaj metni",                  # mesajın yazısı (varsa)
            "type": "photo" | "video" | "sticker" | "document" | "none",
            "emojis": [("🔥", 12345678), ...]       # premium emoji (char, doc_id) listesi
        }
    """
    from telethon.tl import types as tl

    client = get_client()
    if not client.is_connected():
        await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Telegram hesabına giriş yapılmamış. Ayarlar → Telegram API.")

    entity_ref, msg_id = _parse_tg_link(message_link)
    entity = await client.get_entity(entity_ref)
    msg = await client.get_messages(entity, ids=msg_id)

    if not msg:
        raise RuntimeError("Mesaj bulunamadı. Link doğru mu?")

    os.makedirs(save_dir, exist_ok=True)
    downloaded = []
    media_type = "none"

    # Tekil medya
    if msg.media:
        if hasattr(msg.media, "photo") and msg.media.photo:
            media_type = "photo"
            path = await client.download_media(msg.media, file=save_dir)
            if path:
                downloaded.append(str(path))

        elif hasattr(msg.media, "document") and msg.media.document:
            doc = msg.media.document
            # MIME'e göre türü belirle
            mime = getattr(doc, "mime_type", "") or ""
            if "video" in mime or "gif" in mime:
                media_type = "video"
            elif "webp" in mime or "tgs" in mime:
                media_type = "sticker"
            else:
                media_type = "document"
            path = await client.download_media(msg.media, file=save_dir)
            if path:
                downloaded.append(str(path))

    # Grouped (albüm) mesajlar — aynı grouped_id'li önceki/sonraki mesajları da çek
    elif hasattr(msg, "grouped_id") and msg.grouped_id:
        media_type = "album"
        surrounding = await client.get_messages(entity, min_id=msg_id - 10, max_id=msg_id + 10)
        for m in surrounding:
            if getattr(m, "grouped_id", None) == msg.grouped_id and m.media:
                path = await client.download_media(m.media, file=save_dir)
                if path:
                    downloaded.append(str(path))

    # Premium emoji ID'lerini çıkar
    emojis = []
    raw_text = msg.message or ""
    if msg.entities:
        for ent in msg.entities:
            if isinstance(ent, tl.MessageEntityCustomEmoji):
                char = raw_text[ent.offset: ent.offset + ent.length]
                emojis.append((char, ent.document_id))

    return {
        "files": downloaded,
        "text": raw_text,
        "type": media_type,
        "emojis": emojis,          # [(emoji_char, document_id), ...]
    }


def fetch_media_from_message(message_link: str, save_dir: str = None,
                             timeout: float = 60) -> dict:
    """
    Telegram mesaj linkindeki fotoğraf/video/sticker/GIF'i indirir
    ve premium emoji ID'lerini çıkarır.

    Args:
        message_link: Telegram mesaj linki (https://t.me/...)
        save_dir: Dosyaların kaydedileceği klasör (None = uygulama/media)
        timeout: Saniye cinsinden bekleme süresi

    Returns:
        {
            "files": [...],
            "text": "...",
            "type": "photo"|"video"|...,
            "emojis": [("🔥", 12345), ...]
        }
    """
    if save_dir is None:
        save_dir = os.path.join(BASE_DIR, "media")
    return _run(_async_fetch_media(message_link, save_dir), timeout=timeout)





# ---------------------------------------------------------------------------
# Dialog Önbelleği (her tetiklemede 500 diyalog taramayı engeller)
# ---------------------------------------------------------------------------
_dialog_cache: list = []          # [(name, entity), ...]
_dialog_cache_ts: float = 0.0     # Son yenileme zamanı
_CACHE_TTL: float = 300.0         # 5 dakika

async def _refresh_dialog_cache(client):
    """Dialog listesini yeniler ve önbelleğe alır."""
    global _dialog_cache, _dialog_cache_ts
    import time as _time
    strip_chars = "\u200e\u200f\u202a\u202b\u202c\u202d\u202e"
    cache = []
    async for dlg in client.iter_dialogs(limit=300):
        name = (dlg.name or "").strip(strip_chars).strip()
        if name:
            cache.append((name, dlg.entity))
    _dialog_cache = cache
    _dialog_cache_ts = _time.monotonic()


async def _detect_active_chat(window_title: str = ""):
    """
    Aktif Telegram sohbetini bulur.
    window_title: Hotkey anında yakalanan pencere başlığı (gecikmeden korunmak için)
    """
    import time as _time
    global _dialog_cache, _dialog_cache_ts

    client = get_client()
    strip_chars = "\u200e\u200f\u202a\u202b\u202c\u202d\u202e"

    # Pencere başlığını dışarıdan al, yoksa şu anki ön pencereyi kullan
    title = window_title or win32gui.GetWindowText(win32gui.GetForegroundWindow())
    title = title.strip(strip_chars)

    # " – Telegram Desktop" veya benzeri son eki kaldır
    parts = re.split(r"\s*[–—\-]\s*Telegram", title)
    if not parts or not parts[0].strip():
        raise RuntimeError(
            "Aktif Telegram penceresi bulunamadi.\n"
            "Makroyu tetiklemeden once Telegram chat penceresini tiklayin."
        )

    chat_name = parts[0].strip(strip_chars).strip()
    # "(3)" gibi okunmamis mesaj sayacini temizle
    chat_name = re.sub(r"\s*\(\d+\)\s*$", "", chat_name).strip()

    # ── Ozel durum: Kayitli Mesajlar (Saved Messages) ──────────────────
    # Bu chat kendi hesabimizdir, get_me() ile alinir.
    _SAVED_NAMES = {
        "kayitli mesajlar", "saved messages", "saved",
        "kayıtlı mesajlar",   # Turkce
    }
    if chat_name.lower() in _SAVED_NAMES:
        return await client.get_me()

    # Önbellekten bak (TTL dolmadıysa)
    now = _time.monotonic()
    if _dialog_cache and (now - _dialog_cache_ts) < _CACHE_TTL:
        for name, entity in _dialog_cache:
            if name.lower() == chat_name.lower():   # Büyük/küçük harf duyarsız
                return entity
    
    # Önbellek boş veya süresi dolmuş — yenile
    await _refresh_dialog_cache(client)
    
    for name, entity in _dialog_cache:
        if name.lower() == chat_name.lower():
            return entity

    # Önbellekte yoksa direkt entity dene (username/ID olabilir)
    try:
        return await client.get_entity(chat_name)
    except Exception:
        pass

    raise RuntimeError(
        f"'{chat_name}' sohbeti bulunamadi.\n"
        f"Telegram'da o sohbeti acin ve tekrar deneyin.\n\n"
        f"Ipucu: Oncce Telegram penceresini tiklayin, sonra hotkey'e basin."
    )


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------
async def _async_send(text: str, image_path: str = "", window_title: str = ""):
    from telethon.errors import FloodWaitError
    import asyncio

    client = get_client()

    # Bağlantıyı garantile — kopuksa yeniden bağlan
    for attempt in range(3):
        try:
            if not client.is_connected():
                await client.connect()
            if not await client.is_user_authorized():
                raise RuntimeError("Telegram hesabina giris yapilmamis. Ayarlar > Telegram API.")
            break
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"Telegram'a baglanamadi ({e}). Ayarlar > Telegram API.")
            await asyncio.sleep(1)

    entity = await _detect_active_chat(window_title)
    plain_text, entities = _parse_markdown(text)

    # FloodWait'e karşı retry (max 3 deneme)
    for attempt in range(3):
        try:
            if image_path and os.path.exists(image_path):
                await client.send_file(
                    entity,
                    image_path,
                    caption=plain_text,
                    formatting_entities=entities if entities else None,
                    link_preview=False,
                )
            else:
                await client.send_message(
                    entity,
                    plain_text,
                    formatting_entities=entities if entities else None,
                    link_preview=False,
                )
            return  # Başarılı
        except FloodWaitError as e:
            wait = min(e.seconds + 1, 30)  # Max 30 saniye bekle
            await asyncio.sleep(wait)
        except Exception as e:
            err = str(e)
            # Bağlantı hatası — yeniden bağlanıp dene
            if "disconnected" in err.lower() or "connection" in err.lower():
                try:
                    await client.disconnect()
                    await asyncio.sleep(1)
                    await client.connect()
                except Exception:
                    pass
                if attempt == 2:
                    raise RuntimeError(f"Mesaj gonderilemedi (baglanti hatasi): {e}")
            else:
                raise  # Diğer hatalar direkt ilet


def send(text: str, image_path: str = "", window_title: str = "", timeout: float = 30):
    """
    Ana send fonksiyonu — hotkey_listener'dan cagrilir.
    window_title: Hotkey aninda yakalanan Telegram pencere basligi.
    Raises RuntimeError on failure (caller should catch).
    """
    _run(_async_send(text, image_path, window_title), timeout=timeout)


async def _async_send_to(target_name: str, text: str, image_path: str = ""):
    """Belirli bir sohbet adına gönderir (broadcast için)."""
    from telethon.errors import FloodWaitError
    import asyncio

    client = get_client()
    for attempt in range(3):
        try:
            if not client.is_connected():
                await client.connect()
            if not await client.is_user_authorized():
                raise RuntimeError("Telegram hesabına giriş yapılmamış.")
            break
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"Telegram'a baglanamadi: {e}")
            await asyncio.sleep(1)

    # Dialog listesinde ada göre ara
    entity = None
    async for dlg in client.iter_dialogs(limit=500):
        if (dlg.name or "").strip().lower() == target_name.strip().lower():
            entity = dlg.entity
            break

    # Bulunamazsa username dene
    if entity is None:
        try:
            entity = await client.get_entity(target_name)
        except Exception:
            raise RuntimeError(f"'{target_name}' sohbeti bulunamadı.")

    plain_text, entities = _parse_markdown(text)

    for attempt in range(3):
        try:
            if image_path and os.path.exists(image_path):
                await client.send_file(
                    entity, image_path,
                    caption=plain_text,
                    formatting_entities=entities if entities else None,
                    link_preview=False,
                )
            else:
                await client.send_message(
                    entity, plain_text,
                    formatting_entities=entities if entities else None,
                    link_preview=False,
                )
            return
        except FloodWaitError as e:
            await asyncio.sleep(min(e.seconds + 1, 30))
        except Exception as e:
            err = str(e)
            if "disconnected" in err.lower() or "connection" in err.lower():
                try:
                    await client.disconnect()
                    await asyncio.sleep(1)
                    await client.connect()
                except Exception:
                    pass
                if attempt == 2:
                    raise RuntimeError(f"Mesaj gonderilemedi: {e}")
            else:
                raise


def send_to(target_name: str, text: str, image_path: str = "", timeout: float = 30):
    """Broadcast için belirli sohbete gönderir — hotkey_listener'dan çağrılır."""
    _run(_async_send_to(target_name, text, image_path), timeout=timeout)



# Sprint 5 — Son mesajı sil
async def _async_delete_last():
    """Aktif sohbetteki son mesajımızı siler."""
    client = get_client()
    if not client or not client.is_connected():
        raise RuntimeError("Telethon bağlantısı yok. Önce API ayarlarını yapın.")

    me = await client.get_me()
    # İlk birkaç diyaloğu tara — son gönderilen mesajı bul
    async for dialog in client.iter_dialogs(limit=5):
        messages = await client.get_messages(dialog.entity, limit=10, from_user=me)
        if messages:
            await client.delete_messages(dialog.entity, [messages[0].id])
            return
    raise RuntimeError("Silinecek kendi mesajın bulunamadı.")


def delete_last_message(timeout: float = 30):
    """Son gönderilen mesajı Telethon ile siler."""
    _run(_async_delete_last(), timeout=timeout)
