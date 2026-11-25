"""End-to-end HTTP smoke test against the local GIRO/MySQL installation.

Creates one identifiable synthetic product and leaves it as pitch demo data.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from uuid import uuid4

from giro import mysql_db

BASE = "http://127.0.0.1:3000"


def request(path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={"Content-Type": "application/json"} if body else {})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def main():
    health_status, health = request("/api/health")
    assert health_status == 200 and health["ok"] and health["database"] == "MySQL", health
    status, found = request("/api/customers?q=CLI-001")
    assert status == 200 and found["items"][0]["id"] == 1
    code = uuid4().hex[:8].upper()
    status, product = request("/api/products", {
        "sku": f"PITCH-{code}", "name": "Produto demonstracao GIRO",
        "category_id": 1, "supplier_id": 1, "unit": "un",
        "min_stock": 3, "lead_days": 3, "sale_price_cents": 1290,
    })
    assert status == 201, product
    product_id = product["id"]
    batches = []
    for when in ("2027-01-01", "2027-06-01"):
        status, entry = request("/api/receipts", {
            "product_id": product_id, "quantity": 5, "unit_cost_cents": 700,
            "expires_on": when, "source_ref": f"PITCH-{code}-{when}",
        })
        assert status == 201, entry
        batches.append(entry["id"])
    status, sale = request("/api/sales", {
        "product_id": product_id, "quantity": 7, "customer_id": 1,
    })
    assert status == 201, sale
    status, loss = request("/api/losses", {
        "product_id": product_id, "quantity": 1, "reason": "Teste de avaria",
    })
    assert status == 201, loss
    status, refused = request("/api/sales", {
        "product_id": product_id, "quantity": 100, "customer_id": 1,
    })
    assert status == 400 and "insuficiente" in refused["error"].lower(), refused
    with mysql_db.connect() as connection, connection.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT stock FROM product_balance WHERE id=%s", (product_id,))
        assert cursor.fetchone()["stock"] == 2
        cursor.execute("SELECT customer_id FROM sale WHERE id=%s", (sale["id"],))
        assert cursor.fetchone()["customer_id"] == 1
        cursor.execute("""SELECT batch_id,kind,quantity FROM stock_event
                          WHERE sale_id=%s ORDER BY batch_id""", (sale["id"],))
        events = cursor.fetchall()
        assert events == [
            {"batch_id": batches[0], "kind": "SALE", "quantity": 5},
            {"batch_id": batches[1], "kind": "SALE", "quantity": 2},
        ], events
    print(f"OK: produto {product_id}, 2 entradas, venda {sale['id']} com cliente, perda e recusa por estoque insuficiente")


if __name__ == "__main__":
    main()
