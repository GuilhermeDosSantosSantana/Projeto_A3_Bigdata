-- PN06: Onde ocorrem perdas e qual o custo registrado?
SELECT p.sku, p.name, e.reason, SUM(e.quantity) AS lost_quantity,
       SUM(e.quantity * b.unit_cost_cents) AS lost_cost_cents
FROM stock_event e
JOIN batch b ON b.id = e.batch_id
JOIN product p ON p.id = b.product_id
WHERE e.kind = 'LOSS'
GROUP BY p.id, e.reason
ORDER BY lost_cost_cents DESC;
