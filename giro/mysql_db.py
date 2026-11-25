"""GIRO application queries and transactions on the A3 MySQL database."""

from __future__ import annotations

import configparser
from datetime import date, datetime, timezone
from pathlib import Path

import mysql.connector

CONFIG = Path(__file__).resolve().parents[1] / "mysql" / "runtime" / "app.cnf"


def connect():
    parser = configparser.ConfigParser()
    if not parser.read(CONFIG, encoding="utf-8"):
        raise RuntimeError("Configure o acesso ao MySQL com scripts/configurar_app_mysql.py")
    section = parser["client"]
    return mysql.connector.connect(
        user=section["user"], password=section["password"],
        host=section.get("host", "127.0.0.1"), port=section.getint("port", 3306),
        database="giro_a3", charset="utf8mb4", connection_timeout=10,
    )


def rows(cursor, sql, params=()):
    cursor.execute(sql, params)
    return cursor.fetchall()


def integer(data, key, minimum=0, maximum=10_000_000):
    value = data.get(key)
    if isinstance(value, bool):
        raise ValueError(f"{key}: informe um numero inteiro")
    try:
        result = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{key}: informe um numero inteiro") from None
    if str(value).strip() != str(result) or not minimum <= result <= maximum:
        raise ValueError(f"{key}: valor fora do intervalo permitido")
    return result


def label(data, key, minimum=3, maximum=80):
    value = str(data.get(key, "")).strip()
    if not minimum <= len(value) <= maximum:
        raise ValueError(f"{key}: use entre {minimum} e {maximum} caracteres")
    return value


def dashboard():
    with connect() as connection, connection.cursor(dictionary=True) as cursor:
        products = rows(cursor, """
            SELECT pb.*, COALESCE(d.units_7d,0) AS units_7d
            FROM product_balance pb
            LEFT JOIN (
              SELECT product_id, SUM(quantity) AS units_7d
              FROM sale WHERE sold_at >= UTC_TIMESTAMP() - INTERVAL 7 DAY
              GROUP BY product_id
            ) d ON d.product_id = pb.id
            ORDER BY pb.id
        """)
        for product in products:
            daily = float(product["units_7d"]) / 7
            stock = int(product["stock"])
            reorder_point = max(product["min_stock"], int(daily * (product["lead_days"] + 2) + .999))
            product["stock"] = stock
            product["stock_value_cents"] = int(product["stock_value_cents"])
            product["expiring_7d"] = int(product["expiring_7d"])
            product["reorder_quantity"] = max(0, reorder_point - stock)
            product["coverage_days"] = round(stock / daily, 1) if daily else None
            product["alert"] = "inactive" if not product["active"] else "out" if stock == 0 else "low" if stock <= reorder_point else "ok"
            product["alert_reason"] = "Estoque zerado" if stock == 0 else f"Saldo {stock} / ponto de reposicao {reorder_point}"
            del product["units_7d"]
        batches = rows(cursor, """
            SELECT bb.id, bb.product_id, p.name AS product, bb.available_quantity, bb.expires_on
            FROM batch_balance bb JOIN product p ON p.id=bb.product_id
            WHERE bb.expires_on BETWEEN UTC_DATE() AND UTC_DATE() + INTERVAL 7 DAY
              AND bb.available_quantity > 0
            ORDER BY bb.expires_on, bb.id
        """)
        trend = rows(cursor, """
            SELECT DATE(sold_at) AS day, SUM(quantity * unit_price_cents) AS revenue_cents
            FROM sale WHERE sold_at >= UTC_DATE() - INTERVAL 6 DAY
            GROUP BY DATE(sold_at) ORDER BY day
        """)
        categories = rows(cursor, "SELECT id,name,color FROM category ORDER BY id")
        suppliers = rows(cursor, "SELECT id,name FROM supplier ORDER BY id")
        counts = rows(cursor, """
            SELECT (SELECT COUNT(*) FROM customer) AS customers,
                   (SELECT COUNT(*) FROM sale) AS sales,
                   (SELECT COUNT(*) FROM product) AS products
        """)[0]
        events = rows(cursor, """
            SELECT e.kind,e.quantity,e.occurred_at AS at,p.name AS product,
                   COALESCE(e.reason, CONCAT('Lote #',e.batch_id)) AS detail
            FROM stock_event e JOIN batch b ON b.id=e.batch_id
            JOIN product p ON p.id=b.product_id
            ORDER BY e.occurred_at DESC,e.id DESC LIMIT 12
        """)
        entries = rows(cursor, """
            SELECT 'ENTRY' AS kind,b.quantity_received AS quantity,b.received_at AS at,
                   p.name AS product,COALESCE(b.source_ref, CONCAT('Lote #',b.id)) AS detail
            FROM batch b JOIN product p ON p.id=b.product_id
            ORDER BY b.received_at DESC,b.id DESC LIMIT 6
        """)
    category_values = {c["id"]: 0 for c in categories}
    for product in products:
        category_values[product["category_id"]] += product["stock_value_cents"]
    for category in categories:
        category["value_cents"] = category_values[category["id"]]
    recent = sorted(events + entries, key=lambda r: r["at"], reverse=True)[:10]
    metrics = {
        "stock_value_cents": sum(p["stock_value_cents"] for p in products),
        "products_at_risk": sum(p["alert"] in ("out", "low") for p in products),
        "expiring_lots_7d": len(batches),
        "revenue_7d_cents": sum(int(r["revenue_cents"]) for r in trend),
        "customers": counts["customers"], "sales": counts["sales"],
        "products": counts["products"],
    }
    for row in trend:
        row["day"] = row["day"].isoformat()
        row["revenue_cents"] = int(row["revenue_cents"])
    for row in batches:
        row["expires_on"] = row["expires_on"].isoformat()
        row["available_quantity"] = int(row["available_quantity"])
    for row in recent:
        row["at"] = row["at"].isoformat() + "Z"
    return {"metrics": metrics, "products": products, "batches": batches[:12],
            "trend": trend, "category_totals": categories, "recent": recent,
            "categories": categories, "suppliers": suppliers}


