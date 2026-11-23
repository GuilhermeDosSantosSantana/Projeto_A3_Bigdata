-- PN02: Quais regras tiveram maior precisao nos casos com rotulo conhecido?
-- Amostra rotulada pequena: resultado demonstrativo, sem validade estatistica.
SELECT r.codigo,
 count(*) FILTER (WHERE s.disparou) AS disparos_rotulados,
 count(*) FILTER (WHERE s.disparou AND d.rotulo='FRAUDE') AS verdadeiros_positivos,
 round(100.0 * count(*) FILTER (WHERE s.disparou AND d.rotulo='FRAUDE') /
       NULLIF(count(*) FILTER (WHERE s.disparou),0),1) AS precisao_pct
FROM regra r JOIN sinal_apurado s USING(id_regra)
JOIN analise_risco a USING(id_analise)
JOIN alerta al USING(id_analise) JOIN desfecho d USING(id_alerta)
GROUP BY r.codigo ORDER BY precisao_pct DESC NULLS LAST,r.codigo;
