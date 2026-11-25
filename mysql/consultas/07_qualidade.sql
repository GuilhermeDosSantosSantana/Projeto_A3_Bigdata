-- Deve retornar zero linhas.
USE giro_a3;
SELECT 'lote_negativo' AS issue, CAST(id AS CHAR) AS record_id
FROM batch_balance WHERE available_quantity < 0
UNION ALL
SELECT 'venda_divergente', CAST(s.id AS CHAR)
FROM sale s LEFT JOIN stock_event e ON e.sale_id = s.id
GROUP BY s.id, s.quantity HAVING s.quantity <> COALESCE(SUM(e.quantity), 0)
UNION ALL
SELECT 'venda_lote_incoerente', CAST(e.id AS CHAR)
FROM stock_event e
JOIN sale s ON s.id = e.sale_id
JOIN batch b ON b.id = e.batch_id
WHERE e.kind = 'SALE' AND s.product_id <> b.product_id;
