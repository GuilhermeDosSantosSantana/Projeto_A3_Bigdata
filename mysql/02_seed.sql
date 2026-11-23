USE giro_a3;
INSERT INTO category(id,name,color) VALUES
 (1,'Mercearia','#6E9F6D'), (2,'Frios e laticinios','#7295BB'),
 (3,'Padaria','#DDA46B'), (4,'Hortifruti','#B2BC64'), (5,'Limpeza','#A88CC5');
INSERT INTO supplier(id,name) VALUES
 (1,'Distribuidora Centro'), (2,'Laticinios Serra'),
 (3,'Horta da Cidade'), (4,'Paes do Bairro');
INSERT INTO customer(id,code,name) VALUES
 (1,'CLI-001','Cliente Ficticio 001'),
 (2,'CLI-002','Cliente Ficticio 002'),
 (3,'CLI-003','Cliente Ficticio 003'),
 (4,'CLI-004','Cliente Ficticio 004'),
 (5,'CLI-005','Cliente Ficticio 005'),
 (6,'CLI-006','Cliente Ficticio 006'),
 (7,'CLI-007','Cliente Ficticio 007'),
 (8,'CLI-008','Cliente Ficticio 008');
INSERT INTO product(id,sku,name,category_id,supplier_id,unit,min_stock,lead_days,sale_price_cents) VALUES
 (1,'LEI-001','Leite integral 1 L',2,2,'un',12,3,699),
 (2,'ARR-002','Arroz branco 5 kg',1,1,'pct',10,5,2490),
 (3,'CAF-003','Cafe torrado 500 g',1,1,'pct',10,6,1890),
 (4,'PAO-004','Pao integral',3,4,'un',15,1,1290),
 (5,'DET-005','Detergente neutro',5,1,'un',8,7,399),
 (6,'QUE-006','Queijo minas 500 g',2,2,'un',10,3,2190),
 (7,'BAN-007','Banana prata bandeja 1 kg',4,3,'pct',18,2,790),
 (8,'ACU-008','Acucar cristal 1 kg',1,1,'pct',12,5,499);
INSERT INTO batch(id,product_id,quantity_received,unit_cost_cents,expires_on,source_ref,received_at) VALUES
 (1,1,28,460,UTC_DATE() + INTERVAL 5 DAY,'DEMO-LEITE',UTC_TIMESTAMP() - INTERVAL 4 DAY),
 (2,2,36,1790,NULL,'DEMO-ARROZ',UTC_TIMESTAMP() - INTERVAL 6 DAY),
 (3,3,15,1290,UTC_DATE() + INTERVAL 140 DAY,'DEMO-CAFE',UTC_TIMESTAMP() - INTERVAL 7 DAY),
 (4,4,30,760,UTC_DATE() + INTERVAL 1 DAY,'DEMO-PAO',UTC_TIMESTAMP() - INTERVAL 1 DAY),
 (5,5,34,240,NULL,'DEMO-DETERGENTE',UTC_TIMESTAMP() - INTERVAL 8 DAY),
 (6,6,18,1560,UTC_DATE() + INTERVAL 2 DAY,'DEMO-QUEIJO',UTC_TIMESTAMP() - INTERVAL 3 DAY),
 (7,7,25,410,UTC_DATE() + INTERVAL 3 DAY,'DEMO-BANANA',UTC_TIMESTAMP() - INTERVAL 2 DAY),
 (8,8,42,320,NULL,'DEMO-ACUCAR',UTC_TIMESTAMP() - INTERVAL 5 DAY);
INSERT INTO sale(id,product_id,customer_id,quantity,unit_price_cents,sold_at) VALUES
 (1,1,1,9,699,UTC_TIMESTAMP() - INTERVAL 3 DAY),
 (2,2,2,8,2490,UTC_TIMESTAMP() - INTERVAL 5 DAY),
 (3,3,3,7,1890,UTC_TIMESTAMP() - INTERVAL 4 DAY),
 (4,4,4,18,1290,UTC_TIMESTAMP() - INTERVAL 1 DAY),
 (5,5,5,4,399,UTC_TIMESTAMP() - INTERVAL 7 DAY),
 (6,6,6,5,2190,UTC_TIMESTAMP() - INTERVAL 2 DAY),
 (7,7,7,7,790,UTC_TIMESTAMP() - INTERVAL 1 DAY),
 (8,8,8,3,499,UTC_TIMESTAMP() - INTERVAL 3 DAY);
INSERT INTO stock_event(id,batch_id,kind,quantity,sale_id,reason,occurred_at) VALUES
 (1,1,'SALE',9,1,NULL,UTC_TIMESTAMP() - INTERVAL 3 DAY),
 (2,2,'SALE',8,2,NULL,UTC_TIMESTAMP() - INTERVAL 5 DAY),
 (3,3,'SALE',7,3,NULL,UTC_TIMESTAMP() - INTERVAL 4 DAY),
 (4,4,'SALE',18,4,NULL,UTC_TIMESTAMP() - INTERVAL 1 DAY),
 (5,5,'SALE',4,5,NULL,UTC_TIMESTAMP() - INTERVAL 7 DAY),
 (6,6,'SALE',5,6,NULL,UTC_TIMESTAMP() - INTERVAL 2 DAY),
 (7,7,'SALE',7,7,NULL,UTC_TIMESTAMP() - INTERVAL 1 DAY),
 (8,8,'SALE',3,8,NULL,UTC_TIMESTAMP() - INTERVAL 3 DAY),
 (9,4,'LOSS',2,NULL,'Avaria no transporte',UTC_TIMESTAMP() - INTERVAL 1 DAY),
 (10,6,'LOSS',1,NULL,'Embalagem danificada',UTC_TIMESTAMP() - INTERVAL 2 DAY);
