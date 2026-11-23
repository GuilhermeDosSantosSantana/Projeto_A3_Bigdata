-- PN02: lotes com saldo que vencem em até sete dias.
USE giro_a3;
SELECT p.sku, p.name, bb.id AS batch_id, bb.available_quantity,
       bb.expires_on, DATEDIFF(bb.expires_on, UTC_DATE()) AS days_left
FROM batch_balance bb JOIN product p ON p.id = bb.product_id
WHERE bb.available_quantity > 0
  AND bb.expires_on BETWEEN UTC_DATE() AND UTC_DATE() + INTERVAL 7 DAY
ORDER BY bb.expires_on, p.name;
