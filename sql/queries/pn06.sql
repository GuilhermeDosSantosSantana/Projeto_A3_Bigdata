-- PN06: Quantos dias se passaram entre o Pix e a contestacao MED?
SELECT p.id_pagamento,round(extract(epoch FROM (dv.solicitada_em-p.ocorrido_em))/86400,1) AS dias_ate_med,
       dv.valor
FROM devolucao dv JOIN pagamento p USING(id_pagamento)
WHERE dv.origem='MED' ORDER BY dias_ate_med DESC;
