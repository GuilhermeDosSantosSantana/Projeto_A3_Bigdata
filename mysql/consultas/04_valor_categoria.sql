-- PN04: capital imobilizado a custo por categoria.
USE giro_a3;
SELECT category, COUNT(*) AS products, SUM(stock_value_cents) AS value_cents
FROM product_balance WHERE active = 1
GROUP BY category ORDER BY value_cents DESC;
