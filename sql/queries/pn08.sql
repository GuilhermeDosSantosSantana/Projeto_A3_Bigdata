-- PN08: Quantos alertas aguardam analise e quanto demora o fechamento?
SELECT al.situacao,count(*) AS alertas,
       round(avg(extract(epoch FROM (al.fechado_em-al.aberto_em))/60)::numeric,1) AS media_minutos_fechamento
FROM alerta al GROUP BY al.situacao ORDER BY al.situacao;
