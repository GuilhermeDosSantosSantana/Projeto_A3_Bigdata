-- Conferência de qualidade: esta consulta deve retornar zero linhas.
-- Detecta lotes negativos e inconsistências entre vendas e eventos.
SELECT 'lote_negativo' AS issue, CAST(id AS TEXT) AS record_id
FROM batch_balance WHERE available_quantity < 0
UNION ALL
SELECT 'venda_divergente', CAST(s.id AS TEXT)
FROM sale s LEFT JOIN stock_event e ON e.sale_id = s.id
GROUP BY s.id HAVING s.quantity <> COALESCE(SUM(e.quantity), 0);
