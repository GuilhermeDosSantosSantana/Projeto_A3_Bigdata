"""Persistência SQLite do GIRO. Nenhuma dependência externa."""

from __future__ import annotations

import math
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "storage" / "giro.sqlite3"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def database():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize() -> None:
    with database() as conn:
        conn.executescript((ROOT / "sql" / "01_schema.sql").read_text(encoding="utf-8"))
        if conn.execute("SELECT COUNT(*) FROM product").fetchone()[0] == 0:
            seed = (ROOT / "sql" / "02_seed.sql").read_text(encoding="utf-8")
            conn.executescript("BEGIN;\n" + seed + "\nCOMMIT;")


def _rows(conn: sqlite3.Connection, query: str, params: tuple = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def dashboard() -> dict:
    with database() as conn:
        products = _rows(conn, "SELECT * FROM product_balance WHERE active = 1 ORDER BY name")
        sales_7d = {
            row["product_id"]: row["quantity"]
            for row in _rows(conn, """
                SELECT product_id, SUM(quantity) AS quantity
                FROM sale WHERE date(sold_at) >= date('now', '-6 days')
                GROUP BY product_id
            """)
        }
        for product in products:
            daily = sales_7d.get(product["id"], 0) / 7
            point = max(product["min_stock"], math.ceil(daily * (product["lead_days"] + 2)))
            product["sold_7d"] = sales_7d.get(product["id"], 0)
            product["daily_average"] = round(daily, 2)
            product["coverage_days"] = round(product["stock"] / daily, 1) if daily else None
            product["reorder_point"] = point
            target = max(product["min_stock"], math.ceil(daily * (product["lead_days"] + 7)))
            product["reorder_quantity"] = max(0, target - product["stock"])
            product["alert"] = "out" if product["stock"] == 0 else "low" if product["stock"] <= point else "ok"
            product["alert_reason"] = (
                "Sem unidades disponíveis" if product["stock"] == 0
                else f"Estoque {product['stock']} ≤ ponto de reposição {point}"
                if product["alert"] == "low" else "Estoque acima do ponto de reposição"
            )

        batches = _rows(conn, """
            SELECT bb.id, bb.product_id, p.name AS product, bb.available_quantity,
                   bb.expires_on, bb.received_at, bb.unit_cost_cents
            FROM batch_balance bb JOIN product p ON p.id = bb.product_id
            WHERE bb.available_quantity > 0
              AND (bb.expires_on IS NULL OR date(bb.expires_on) >= date('now'))
            ORDER BY CASE WHEN bb.expires_on IS NULL THEN 1 ELSE 0 END, bb.expires_on
        """)
        trend = _rows(conn, """
            SELECT date(sold_at) AS day, SUM(quantity) AS units,
                   SUM(quantity * unit_price_cents) AS revenue_cents
            FROM sale WHERE date(sold_at) >= date('now', '-6 days')
            GROUP BY date(sold_at) ORDER BY day
        """)
        recent = _rows(conn, """
            SELECT 'ENTRY' AS kind, b.id, p.name AS product, b.quantity_received AS quantity,
                   b.received_at AS at, b.source_ref AS detail
            FROM batch b JOIN product p ON p.id = b.product_id
            UNION ALL
            SELECT e.kind, e.id, p.name, e.quantity, e.occurred_at,
                   CASE WHEN e.kind = 'LOSS' THEN e.reason ELSE 'Venda registrada' END
            FROM stock_event e JOIN batch b ON b.id = e.batch_id
            JOIN product p ON p.id = b.product_id
            ORDER BY at DESC, id DESC LIMIT 12
        """)
        categories = _rows(conn, "SELECT * FROM category ORDER BY name")
        suppliers = _rows(conn, "SELECT * FROM supplier ORDER BY name")
        category_totals = []
        for category in categories:
            group = [p for p in products if p["category_id"] == category["id"]]
            category_totals.append({
                "name": category["name"], "color": category["color"],
                "value_cents": sum(p["stock_value_cents"] for p in group),
                "products": len(group),
            })
        return {
            "products": products,
            "batches": batches,
            "categories": categories,
            "suppliers": suppliers,
            "category_totals": category_totals,
            "trend": trend,
            "recent": recent,
            "metrics": {
                "stock_value_cents": sum(p["stock_value_cents"] for p in products),
                "products_at_risk": sum(p["alert"] != "ok" for p in products),
                "expiring_lots_7d": sum(
                    bool(b["expires_on"]) and datetime.now(timezone.utc).date().isoformat() <= b["expires_on"]
                    <= (datetime.now(timezone.utc).date() + timedelta(days=7)).isoformat()
                    for b in batches
                ),
                "revenue_7d_cents": sum(item["revenue_cents"] for item in trend),
                "active_products": len(products),
            },
        }


def _positive_int(value: object, label: str, limit: int = 100000) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} deve ser um número inteiro positivo")
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} deve ser um número inteiro positivo") from None
    if str(result) != str(value).strip() or not 0 < result <= limit:
        raise ValueError(f"{label} deve estar entre 1 e {limit}")
    return result


