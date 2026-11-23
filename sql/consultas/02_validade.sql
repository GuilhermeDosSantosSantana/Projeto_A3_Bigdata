-- PN02: Quais lotes com saldo vencem nos próximos 7 dias?
SELECT p.sku, p.name, bb.id AS batch_id, bb.available_quantity,
       bb.expires_on, CAST(julianday(bb.expires_on) - julianday(date('now')) AS INTEGER) AS days_left
FROM batch_balance bb JOIN product p ON p.id = bb.product_id
WHERE bb.available_quantity > 0
  AND date(bb.expires_on) BETWEEN date('now') AND date('now', '+7 days')
ORDER BY bb.expires_on, p.name;
