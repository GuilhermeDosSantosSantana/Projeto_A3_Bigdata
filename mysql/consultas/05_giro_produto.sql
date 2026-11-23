-- PN05: cobertura em dias pela média dos últimos sete dias.
USE giro_a3;
WITH demand AS (
  SELECT product_id, SUM(quantity) / 7.0 AS daily_average
  FROM sale WHERE DATE(sold_at) >= UTC_DATE() - INTERVAL 6 DAY
  GROUP BY product_id
)
SELECT pb.sku, pb.name, pb.stock, ROUND(d.daily_average, 2) AS daily_average,
       ROUND(pb.stock / d.daily_average, 1) AS coverage_days
FROM product_balance pb JOIN demand d ON d.product_id = pb.id
WHERE pb.active = 1 AND d.daily_average > 0
ORDER BY coverage_days, pb.name;
