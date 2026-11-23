-- PN07: clientes ficticios com maior receita nos ultimos 30 dias.
USE giro_a3;
SELECT c.code, c.name, COUNT(s.id) AS purchases,
       SUM(s.quantity * s.unit_price_cents) AS revenue_cents
FROM customer c JOIN sale s ON s.customer_id = c.id
WHERE s.sold_at >= UTC_TIMESTAMP() - INTERVAL 30 DAY
GROUP BY c.id, c.code, c.name
ORDER BY revenue_cents DESC, c.code
LIMIT 10;
