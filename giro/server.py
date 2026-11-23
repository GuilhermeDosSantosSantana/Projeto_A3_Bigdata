"""Servidor local do GIRO. Executar somente quando o grupo decidir testar."""

from __future__ import annotations

import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from giro import db

WEB = Path(__file__).resolve().parents[1] / "web"
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}
POST_ROUTES = {
    "/api/products": db.add_product,
    "/api/receipts": db.add_receipt,
    "/api/sales": db.add_sale,
    "/api/losses": db.add_loss,
}


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, value: object) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/dashboard":
            try:
                self._json(200, db.dashboard())
            except sqlite3.Error:
                self._json(500, {"error": "Falha ao consultar o banco"})
            return
        file_info = STATIC.get(path)
        if not file_info:
            self._json(404, {"error": "Rota não encontrada"})
            return
        filename, mime = file_info
        body = (WEB / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        action = POST_ROUTES.get(path)
        if action is None:
            self._json(404, {"error": "Rota não encontrada"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 100_000:
                raise ValueError("Corpo da requisição inválido")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Envie um objeto JSON")
            identifier = action(data)
            self._json(201, {"id": identifier, "ok": True})
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
        except sqlite3.IntegrityError as exc:
            message = str(exc)
            if "UNIQUE" in message:
                message = "SKU ou referência de entrada já existe"
            else:
                message = "Os dados violam uma regra do banco"
            self._json(409, {"error": message})
        except sqlite3.Error:
            self._json(500, {"error": "Falha ao gravar no banco"})


def main() -> None:
    db.initialize()
    port = int(os.environ.get("GIRO_PORT", "3000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"GIRO disponível em http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