def customers(query, page=1, page_size=12):
    query = query.strip()
    if len(query) < 2:
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "pages": 1}
    field = "code" if query.upper().startswith("CLI") else "name"
    with connect() as connection, connection.cursor(dictionary=True) as cursor:
        total = rows(cursor, f"SELECT COUNT(*) AS total FROM customer WHERE {field} LIKE %s", (query + "%",))[0]["total"]
        items = rows(cursor, f"""
            SELECT id,code,name FROM customer WHERE {field} LIKE %s
            ORDER BY id LIMIT %s OFFSET %s
        """, (query + "%", page_size, (page - 1) * page_size))
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": max(1, (total + page_size - 1) // page_size)}


def product_detail(product_id):
    with connect() as connection, connection.cursor(dictionary=True) as cursor:
        product = rows(cursor, """
            SELECT p.*, c.name AS category, s.name AS supplier
            FROM product p JOIN category c ON c.id=p.category_id
            JOIN supplier s ON s.id=p.supplier_id WHERE p.id=%s
        """, (product_id,))
        if not product:
            raise ValueError("Produto nao encontrado")
        batches = rows(cursor, """
            SELECT b.*, b.quantity_received-COALESCE(SUM(e.quantity),0) AS available_quantity
            FROM batch b LEFT JOIN stock_event e ON e.batch_id=b.id
            WHERE b.product_id=%s GROUP BY b.id
            ORDER BY b.received_at DESC,b.id DESC LIMIT 30
        """, (product_id,))
        events = rows(cursor, """
            SELECT e.id,e.batch_id,e.kind,e.quantity,e.sale_id,e.reason,e.occurred_at,
                   s.customer_id,c.name AS customer
            FROM stock_event e JOIN batch b ON b.id=e.batch_id
            LEFT JOIN sale s ON s.id=e.sale_id
            LEFT JOIN customer c ON c.id=s.customer_id
            WHERE b.product_id=%s ORDER BY e.occurred_at DESC,e.id DESC LIMIT 30
        """, (product_id,))
    for batch in batches:
        batch["available_quantity"] = int(batch["available_quantity"])
        batch["expires_on"] = batch["expires_on"].isoformat() if batch["expires_on"] else None
        batch["received_at"] = batch["received_at"].isoformat() + "Z"
    for event in events:
        event["occurred_at"] = event["occurred_at"].isoformat() + "Z"
    return {"product": product[0], "batches": batches, "events": events}


