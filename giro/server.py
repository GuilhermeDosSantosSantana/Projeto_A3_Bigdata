"""Local GIRO web server connected to the A3 MySQL database."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import mysql.connector

from giro import cache, mysql_db as db

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


def page_from(query: str) -> int:
    raw = parse_qs(query).get("page", ["1"])[0]
    page = int(raw)
    if not 1 <= page <= 1000:
        raise ValueError("Pagina fora do intervalo permitido")
    return page


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, value: object, cache_state: str | None = None) -> None:
        body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if cache_state:
            self.send_header("X-Giro-Cache", cache_state)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        request = urlsplit(self.path)
        try:
            if request.path == "/api/health":
                with db.connect() as connection, connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                self._json(200, {"ok": True, "database": "MySQL", "cache": cache.status()})
                return
            if request.path == "/api/dashboard":
                data, cache_state = cache.dashboard_summary()
                self._json(200, data, cache_state)
                return
            if request.path == "/api/products":
                params = parse_qs(request.query)
                query = params.get("q", [""])[0][:80]
                situation = params.get("filter", ["all"])[0]
                if situation not in ("all", "risk", "expiry"):
                    raise ValueError("Filtro de produto invalido")
                data, cache_state = cache.catalog_page(page_from(request.query), 12, query, situation)
                self._json(200, data, cache_state)
                return
            if request.path == "/api/customers":
                query = parse_qs(request.query).get("q", [""])[0][:80]
                self._json(200, db.customers(query, page_from(request.query)))
                return
            if request.path == "/api/movements":
                kind = parse_qs(request.query).get("kind", ["all"])[0]
                self._json(200, db.movements(kind, page_from(request.query)))
                return
            if request.path.startswith("/api/products/"):
                self._json(200, db.product_detail(int(request.path.rsplit("/", 1)[-1])))
                return
            if request.path.startswith("/api/customers/"):
                self._json(200, db.customer_detail(int(request.path.rsplit("/", 1)[-1])))
                return
        except ValueError as error:
            self._json(400, {"error": str(error)})
            return
        except (mysql.connector.Error, RuntimeError) as error:
            print(f"MySQL GET failed: {error}")
            self._json(503, {"error": "Banco MySQL indisponivel. Inicie o GIRO novamente."})
            return
        file_info = STATIC.get(request.path)
        if not file_info:
            self._json(404, {"error": "Rota nao encontrada"})
            return
        filename, mime = file_info
        body = (WEB / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        action = POST_ROUTES.get(urlsplit(self.path).path)
        if action is None:
            self._json(404, {"error": "Rota nao encontrada"})
            return
        self._write(action, 201)

    def do_PATCH(self) -> None:
        path = urlsplit(self.path).path
        if not path.startswith("/api/products/") or not path.rsplit("/", 1)[-1].isdigit():
            self._json(404, {"error": "Rota nao encontrada"})
            return
        product_id = int(path.rsplit("/", 1)[-1])
        self._write(lambda data: db.update_product(product_id, data), 200)

    def _write(self, action, success_status: int) -> None:
        try:
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                raise ValueError("Envie JSON")
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= 100_000:
                raise ValueError("Corpo da requisicao invalido")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Envie um objeto JSON")
            identifier = action(data)
            cache.invalidate()
            self._json(success_status, {"id": identifier, "ok": True})
        except (ValueError, json.JSONDecodeError) as error:
            self._json(400, {"error": str(error)})
        except mysql.connector.IntegrityError as error:
            message = "SKU ou referencia ja cadastrado" if error.errno == 1062 else "Dados violam uma regra do banco"
            self._json(409, {"error": message})
        except mysql.connector.Error as error:
            print(f"MySQL POST failed: {error}")
            self._json(503, {"error": "Nao foi possivel gravar no MySQL"})
        except RuntimeError as error:
            print(f"Backend failed: {error}")
            self._json(503, {"error": str(error)})


def main() -> None:
    with db.connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM product")
        print(f"GIRO conectado ao MySQL: {cursor.fetchone()[0]} produtos", flush=True)
    port = int(os.environ.get("GIRO_PORT", "3000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"GIRO disponivel em http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
