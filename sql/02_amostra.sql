-- Amostra inteiramente ficticia; caracteres repetidos sao identificadores de teste, nao hashes reais.
INSERT INTO lojista VALUES (1,'Mercado Aurora',repeat('a',64),'08:00','20:00',true),(2,'Livraria Horizonte',repeat('b',64),'09:00','18:00',true);
INSERT INTO usuario VALUES (1,1,'demo1@example.invalid','hash-ficticio','LOJISTA'),(2,2,'demo2@example.invalid','hash-ficticio','LOJISTA');
INSERT INTO conta_recebedora VALUES (1,1,repeat('c',64),'Balcao','PRESENCIAL'),(2,1,repeat('d',64),'Online','ECOMMERCE'),(3,2,repeat('e',64),'Balcao','PRESENCIAL');
INSERT INTO pagador VALUES
 (1,1,repeat('1',64),repeat('2',64),'2026-11-01','2026-11-20',4,0),
 (2,1,repeat('3',64),repeat('4',64),'2026-09-02','2026-11-20',4,1),
 (3,1,repeat('5',64),repeat('6',64),'2026-11-16','2026-11-21',3,0),
 (4,2,repeat('1',64),repeat('2',64),'2026-11-20','2026-11-20',1,0);
INSERT INTO cobranca_esperada VALUES (1,2,'TX-ONLINE-1',250,'PED-1','2026-12-01');
INSERT INTO pagamento (id_pagamento,id_conta,id_lojista,id_pagador,psp,end_to_end_id,txid,canal,valor,ocorrido_em,situacao_entrega) VALUES
 (1,1,1,1,'SIMULADO','E-001',null,'PRESENCIAL',45,'2026-11-01 10:00-03','LIBERADA'),
 (2,1,1,1,'SIMULADO','E-002',null,'PRESENCIAL',80,'2026-11-05 11:00-03','LIBERADA'),
 (3,1,1,2,'SIMULADO','E-003',null,'PRESENCIAL',5,'2026-11-18 13:00-03','LIBERADA'),
 (4,1,1,2,'SIMULADO','E-004',null,'PRESENCIAL',600,'2026-11-18 13:12-03','RETIDA'),
 (5,2,1,1,'SIMULADO','E-005','TX-ONLINE-1','ECOMMERCE',250,'2026-11-19 15:00-03','LIBERADA'),
 (6,1,1,3,'SIMULADO','E-006',null,'PRESENCIAL',180,'2026-11-19 22:00-03','RETIDA'),
 (7,1,1,2,'SIMULADO','E-007',null,'PRESENCIAL',900,'2026-11-20 09:00-03','RETIDA'),
 (8,3,2,4,'SIMULADO','E-008',null,'PRESENCIAL',35,'2026-11-20 10:00-03','LIBERADA'),
 (9,1,1,3,'SIMULADO','E-009',null,'PRESENCIAL',3,'2026-11-21 11:00-03','LIBERADA'),
 (10,1,1,3,'SIMULADO','E-010',null,'PRESENCIAL',120,'2026-11-21 11:15-03','RETIDA'),
 (11,1,1,1,'SIMULADO','E-011',null,'PRESENCIAL',70,'2026-11-20 16:00-03','LIBERADA'),
 (12,1,1,2,'SIMULADO','E-012',null,'PRESENCIAL',250,'2026-09-02 12:00-03','CONTESTADA');
INSERT INTO regra (id_regra,codigo,versao,descricao,peso) VALUES
 (1,'RN09',1,'Contestacao previa na loja',40),(2,'RN05',1,'Nome divergente para documento',35),
 (3,'RN08',1,'Sonda ate R$5 antes de valor 20x',30),(4,'RN04',1,'Novo e acima do p95',25),
 (5,'RN06',1,'Tres pagamentos em dez minutos',25),(6,'RN07',1,'Acima do p99',15),
 (7,'RN12',1,'Multiplas contas do lojista',15),(8,'RN11',1,'Rajada na loja',12),
 (9,'RN10',1,'Fora do horario',10);
INSERT INTO analise_risco (id_analise,id_pagamento,veredito,score,degradada,latencia_ms,versao_catalogo,analisado_em) VALUES
 (1,1,'APROVADO',0,false,85,1,'2026-11-01'),(2,2,'APROVADO',0,false,90,1,'2026-11-05'),
 (3,3,'APROVADO',0,false,120,1,'2026-11-18'),(4,4,'RECUSADO',100,false,240,1,'2026-11-18'),
 (5,5,'APROVADO',0,false,110,1,'2026-11-19'),(6,6,'EM_ANALISE',35,false,190,1,'2026-11-19'),
 (7,7,'RECUSADO',75,false,280,1,'2026-11-20'),(8,8,'APROVADO',0,false,75,1,'2026-11-20'),
 (9,9,'APROVADO',0,false,95,1,'2026-11-21'),(10,10,'EM_ANALISE',55,false,205,1,'2026-11-21'),
 (11,11,'APROVADO',0,false,100,1,'2026-11-20'),(12,12,'APROVADO',0,false,140,1,'2026-09-02');
-- Uma linha por regra e analise, inclusive quando a regra nao dispara.
INSERT INTO sinal_apurado(id_analise,id_regra,disparou,contribuicao)
SELECT a.id_analise,r.id_regra,
  CASE WHEN a.id_analise IN (4,7) AND r.codigo IN ('RN09','RN05') THEN true
       WHEN a.id_analise IN (4,10) AND r.codigo='RN08' THEN true
       WHEN a.id_analise=6 AND r.codigo IN ('RN04','RN10') THEN true
       WHEN a.id_analise=10 AND r.codigo='RN04' THEN true ELSE false END,
  CASE WHEN (a.id_analise IN (4,7) AND r.codigo IN ('RN09','RN05'))
         OR (a.id_analise IN (4,10) AND r.codigo='RN08')
         OR (a.id_analise=6 AND r.codigo IN ('RN04','RN10'))
         OR (a.id_analise=10 AND r.codigo='RN04') THEN r.peso ELSE 0 END
FROM analise_risco a CROSS JOIN regra r;
INSERT INTO alerta VALUES (1,4,'FECHADO','2026-11-18 13:13-03','2026-11-18 14:00-03'),(2,6,'ABERTO','2026-11-19 22:01-03',null),(3,7,'FECHADO','2026-11-20 09:01-03','2026-11-20 09:25-03'),(4,10,'ABERTO','2026-11-21 11:16-03',null);
INSERT INTO desfecho VALUES (1,1,'FRAUDE','Simulacao de contestacao','2026-11-18 14:00-03'),(2,3,'FRAUDE','Simulacao de contestacao','2026-11-20 09:25-03');
INSERT INTO devolucao VALUES (1,12,'MED',250,'CONCLUIDA','2026-11-17', '2026-11-18');
INSERT INTO notificacao VALUES (1,1,1,'APP','Recebido R$45,00. Aprovado.','2026-11-01 10:01-03');
INSERT INTO auditoria VALUES (1,1,'ALERTA',1,'ROTULOU','demo',repeat('f',64),null,'2026-11-18 14:00-03');
INSERT INTO ingestao_webhook (psp,origem_autenticada,confirmado_na_api,payload,situacao_processamento,recebido_em,expurgar_em)
VALUES ('SIMULADO',true,true,'{"event":"PAYMENT_RECEIVED","id":"fixture-001"}'::jsonb,'PROCESSADO','2026-11-01','2026-11-08');
