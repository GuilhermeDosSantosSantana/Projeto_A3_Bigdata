PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS category (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  color TEXT NOT NULL CHECK (length(color) = 7)
);

CREATE TABLE IF NOT EXISTS supplier (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS product (
  id INTEGER PRIMARY KEY,
  sku TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 3 AND 80),
  category_id INTEGER NOT NULL REFERENCES category(id),
  supplier_id INTEGER NOT NULL REFERENCES supplier(id),
  unit TEXT NOT NULL CHECK (unit IN ('un','kg','pct','cx')),
  min_stock INTEGER NOT NULL CHECK (min_stock >= 0),
  lead_days INTEGER NOT NULL CHECK (lead_days BETWEEN 1 AND 90),
  sale_price_cents INTEGER NOT NULL CHECK (sale_price_cents >= 0),
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
);

CREATE TABLE IF NOT EXISTS batch (
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES product(id),
  quantity_received INTEGER NOT NULL CHECK (quantity_received > 0),
  unit_cost_cents INTEGER NOT NULL CHECK (unit_cost_cents >= 0),
  expires_on TEXT CHECK (expires_on IS NULL OR expires_on GLOB '????-??-??'),
  source_ref TEXT UNIQUE,
  received_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sale (
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES product(id),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
  sold_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stock_event (
  id INTEGER PRIMARY KEY,
  batch_id INTEGER NOT NULL REFERENCES batch(id),
  kind TEXT NOT NULL CHECK (kind IN ('SALE','LOSS')),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  sale_id INTEGER REFERENCES sale(id),
  reason TEXT,
  occurred_at TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK ((kind = 'SALE' AND sale_id IS NOT NULL AND reason IS NULL)
      OR (kind = 'LOSS' AND sale_id IS NULL AND length(trim(reason)) BETWEEN 3 AND 120))
);

CREATE INDEX IF NOT EXISTS ix_batch_product_expiry ON batch(product_id, expires_on);
CREATE INDEX IF NOT EXISTS ix_event_batch ON stock_event(batch_id);
CREATE INDEX IF NOT EXISTS ix_sale_product_date ON sale(product_id, sold_at);
CREATE INDEX IF NOT EXISTS ix_event_date ON stock_event(occurred_at);

CREATE TRIGGER IF NOT EXISTS trg_event_prevent_negative_stock
BEFORE INSERT ON stock_event
WHEN NEW.quantity + COALESCE((SELECT SUM(quantity) FROM stock_event WHERE batch_id = NEW.batch_id), 0)
     > (SELECT quantity_received FROM batch WHERE id = NEW.batch_id)
BEGIN
  SELECT RAISE(ABORT, 'batch stock cannot be negative');
END;

CREATE TRIGGER IF NOT EXISTS trg_sale_batch_same_product
BEFORE INSERT ON stock_event
WHEN NEW.kind = 'SALE' AND
     (SELECT product_id FROM sale WHERE id = NEW.sale_id) <> (SELECT product_id FROM batch WHERE id = NEW.batch_id)
BEGIN
  SELECT RAISE(ABORT, 'sale and batch product mismatch');
END;

CREATE VIEW IF NOT EXISTS batch_balance AS
SELECT b.id, b.product_id, b.quantity_received, b.unit_cost_cents,
       b.expires_on, b.received_at,
       b.quantity_received - COALESCE(e.used_quantity, 0) AS available_quantity
FROM batch b
LEFT JOIN (
  SELECT batch_id, SUM(quantity) AS used_quantity
  FROM stock_event
  GROUP BY batch_id
) e ON e.batch_id = b.id;

CREATE VIEW IF NOT EXISTS product_balance AS
SELECT p.id, p.sku, p.name, p.category_id, c.name AS category,
       c.color, p.supplier_id, s.name AS supplier, p.unit,
       p.min_stock, p.lead_days, p.sale_price_cents, p.active,
       COALESCE(SUM(CASE WHEN bb.expires_on IS NULL OR date(bb.expires_on) >= date('now')
                         THEN bb.available_quantity ELSE 0 END), 0) AS stock,
       COALESCE(SUM(CASE WHEN bb.expires_on IS NULL OR date(bb.expires_on) >= date('now')
                         THEN bb.available_quantity * bb.unit_cost_cents ELSE 0 END), 0) AS stock_value_cents,
       COALESCE(SUM(CASE WHEN bb.expires_on IS NOT NULL
                          AND date(bb.expires_on) BETWEEN date('now') AND date('now', '+7 days')
                         THEN bb.available_quantity ELSE 0 END), 0) AS expiring_7d
FROM product p
JOIN category c ON c.id = p.category_id
JOIN supplier s ON s.id = p.supplier_id
LEFT JOIN batch_balance bb ON bb.product_id = p.id
GROUP BY p.id;
