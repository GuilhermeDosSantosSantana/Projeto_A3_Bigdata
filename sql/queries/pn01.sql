-- PN01: Como os vereditos se distribuem por canal e faixa de valor?
SELECT p.canal, width_bucket(p.valor,0,1000,4) AS faixa, a.veredito,
       count(*) AS pagamentos, sum(p.valor)::numeric(12,2) AS valor_total
FROM pagamento p JOIN analise_risco a USING(id_pagamento)
GROUP BY p.canal,faixa,a.veredito ORDER BY p.canal,faixa,a.veredito;
