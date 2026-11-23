-- PN01: Quais produtos precisam de reposição hoje?
-- A média de 7 dias considera dias sem venda no denominador.
WITH demand AS (
  SELECT product_id, SUM(quantity) / 7.0 AS daily_average
  FROM sale WHERE date(sold_at) >= date('now', '-6 days')
  GROUP BY product_id
), threshold AS (
  SELECT pb.*, COALESCE(d.daily_average, 0) AS daily_average,
         MAX(pb.min_stock, CAST(COALESCE(d.daily_average, 0) * (pb.lead_days + 2) + 0.9999 AS INTEGER)) AS reorder_point
  FROM product_balance pb LEFT JOIN demand d ON d.product_id = pb.id
  WHERE pb.active = 1
)
SELECT sku, name, stock, min_stock, lead_days,
       ROUND(daily_average, 2) AS daily_average, reorder_point
FROM threshold WHERE stock <= reorder_point
ORDER BY stock - reorder_point, name;