def _nonnegative_int(value: object, label: str, limit: int = 10000000) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} deve ser um número inteiro")
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} deve ser um número inteiro") from None
    if str(result) != str(value).strip() or not 0 <= result <= limit:
        raise ValueError(f"{label} deve estar entre 0 e {limit}")
    return result


def add_product(data: dict) -> int:
    sku = str(data.get("sku", "")).strip().upper()
    name = str(data.get("name", "")).strip()
    unit = str(data.get("unit", "")).strip()
    if not 3 <= len(sku) <= 24 or not 3 <= len(name) <= 80:
        raise ValueError("Informe SKU e nome com pelo menos 3 caracteres")
    if unit not in {"un", "pct", "cx"}:
        raise ValueError("Unidade inválida")
    with database() as conn:
        cursor = conn.execute("""
            INSERT INTO product(sku,name,category_id,supplier_id,unit,min_stock,lead_days,sale_price_cents)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            sku, name, _positive_int(data.get("category_id"), "Categoria"),
            _positive_int(data.get("supplier_id"), "Fornecedor"), unit,
            _nonnegative_int(data.get("min_stock"), "Estoque mínimo"),
            _positive_int(data.get("lead_days"), "Prazo do fornecedor", 90),
            _nonnegative_int(data.get("sale_price_cents"), "Preço"),
        ))
        return cursor.lastrowid


def add_receipt(data: dict) -> int:
    product_id = _positive_int(data.get("product_id"), "Produto")
    quantity = _positive_int(data.get("quantity"), "Quantidade")
    cost = _nonnegative_int(data.get("unit_cost_cents"), "Custo")
    expires_on = data.get("expires_on") or None
    if expires_on:
        try:
            expiry = date.fromisoformat(str(expires_on))
        except ValueError:
            raise ValueError("Validade deve estar em AAAA-MM-DD") from None
        if expiry < datetime.now(timezone.utc).date():
            raise ValueError("Não é permitido entrar lote já vencido")
        expires_on = expiry.isoformat()
    source_ref = str(data.get("source_ref", "")).strip() or None
    if source_ref and len(source_ref) > 80:
        raise ValueError("Referência da entrada deve ter no máximo 80 caracteres")
    with database() as conn:
        product = conn.execute("SELECT id FROM product WHERE id = ? AND active = 1", (product_id,)).fetchone()
        if not product:
            raise ValueError("Produto não encontrado")
        cursor = conn.execute("""
            INSERT INTO batch(product_id,quantity_received,unit_cost_cents,expires_on,source_ref)
            VALUES (?,?,?,?,?)
        """, (product_id, quantity, cost, expires_on, source_ref))
        return cursor.lastrowid


def _consume(product_id: int, quantity: int, kind: str, reason: str | None) -> int:
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        product = conn.execute(
            "SELECT id,sale_price_cents FROM product WHERE id = ? AND active = 1", (product_id,)
        ).fetchone()
        if not product:
            raise ValueError("Produto não encontrado")
        expiry_filter = "AND (expires_on IS NULL OR date(expires_on) >= date('now'))" if kind == "SALE" else ""
        batches = _rows(conn, f"""
            SELECT id, available_quantity FROM batch_balance
            WHERE product_id = ? AND available_quantity > 0
              {expiry_filter}
            ORDER BY CASE WHEN expires_on IS NULL THEN 1 ELSE 0 END,
                     expires_on, received_at, id
        """, (product_id,))
        if sum(b["available_quantity"] for b in batches) < quantity:
            raise ValueError("Estoque disponível insuficiente; venda não pode usar lote vencido")
        sale_id = None
        if kind == "SALE":
            sale_id = conn.execute(
                "INSERT INTO sale(product_id,quantity,unit_price_cents) VALUES (?,?,?)",
                (product_id, quantity, product["sale_price_cents"]),
            ).lastrowid
        remaining = quantity
        for batch in batches:
            take = min(remaining, batch["available_quantity"])
            if take:
                conn.execute("""
                    INSERT INTO stock_event(batch_id,kind,quantity,sale_id,reason)
                    VALUES (?,?,?,?,?)
                """, (batch["id"], kind, take, sale_id, reason))
                remaining -= take
            if remaining == 0:
                break
        conn.commit()
        return sale_id if sale_id is not None else quantity
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def add_sale(data: dict) -> int:
    return _consume(
        _positive_int(data.get("product_id"), "Produto"),
        _positive_int(data.get("quantity"), "Quantidade"), "SALE", None,
    )


def add_loss(data: dict) -> int:
    reason = str(data.get("reason", "")).strip()
    if not 3 <= len(reason) <= 120:
        raise ValueError("Informe o motivo da perda em até 120 caracteres")
    return _consume(
        _positive_int(data.get("product_id"), "Produto"),
        _positive_int(data.get("quantity"), "Quantidade"), "LOSS", reason,
    )