def customer_detail(customer_id):
    with connect() as connection, connection.cursor(dictionary=True) as cursor:
        customer = rows(cursor, "SELECT id,code,name FROM customer WHERE id=%s", (customer_id,))
        if not customer:
            raise ValueError("Cliente nao encontrado")
        summary = rows(cursor, """
            SELECT COUNT(*) AS purchases,COALESCE(SUM(quantity),0) AS units,
                   COALESCE(SUM(quantity*unit_price_cents),0) AS revenue_cents
            FROM sale WHERE customer_id=%s
        """, (customer_id,))[0]
        sales = rows(cursor, """
            SELECT s.id,s.product_id,p.name AS product,s.quantity,s.unit_price_cents,s.sold_at
            FROM sale s JOIN product p ON p.id=s.product_id WHERE s.customer_id=%s
            ORDER BY s.sold_at DESC,s.id DESC LIMIT 20
        """, (customer_id,))
    summary = {key: int(value) for key, value in summary.items()}
    for sale in sales:
        sale["sold_at"] = sale["sold_at"].isoformat() + "Z"
    return {"customer": customer[0], "summary": summary, "sales": sales}


def movements(kind="all", page=1, page_size=20):
    if kind not in ("all", "ENTRY", "SALE", "LOSS"):
        raise ValueError("Filtro de movimentacao invalido")
    with connect() as connection, connection.cursor(dictionary=True) as cursor:
        events = []
        entries = []
        event_total = 0
        entry_total = 0
        fetch_limit = page * page_size
        if kind != "ENTRY":
            filter_sql = "WHERE e.kind=%s" if kind != "all" else ""
            params = (kind,) if kind != "all" else ()
            count_filter = "WHERE kind=%s" if kind != "all" else ""
            event_total = rows(cursor, f"SELECT COUNT(*) AS total FROM stock_event {count_filter}", params)[0]["total"]
            events = rows(cursor, f"""
                SELECT e.id,e.kind,e.quantity,e.occurred_at AS at,p.id AS product_id,
                       p.name AS product,p.sku,b.id AS batch_id,e.sale_id,e.reason,
                       s.customer_id,c.name AS customer,b.unit_cost_cents,
                       s.unit_price_cents
                FROM stock_event e JOIN batch b ON b.id=e.batch_id
                JOIN product p ON p.id=b.product_id
                LEFT JOIN sale s ON s.id=e.sale_id
                LEFT JOIN customer c ON c.id=s.customer_id
                {filter_sql} ORDER BY e.occurred_at DESC,e.id DESC LIMIT %s
            """, params + (fetch_limit,))
        if kind in ("all", "ENTRY"):
            entry_total = rows(cursor, "SELECT COUNT(*) AS total FROM batch")[0]["total"]
            entries = rows(cursor, """
                SELECT b.id,'ENTRY' AS kind,b.quantity_received AS quantity,
                       b.received_at AS at,p.id AS product_id,p.name AS product,p.sku,
                       b.id AS batch_id,NULL AS sale_id,b.source_ref AS reason,
                       NULL AS customer_id,NULL AS customer,b.unit_cost_cents,
                       NULL AS unit_price_cents
                FROM batch b JOIN product p ON p.id=b.product_id
                ORDER BY b.received_at DESC,b.id DESC LIMIT %s
            """, (fetch_limit,))
    result = sorted(events + entries, key=lambda item: (item["at"], item["id"]), reverse=True)
    result = result[(page - 1) * page_size:page * page_size]
    for row in result:
        row["at"] = row["at"].isoformat() + "Z"
    total = event_total + entry_total
    return {"items": result, "total": total, "page": page, "page_size": page_size,
            "pages": max(1, (total + page_size - 1) // page_size)}


def _product_values(data):
    unit = data.get("unit")
    if unit not in ("un", "pct", "cx"):
        raise ValueError("Unidade invalida")
    active = data.get("active", 1)
    if str(active) not in ("0", "1"):
        raise ValueError("Situacao do produto invalida")
    return (label(data, "sku", 3, 30), label(data, "name"),
            integer(data, "category_id", 1), integer(data, "supplier_id", 1),
            unit, integer(data, "min_stock"), integer(data, "lead_days", 1, 90),
            integer(data, "sale_price_cents"), int(active))


def add_product(data):
    values = _product_values(data)
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("""INSERT INTO product
            (sku,name,category_id,supplier_id,unit,min_stock,lead_days,sale_price_cents,active)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""", values)
        identifier = cursor.lastrowid
        connection.commit()
        return identifier


def update_product(product_id, data):
    values = _product_values(data)
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("""UPDATE product SET sku=%s,name=%s,category_id=%s,
            supplier_id=%s,unit=%s,min_stock=%s,lead_days=%s,
            sale_price_cents=%s,active=%s WHERE id=%s""", values + (product_id,))
        if cursor.rowcount == 0:
            cursor.execute("SELECT id FROM product WHERE id=%s", (product_id,))
            if not cursor.fetchone():
                raise ValueError("Produto nao encontrado")
        connection.commit()
    return product_id


def add_receipt(data):
    product_id = integer(data, "product_id", 1)
    quantity = integer(data, "quantity", 1)
    cost = integer(data, "unit_cost_cents")
    expiry = data.get("expires_on") or None
    if expiry:
        try:
            expiry = date.fromisoformat(expiry)
        except (ValueError, TypeError):
            raise ValueError("Data de validade invalida") from None
    source = str(data.get("source_ref", "")).strip() or None
    if source and len(source) > 80:
        raise ValueError("Referencia muito longa")
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("""INSERT INTO batch
            (product_id,quantity_received,unit_cost_cents,expires_on,source_ref)
            VALUES (%s,%s,%s,%s,%s)""", (product_id, quantity, cost, expiry, source))
        identifier = cursor.lastrowid
        connection.commit()
        return identifier


def _consume(data, kind):
    product_id = integer(data, "product_id", 1)
    quantity = integer(data, "quantity", 1)
    customer_id = None
    reason = None
    if kind == "SALE":
        raw = data.get("customer_id")
        customer_id = integer(data, "customer_id", 1) if raw not in (None, "") else None
    else:
        reason = label(data, "reason", 3, 120)
    with connect() as connection:
        connection.start_transaction(isolation_level="READ COMMITTED")
        try:
            with connection.cursor(dictionary=True) as cursor:
                product = rows(cursor, "SELECT id,sale_price_cents FROM product WHERE id=%s AND active=1 FOR UPDATE", (product_id,))
                if not product:
                    raise ValueError("Produto nao encontrado")
                if customer_id is not None and not rows(cursor, "SELECT id FROM customer WHERE id=%s", (customer_id,)):
                    raise ValueError("Cliente nao encontrado")
                expiry_filter = "AND (b.expires_on IS NULL OR b.expires_on >= UTC_DATE())" if kind == "SALE" else ""
                lots = rows(cursor, f"""
                    SELECT b.id,b.quantity_received-COALESCE(
                      (SELECT SUM(e.quantity) FROM stock_event e WHERE e.batch_id=b.id),0
                    ) AS available
                    FROM batch b WHERE b.product_id=%s {expiry_filter}
                    ORDER BY b.expires_on IS NULL,b.expires_on,b.received_at,b.id
                """, (product_id,))
                if sum(int(lot["available"]) for lot in lots) < quantity:
                    raise ValueError("Estoque insuficiente para esta movimentacao")
                sale_id = None
                if kind == "SALE":
                    cursor.execute("""INSERT INTO sale
                        (product_id,customer_id,quantity,unit_price_cents)
                        VALUES (%s,%s,%s,%s)""", (product_id, customer_id, quantity, product[0]["sale_price_cents"]))
                    sale_id = cursor.lastrowid
                remaining = quantity
                for lot in lots:
                    used = min(remaining, int(lot["available"]))
                    if used <= 0:
                        continue
                    cursor.execute("""INSERT INTO stock_event (batch_id,kind,quantity,sale_id,reason)
                        VALUES (%s,%s,%s,%s,%s)""", (lot["id"], kind, used, sale_id, reason))
                    remaining -= used
                    if remaining == 0:
                        break
                identifier = sale_id if sale_id else cursor.lastrowid
            connection.commit()
            return identifier
        except Exception:
            connection.rollback()
            raise


def add_sale(data):
    return _consume(data, "SALE")


def add_loss(data):
    return _consume(data, "LOSS")
