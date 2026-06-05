"""
webhook_server.py - KlavyeMacro HTTP Webhook Sunucusu

Makroları HTTP ile tetiklemek için kullanılır.
Varsayılan port: 7474

Endpointler:
  GET  /health           -> {"status": "ok", "macros": <sayı>}
  GET  /macros           -> Tüm etkin makroların listesi
  POST /trigger          -> {"name": "makro adı"} veya {"id": "makro_id"} ile tetikle
  POST /trigger/hotkey   -> {"hotkey": "ctrl+1"} ile hotkey tetikle
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP istek işleyici."""

    # MacroManager ve HotkeyListener dışarıdan atanır
    manager = None
    listener = None

    def log_message(self, format, *args):
        print(f"[Webhook] {self.address_string()} - {format % args}")

    def _send_json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/")

        if path == "/health":
            count = len(self.manager.macros) if self.manager else 0
            self._send_json(200, {"status": "ok", "macros": count,
                                  "app": "KlavyeMacro"})

        elif path == "/macros":
            if not self.manager:
                self._send_json(503, {"error": "Manager hazır değil."})
                return
            macros = [
                {
                    "id": m.id,
                    "name": m.name,
                    "hotkey": m.hotkey,
                    "category": m.category,
                    "enabled": m.enabled,
                    "use_count": m.use_count,
                }
                for m in self.manager.macros
            ]
            self._send_json(200, {"macros": macros, "total": len(macros)})

        else:
            self._send_json(404, {"error": f"Bilinmeyen endpoint: {path}"})

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")
        body = self._read_body()

        if path == "/trigger":
            if not self.manager or not self.listener:
                self._send_json(503, {"error": "Servis hazır değil."})
                return

            # İsim veya ID ile bul
            macro = None
            if "id" in body:
                macro = next((m for m in self.manager.macros
                              if m.id == body["id"] and m.enabled), None)
            elif "name" in body:
                name_lower = body["name"].lower()
                macro = next((m for m in self.manager.macros
                              if m.name.lower() == name_lower and m.enabled), None)

            if not macro:
                self._send_json(404, {"error": "Makro bulunamadı veya devre dışı."})
                return

            # Arka planda çalıştır
            threading.Thread(
                target=self.listener._do_execute,
                args=(macro,),
                daemon=True
            ).start()
            macro.increment_use()
            self._send_json(200, {"status": "triggered", "macro": macro.name})

        elif path == "/trigger/hotkey":
            hotkey = body.get("hotkey", "").strip()
            if not hotkey or not self.manager:
                self._send_json(400, {"error": "hotkey alanı gerekli."})
                return
            macro = self.manager.get_by_hotkey(hotkey)
            if not macro:
                self._send_json(404, {"error": f"'{hotkey}' hotkey'i bulunamadı."})
                return
            threading.Thread(
                target=self.listener._do_execute,
                args=(macro,),
                daemon=True
            ).start()
            macro.increment_use()
            self._send_json(200, {"status": "triggered", "macro": macro.name})

        else:
            self._send_json(404, {"error": f"Bilinmeyen endpoint: {path}"})


class WebhookServer:
    """Arka planda HTTP webhook sunucusu çalıştırır."""

    def __init__(self, manager, listener, port: int = 7474):
        WebhookHandler.manager = manager
        WebhookHandler.listener = listener
        self._port = port
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self):
        try:
            self._server = HTTPServer(("127.0.0.1", self._port), WebhookHandler)
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
                name="WebhookServer"
            )
            self._thread.start()
            print(f"[Webhook] http://127.0.0.1:{self._port} adresinde dinliyor.")
        except OSError as e:
            print(f"[Webhook] Port {self._port} meşgul/hata: {e}")

    def stop(self):
        if self._server:
            self._server.shutdown()
            print("[Webhook] Durduruldu.")

    @property
    def port(self) -> int:
        return self._port
