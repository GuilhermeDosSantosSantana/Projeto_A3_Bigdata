-- PN05: Em que horario e faixa de valor aparecem os casos de fraude rotulados?
SELECT d.rotulo,extract(hour FROM p.ocorrido_em AT TIME ZONE 'America/Sao_Paulo')::integer AS hora_local,
       width_bucket(p.valor,0,1000,4) AS faixa,count(*) AS pagamentos
FROM pagamento p JOIN analise_risco a USING(id_pagamento)
JOIN alerta al USING(id_analise) JOIN desfecho d USING(id_alerta)
GROUP BY d.rotulo,hora_local,faixa ORDER BY d.rotulo,hora_local,faixa;
