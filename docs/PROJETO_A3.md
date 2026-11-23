# GIRO - justificativa das escolhas de dados

O banco escolhido para a entrega e **MySQL 8.4/InnoDB**. O modelo relaciona cliente ficticio, venda, produto, lote e baixa de estoque com chaves estrangeiras. O saldo e calculado a partir de entradas menos vendas e perdas, e um gatilho recusa baixa acima do saldo. Os valores monetarios usam centavos inteiros. O campo `sale.customer_id` e opcional para permitir venda anonima; na amostra sintetica, as vendas foram ligadas a clientes ficticios.

MySQL foi escolhido para uma operacao varejista centralizada com multiplas conexoes, usuarios e ferramentas de inspecao. SQLite era conveniente para o prototipo local inicial, mas exigiria outra camada para concorrencia e controle de acesso. PostgreSQL tambem seria uma escolha tecnica defensavel; nao ha benchmark que prove vantagem de MySQL sobre ele neste projeto. Banco de documentos foi descartado como principal porque as relacoes e invariantes transacionais sao centrais. CAP nao diferencia uma instancia unica instalada localmente.

A carga de demonstracao tem 2.000 produtos, 500.000 clientes ficticios, 2.498 lotes, 750.000 vendas e 755.002 eventos. Ela foi gerada artificialmente para testar estrutura e consultas. Esses numeros nao demonstram, sozinhos, desempenho sob usuarios simultaneos ou impacto real em perdas. A regra de reposicao e uma formula simples e explicavel, nao uma previsao de IA.

O dicionario completo, o esquema SQL, as consultas e as evidencias estao nas pastas `docs`, `mysql` e `evidencias`. O relatorio final esta em `output/pdf/GIRO_relatorio_A3.pdf`. Antes da entrega ao professor, o grupo deve preencher integrantes e turma na capa e revisar a defesa oral.
