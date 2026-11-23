-- PN03: receita por dia, nos últimos sete dias.
USE giro_a3;
SELECT DATE(sold_at) AS day, COUNT(*) AS sales,
       SUM(quantity * unit_price_cents) AS revenue_cents
FROM sale
WHERE DATE(sold_at) >= UTC_DATE() - INTERVAL 6 DAY
GROUP BY DATE(sold_at)
ORDER BY day;
