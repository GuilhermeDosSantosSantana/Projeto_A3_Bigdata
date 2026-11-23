-- PN07: Como evolui a recorrencia de cada pagador dentro de sua loja?
SELECT p.id_lojista,p.id_pagador,p.id_pagamento,p.ocorrido_em,
       count(*) OVER (PARTITION BY p.id_lojista,p.id_pagador ORDER BY p.ocorrido_em) AS compra_numero,
       a.veredito
FROM pagamento p JOIN analise_risco a USING(id_pagamento)
ORDER BY p.id_lojista,p.id_pagador,p.ocorrido_em;
