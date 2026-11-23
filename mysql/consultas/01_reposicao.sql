-- PN01: produtos abaixo do ponto de reposição.
USE giro_a3;
WITH demand AS (
  SELECT product_id, SUM(quantity) / 7.0 AS daily_average
  FROM sale WHERE DATE(sold_at) >= UTC_DATE() - INTERVAL 6 DAY
  GROUP BY product_id
), threshold AS (
  SELECT pb.*, COALESCE(d.daily_average, 0) AS daily_average,
    GREATEST(pb.min_stock, CEIL(COALESCE(d.daily_average, 0) * (pb.lead_days + 2))) AS reorder_point
  FROM product_balance pb LEFT JOIN demand d ON d.product_id = pb.id
  WHERE pb.active = 1
)
SELECT sku, name, stock, min_stock, lead_days,
       ROUND(daily_average, 2) AS daily_average, reorder_point
FROM threshold WHERE stock <= reorder_point
ORDER BY stock - reorder_point, name;
