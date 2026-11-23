-- Deve retornar zero linhas.
USE giro_a3;
SELECT 'lote_negativo' AS issue, CAST(id AS CHAR) AS record_id
FROM batch_balance WHERE available_quantity < 0
UNION ALL
SELECT 'venda_divergente', CAST(s.id AS CHAR)
FROM sale s LEFT JOIN stock_event e ON e.sale_id = s.id
GROUP BY s.id, s.quantity HAVING s.quantity <> COALESCE(SUM(e.quantity), 0)
UNION ALL
SELECT 'vencido_sem_baixa', CAST(id AS CHAR)
FROM batch_balance WHERE available_quantity > 0 AND expires_on < UTC_DATE();
