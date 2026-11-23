-- GIRO: modelo relacional para MySQL 8.4, uma loja.
CREATE DATABASE IF NOT EXISTS giro_a3 CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE giro_a3;

CREATE TABLE IF NOT EXISTS category (
  id BIGINT PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE,
  color CHAR(7) NOT NULL,
  CONSTRAINT ck_category_color CHECK (color REGEXP '^#[0-9A-Fa-f]{6}$')
);

CREATE TABLE IF NOT EXISTS supplier (
  id BIGINT PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS customer (
  id BIGINT PRIMARY KEY,
  code VARCHAR(20) NOT NULL UNIQUE,
  name VARCHAR(80) NOT NULL,
  CONSTRAINT ck_customer_name CHECK (CHAR_LENGTH(TRIM(name)) BETWEEN 3 AND 80)
);

CREATE TABLE IF NOT EXISTS product (
  id BIGINT PRIMARY KEY,
  sku VARCHAR(30) NOT NULL UNIQUE,
  name VARCHAR(80) NOT NULL,
  category_id BIGINT NOT NULL,
  supplier_id BIGINT NOT NULL,
  unit VARCHAR(3) NOT NULL,
  min_stock INT NOT NULL,
  lead_days INT NOT NULL,
  sale_price_cents INT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES category(id),
  CONSTRAINT fk_product_supplier FOREIGN KEY (supplier_id) REFERENCES supplier(id),
  CONSTRAINT ck_product_name CHECK (CHAR_LENGTH(TRIM(name)) BETWEEN 3 AND 80),
  CONSTRAINT ck_product_unit CHECK (unit IN ('un','pct','cx')),
  CONSTRAINT ck_product_min CHECK (min_stock >= 0),
  CONSTRAINT ck_product_lead CHECK (lead_days BETWEEN 1 AND 90),
  CONSTRAINT ck_product_price CHECK (sale_price_cents >= 0),
  CONSTRAINT ck_product_active CHECK (active IN (0,1))
);

CREATE TABLE IF NOT EXISTS batch (
  id BIGINT PRIMARY KEY,
  product_id BIGINT NOT NULL,
  quantity_received INT NOT NULL,
  unit_cost_cents INT NOT NULL,
  expires_on DATE NULL,
  source_ref VARCHAR(80) UNIQUE,
  received_at DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP()),
  CONSTRAINT fk_batch_product FOREIGN KEY (product_id) REFERENCES product(id),
  CONSTRAINT ck_batch_quantity CHECK (quantity_received > 0),
  CONSTRAINT ck_batch_cost CHECK (unit_cost_cents >= 0),
  INDEX ix_batch_product_expiry (product_id, expires_on)
);

CREATE TABLE IF NOT EXISTS sale (
  id BIGINT PRIMARY KEY,
  product_id BIGINT NOT NULL,
  customer_id BIGINT NULL,
  quantity INT NOT NULL,
  unit_price_cents INT NOT NULL,
  sold_at DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP()),
  CONSTRAINT fk_sale_product FOREIGN KEY (product_id) REFERENCES product(id),
  CONSTRAINT fk_sale_customer FOREIGN KEY (customer_id) REFERENCES customer(id),
  CONSTRAINT ck_sale_quantity CHECK (quantity > 0),
  CONSTRAINT ck_sale_price CHECK (unit_price_cents >= 0),
  INDEX ix_sale_product_date (product_id, sold_at),
  INDEX ix_sale_customer_date (customer_id, sold_at)
);

CREATE TABLE IF NOT EXISTS stock_event (
  id BIGINT PRIMARY KEY,
  batch_id BIGINT NOT NULL,
  kind VARCHAR(4) NOT NULL,
  quantity INT NOT NULL,
  sale_id BIGINT NULL,
  reason VARCHAR(120) NULL,
  occurred_at DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP()),
  CONSTRAINT fk_event_batch FOREIGN KEY (batch_id) REFERENCES batch(id),
  CONSTRAINT fk_event_sale FOREIGN KEY (sale_id) REFERENCES sale(id),
  CONSTRAINT ck_event_kind CHECK (kind IN ('SALE','LOSS')),
  CONSTRAINT ck_event_quantity CHECK (quantity > 0),
  CONSTRAINT ck_event_shape CHECK (
    (kind = 'SALE' AND sale_id IS NOT NULL AND reason IS NULL)
    OR (kind = 'LOSS' AND sale_id IS NULL AND reason IS NOT NULL
        AND CHAR_LENGTH(TRIM(reason)) BETWEEN 3 AND 120)
  ),
  INDEX ix_event_batch (batch_id),
  INDEX ix_event_date (occurred_at)
);

CREATE OR REPLACE VIEW batch_balance AS
SELECT b.id, b.product_id, b.quantity_received, b.unit_cost_cents,
       b.expires_on, b.received_at,
       b.quantity_received - COALESCE(e.used_quantity, 0) AS available_quantity
FROM batch b
LEFT JOIN (
  SELECT batch_id, SUM(quantity) AS used_quantity FROM stock_event GROUP BY batch_id
) e ON e.batch_id = b.id;

CREATE OR REPLACE VIEW product_balance AS
SELECT p.id, p.sku, p.name, p.category_id, c.name AS category,
       c.color, p.supplier_id, s.name AS supplier, p.unit,
       p.min_stock, p.lead_days, p.sale_price_cents, p.active,
       COALESCE(x.stock, 0) AS stock,
       COALESCE(x.stock_value_cents, 0) AS stock_value_cents,
       COALESCE(x.expiring_7d, 0) AS expiring_7d
FROM product p
JOIN category c ON c.id = p.category_id
JOIN supplier s ON s.id = p.supplier_id
LEFT JOIN (
  SELECT product_id,
    SUM(CASE WHEN expires_on IS NULL OR expires_on >= UTC_DATE()
        THEN available_quantity ELSE 0 END) AS stock,
    SUM(CASE WHEN expires_on IS NULL OR expires_on >= UTC_DATE()
        THEN available_quantity * unit_cost_cents ELSE 0 END) AS stock_value_cents,
    SUM(CASE WHEN expires_on BETWEEN UTC_DATE() AND UTC_DATE() + INTERVAL 7 DAY
        THEN available_quantity ELSE 0 END) AS expiring_7d
  FROM batch_balance GROUP BY product_id
) x ON x.product_id = p.id;
