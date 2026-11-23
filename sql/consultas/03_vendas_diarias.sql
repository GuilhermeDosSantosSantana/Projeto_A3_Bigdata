-- PN03: Qual foi a receita diária da última semana?
SELECT date(sold_at) AS day, COUNT(*) AS sales,
       SUM(quantity * unit_price_cents) AS revenue_cents
FROM sale
WHERE date(sold_at) >= date('now', '-6 days')
GROUP BY date(sold_at)
ORDER BY day;
