INSERT INTO category(id,name,color) VALUES
 (1,'Mercearia','#6E9F6D'),
 (2,'Frios e laticínios','#7295BB'),
 (3,'Padaria','#DDA46B'),
 (4,'Hortifruti','#B2BC64'),
 (5,'Limpeza','#A88CC5');

INSERT INTO supplier(id,name) VALUES
 (1,'Distribuidora Centro'),
 (2,'Laticínios Serra'),
 (3,'Horta da Cidade'),
 (4,'Pães do Bairro');

INSERT INTO product(id,sku,name,category_id,supplier_id,unit,min_stock,lead_days,sale_price_cents) VALUES
 (1,'LEI-001','Leite integral 1 L',2,2,'un',12,3,699),
 (2,'ARR-002','Arroz branco 5 kg',1,1,'pct',10,5,2490),
 (3,'CAF-003','Café torrado 500 g',1,1,'pct',10,6,1890),
 (4,'PAO-004','Pão integral',3,4,'un',15,1,1290),
 (5,'DET-005','Detergente neutro',5,1,'un',8,7,399),
 (6,'QUE-006','Queijo minas 500 g',2,2,'un',10,3,2190),
 (7,'BAN-007','Banana prata',4,3,'kg',18,2,790),
 (8,'ACU-008','Açúcar cristal 1 kg',1,1,'pct',12,5,499);

INSERT INTO batch(id,product_id,quantity_received,unit_cost_cents,expires_on,source_ref,received_at) VALUES
 (1,1,28,460,date('now','+5 days'),'DEMO-LEITE',datetime('now','-4 days')),
 (2,2,36,1790,NULL,'DEMO-ARROZ',datetime('now','-6 days')),
 (3,3,15,1290,date('now','+140 days'),'DEMO-CAFE',datetime('now','-7 days')),
 (4,4,30,760,date('now','+1 day'),'DEMO-PAO',datetime('now','-1 day')),
 (5,5,34,240,NULL,'DEMO-DETERGENTE',datetime('now','-8 days')),
 (6,6,18,1560,date('now','+2 days'),'DEMO-QUEIJO',datetime('now','-3 days')),
 (7,7,25,410,date('now','+3 days'),'DEMO-BANANA',datetime('now','-2 days')),
 (8,8,42,320,NULL,'DEMO-ACUCAR',datetime('now','-5 days'));

INSERT INTO sale(id,product_id,quantity,unit_price_cents,sold_at) VALUES
 (1,1,9,699,datetime('now','-3 days')),
 (2,2,8,2490,datetime('now','-5 days')),
 (3,3,7,1890,datetime('now','-4 days')),
 (4,4,18,1290,datetime('now','-1 day')),
 (5,5,4,399,datetime('now','-7 days')),
 (6,6,5,2190,datetime('now','-2 days')),
 (7,7,7,790,datetime('now','-1 day')),
 (8,8,3,499,datetime('now','-3 days'));

INSERT INTO stock_event(id,batch_id,kind,quantity,sale_id,reason,occurred_at) VALUES
 (1,1,'SALE',9,1,NULL,datetime('now','-3 days')),
 (2,2,'SALE',8,2,NULL,datetime('now','-5 days')),
 (3,3,'SALE',7,3,NULL,datetime('now','-4 days')),
 (4,4,'SALE',18,4,NULL,datetime('now','-1 day')),
 (5,5,'SALE',4,5,NULL,datetime('now','-7 days')),
 (6,6,'SALE',5,6,NULL,datetime('now','-2 days')),
 (7,7,'SALE',7,7,NULL,datetime('now','-1 day')),
 (8,8,'SALE',3,8,NULL,datetime('now','-3 days')),
 (9,4,'LOSS',2,NULL,'Avaria no transporte',datetime('now','-1 day')),
 (10,6,'LOSS',1,NULL,'Embalagem danificada',datetime('now','-2 days'));
