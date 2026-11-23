-- PN04: Quanto valor foi retido de pagadores com contestacao anterior na loja?
-- Proxy de exposicao evitada, nao prova de perda financeira efetivamente evitada.
SELECT p.id_lojista,count(*) AS pagamentos_retidos,
       sum(p.valor)::numeric(12,2) AS valor_exposto_retido
FROM pagamento p JOIN analise_risco a USING(id_pagamento)
JOIN pagador pg ON pg.id_pagador=p.id_pagador
WHERE a.veredito='RECUSADO' AND pg.qtd_contestacoes>0
GROUP BY p.id_lojista ORDER BY p.id_lojista;
