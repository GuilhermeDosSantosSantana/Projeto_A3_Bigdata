# Roteiro de defesa do banco GIRO

## Fala inicial (cerca de 90 segundos)

"O GIRO e uma proposta de gestao de estoque para uma operacao varejista centralizada. O problema e saber quando repor produtos, quais lotes vencem e quanto capital esta parado. Escolhemos MySQL porque produto, lote, venda, cliente e baixa formam relacoes que precisam de chaves estrangeiras e transacoes. O saldo nao e digitado manualmente: e derivado das entradas e saidas. Nesta maquina carregamos 2 mil produtos, 500 mil clientes ficticios e 750 mil vendas. Sete consultas respondem perguntas de negocio e uma oitava verifica inconsistencias. A verificacao retornou zero problemas. Tambem testamos a rejeicao de baixa acima do saldo e restauramos o dump em outro esquema. Os dados sao sinteticos; nao afirmamos que essa carga prova desempenho em producao nem reducao real de perdas."

## Demonstracao no Workbench

1. Abra `GIRO A3 - MySQL local`, esquema `giro_a3`, e mostre as 7 tabelas.
2. Rode `SELECT COUNT(*) FROM customer;` e `SELECT COUNT(*) FROM sale;` para mostrar 500.000 e 750.000.
3. Rode `SELECT * FROM product_balance LIMIT 20;` e explique saldo derivado.
4. Abra `mysql/consultas/01_reposicao.sql` para mostrar produtos a repor.
5. Abra `mysql/consultas/02_validade.sql` e `08_clientes.sql` para mostrar lotes e compras.
6. Rode `mysql/consultas/07_qualidade.sql`: resultado esperado e zero linhas.
7. Mostre `docs/dicionario_de_dados_mysql.csv` e `entrega/GIRO_mysql_A3.sql`.

## Perguntas provaveis

**Por que MySQL?** Integridade relacional, transacoes ACID, conexoes simultaneas, permissoes e ferramenta visual. PostgreSQL tambem seria bom; SQLite foi mais simples no prototipo inicial, mas menos alinhado a base centralizada.

**Onde esta a inovacao?** Na combinacao operacional de lote, validade, ponto de reposicao, cobertura e historico por cliente, com explicacoes auditaveis. A formula nao e IA.

**Como impede estoque negativo?** O gatilho trava o lote e recusa evento que ultrapasse a quantidade recebida. A venda real ainda deve ser implementada como transacao que grave venda e baixas juntas.

**A base tem dados pessoais?** Nao. Os clientes sao rotulos `Cliente Ficticio 000001` etc. Em uso real, seriam necessarios finalidade, base legal, minimizacao, acesso e retencao conforme LGPD.

**E se crescer 100 vezes?** Medir carga e concorrencia; estudar particionamento por data, agregados, replicas, arquivamento e isolamento por centro de estoque. A base atual modela um centro.

**O que foi realmente testado?** Contagens das sete tabelas, oito consultas SQL, dicionario comparado ao esquema, rejeicao de saldo negativo, perda sem motivo e cliente inexistente, e restauracao do dump com contagens identicas. O teste nao e um benchmark multiusuario.
