# Como escrever e defender a A3 do GIRO

Este roteiro traduz o **enunciado da professora** (`A3_Analise_de_Dados_e_Big_Data_20260929135523.pdf`) para o projeto GIRO. O enunciado e a lista de exigencias; este arquivo e um guia de redacao para o grupo, nao uma instrução para copiar texto sem revisar. O relatorio editavel e gerado por `scripts/relatorio.py`; a versao entregue esta em `output/pdf/GIRO_relatorio_A3.pdf`.

Antes de entregar, revisem os numeros apos a ultima validacao e declarem onde a IA foi usada e o que foi conferido. Nao afirmem que os clientes da amostra sao reais.

## 4.1 Problema e visao

Escrevam em poucas linhas a dor: ruptura e vencimento custam vendas e geram desperdicio. Definam o publico como gestor de estoque de varejo centralizado. Expliquem o diferencial concreto: conectar lote, validade, venda, reposicao e historico de cliente. Formulem perguntas mensuraveis: o que repor, o que vence, receita por dia, cobertura, perdas e capital parado. Para cada pergunta, indiquem o indicador e a consulta SQL correspondente (`mysql/consultas/`).

## 4.2 Diagnostico dos dados

Identifiquem as fontes internas: produto, categoria, fornecedor, cliente ficticio, lote, venda e evento de estoque. Dados sao estruturados. Percorram os **5 Vs** sem exagerar: o volume e uma amostra sintetica grande; a velocidade da prova de conceito e de transacoes locais; a variedade e de tipos de registro, nao de formatos de arquivo; a veracidade vem de restricoes e conciliacao; o valor esta nas decisoes de reposicao e perdas. Digam que o acesso tem leituras frequentes de painel e escritas curtas. Estimem crescimento como hipotese, distinguindo-o das contagens observadas.

## 4.3 Escolha do banco — Eixo 1 (3 pontos)

Justifiquem **MySQL/InnoDB** com relacoes, chaves estrangeiras, restricoes e transacoes para venda e baixa de lotes. Comparem ao menos duas alternativas: SQLite (simples para prototipo local, limitado como servidor central multiusuario) e PostgreSQL (tambem forte tecnicamente; escolher MySQL pela instalacao, familiaridade e Workbench, sem alegar superioridade medida). Um banco de documentos exigiria tratamento adicional para as relacoes e invariantes. Discutam ACID, custo operacional, consultas, latencia e crescimento. O Redis e **cache**: nao guarda o saldo definitivo nem substitui o MySQL; sua indisponibilidade nao pode impedir uma venda. CAP nao e comparacao util para a instancia unica atual; seria relevante ao desenhar replicacao ou sincronizacao distribuida.

## 4.4 Modelo e organizacao — Eixo 2 (3 pontos)

Mostrem o desenho conceitual (entidades e relacoes), o modelo logico (7 tabelas, PKs/FKs, cardinalidade) e o fisico (`mysql/01_schema.sql`: tipos, indices, CHECK, visoes, gatilho). Usem `docs/dicionario_de_dados_mysql.csv` para explicar campo por campo. Expliquem por que lote tem validade e custo, venda referencia cliente opcional, e evento liga lote a entrada/saida. O saldo e calculado, evitando uma coluna manual que possa divergir. Justifiquem indices usados em busca e historico e a normalizacao dos cadastros. Para crescer, apresentem particionamento/replicacao como avaliacao futura, nao algo ja implementado.

## 4.5 Qualidade e governanca (1,5 ponto)

Descrevam completude (`NOT NULL`), unicidade (SKU e referencia), validade (quantidades, datas), consistencia (FKs, transacao, gatilho contra saldo negativo) e atualidade (movimentacoes refletidas no saldo). O fluxo e: geracao ficticia deterministica -> carga SQL -> tabelas e visoes -> consultas e alertas; na interface, cada operacao entra no MySQL e invalida o cache. Mostrem que a consulta `07_qualidade.sql` retorna zero linhas. Expliquem que os clientes nao possuem dados pessoais reais; para producao, seriam necessarias finalidade, base legal, minimizacao, acesso, retencao e seguranca. Mencionem dump, teste de restauracao e contas locais com permissoes diferentes. Nao publiquem senhas.

## 4.6 Prova de conceito (1 ponto)

Incluam contagens reais de tabelas e **pelo menos cinco** consultas de negocio com resultados interpretados, nao apenas SQL: reposicao, validade, vendas diarias, valor por categoria, cobertura, perdas e clientes. Usem `evidencias/mysql_resultados_consultas.json` e `output/pdf/GIRO_relatorio_A3.pdf`. Mostrem na apresentacao uma mudanca de saldo na interface e a tabela/visao correspondente no Workbench. Os prints em `evidencias/` comprovam a interface, enquanto scripts e resultados comprovam o banco.

## 4.7 Limitacoes e proximos passos

Sejam claros: centro de estoque unico, clientes sinteticos, sem login de operador, sem integracao com caixa, sem benchmark de concorrencia ou desempenho em producao. Em 100 vezes o volume, medir antes de decidir particionamento, agregados e replicas; varios centros exigem identificador de unidade e isolamento. Relatem um aprendizado do grupo, por exemplo que um alerta confiavel depende de saldo e historico consistentes.

## Revisao final e divisao da fala

| Parte | Ponto principal | Prova na tela |
|---|---|---|
| Dor e proposta | Ruptura e desperdicio | Visao geral |
| Banco e alternativas | Integridade e transacoes | DER, esquema no Workbench |
| Modelo e qualidade | Saldo derivado e regras | Dicionario e consulta de qualidade |
| Operacao e resultados | Dados em uso | Entrada, venda, perda e cinco consultas |
| Limites e conclusao | O que falta para producao | PDF e proximos passos |

Todos devem conseguir responder: **por que MySQL?**, **de onde vem o saldo?**, **por que Redis?**, **o que foi medido de verdade?** e **o que ainda falta para producao?** A nota do enunciado privilegia a qualidade da justificativa: banco (3,0), modelo (3,0), governanca (1,5), prova (1,0), problema/inovacao (1,0) e pitch (0,5).
