-- PN03: Qual a latencia mediana e nos percentis 95 e 99?
SELECT count(*) AS analises,
 round(percentile_cont(0.50) WITHIN GROUP (ORDER BY latencia_ms)::numeric,1) AS p50_ms,
 round(percentile_cont(0.95) WITHIN GROUP (ORDER BY latencia_ms)::numeric,1) AS p95_ms,
 round(percentile_cont(0.99) WITHIN GROUP (ORDER BY latencia_ms)::numeric,1) AS p99_ms
FROM analise_risco;
