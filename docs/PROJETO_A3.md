# GIRO — base da defesa da A3

Este texto é um rascunho para revisão do grupo. O enunciado da disciplina está em `C:\Users\gsantana5\Downloads\A3_Analise_de_Dados_e_Big_Data_20260929135523.pdf`.

## 4.1 Problema e proposta

Pequenos comércios perdem vendas por falta de produto e capital por excesso ou vencimento de mercadorias. O GIRO registra entradas por lote, vendas e perdas, e transforma esse histórico em alertas compreensíveis de reposição e validade. O público é o gestor de um mercado de bairro com operação local.

Perguntas de negócio: quais produtos repor, quais lotes vencem em até sete dias, quanto foi vendido por dia, onde está o valor do estoque, quais produtos têm menor cobertura e quais perdas custaram mais. Indicadores: produtos abaixo do ponto de reposição, lotes próximos da validade, valor de estoque a custo, receita de vendas, cobertura em dias e custo das perdas.

## 4.2 Dados e 5 Vs

As fontes do protótipo são cadastros de produtos, fornecedores e categorias, entradas por lote, vendas e perdas registrados pelo operador. A amostra é fictícia. São dados estruturados; não há imagem, dado de cliente ou API externa. Volume atual: poucos registros para apresentação. Hipótese de crescimento: 100 lojas × 500 produtos × 20 movimentações por produto/mês = 1 milhão de movimentações mensais. Esta é uma estimativa de cenário, não uma medição. Velocidade: gravações a cada venda e entrada. Variedade: cadastro, lote, validade e evento. Veracidade: SKU único, chaves estrangeiras, validações e conciliação de saldos. Valor: menos ruptura e perda. O acesso esperado mistura escritas curtas de operação com leituras agregadas do painel.

## 4.3 Escolha do banco

**Escolha: SQLite relacional para a prova de conceito local.** Transações ACID preservam a venda e a baixa de todos os lotes como uma unidade. Chaves estrangeiras e `CHECK` restringem relações e valores. O arquivo único facilita a apresentação sem login ou instalação de servidor. O custo operacional é baixo para uma loja e uma instância. A latência local é adequada ao protótipo, mas a concorrência de muitas lojas não foi testada.

Alternativas consideradas: um banco de documentos flexibilizaria o cadastro, porém exigiria cuidado adicional com relações entre produto, lote, venda e eventos; um banco de séries temporais favoreceria telemetria e análise de eventos, mas não seria o melhor banco transacional principal para cadastro e saldo. PostgreSQL seria a evolução natural para múltiplas lojas, controle de acesso e maior concorrência. CAP não é o critério central de um SQLite em arquivo local e sem cluster distribuído; não se deve fingir uma troca CAP que o protótipo não faz.

## 4.4 Modelo

Modelo conceitual: **categoria** e **fornecedor** classificam o **produto**; um produto recebe vários **lotes**; uma **venda** corresponde a um produto e pode consumir vários lotes por meio de **eventos de estoque**. Eventos também registram perdas com motivo.

Modelo lógico: `category(id,name,color)`, `supplier(id,name)`, `product(id,sku,name,category_id,supplier_id,unit,min_stock,lead_days,sale_price_cents,active)`, `batch(id,product_id,quantity_received,unit_cost_cents,expires_on,source_ref,received_at)`, `sale(id,product_id,quantity,unit_price_cents,sold_at)`, `stock_event(id,batch_id,kind,quantity,sale_id,reason,occurred_at)`.

Modelo físico: inteiros para IDs, quantidades e centavos de real; datas em texto ISO 8601; chaves primárias e estrangeiras; índice único em SKU e referência de entrada; índices por produto/validade, venda/data e evento/lote. `batch_balance` calcula saldo por lote; `product_balance` agrega saldo vendável, custo e unidades próximas da validade. Os registros operacionais ficam normalizados; as visões calculam indicadores, sem copiar saldos para uma coluna que poderia divergir.

### Dicionário resumido

| Campo | Tipo | Descrição e regra |
|---|---|---|
| `product.sku` | TEXT | Identificador comercial único, obrigatório |
| `product.name` | TEXT | Nome com 3 a 80 caracteres |
| `product.category_id`, `supplier_id` | INTEGER | FKs obrigatórias |
| `product.unit` | TEXT | `un`, `kg`, `pct` ou `cx` |
| `product.min_stock` | INTEGER | Piso de estoque, não negativo |
| `product.lead_days` | INTEGER | Prazo de reposição entre 1 e 90 dias |
| `product.sale_price_cents` | INTEGER | Preço atual em centavos, não negativo |
| `batch.product_id` | INTEGER | FK para produto |
| `batch.quantity_received` | INTEGER | Quantidade de entrada, positiva |
| `batch.unit_cost_cents` | INTEGER | Custo na entrada, snapshot em centavos |
| `batch.expires_on` | TEXT | Validade ISO, opcional; entrada vencida rejeitada pela API |
| `batch.source_ref` | TEXT | Referência opcional e única para evitar duplicidade |
| `sale.product_id`, `quantity` | INTEGER | Produto e quantidade vendida, positivos |
| `sale.unit_price_cents` | INTEGER | Preço da venda preservado como snapshot |
| `stock_event.batch_id`, `sale_id` | INTEGER | FKs para lote e venda; `sale_id` só em evento de venda |
| `stock_event.kind`, `quantity`, `reason` | TEXT, INTEGER, TEXT | Tipo `SALE` ou `LOSS`, quantidade positiva; perda exige motivo |

Os demais campos `id`, `received_at`, `sold_at` e `occurred_at` são chaves primárias ou carimbos de tempo obrigatórios. O esquema SQL contém a definição completa.

## 4.5 Qualidade e governança

Entrada exige produto ativo, quantidade positiva, custo válido e validade não passada. SKU e referência de entrada são únicos. Venda e perda usam transação de escrita; a escolha de lotes segue a validade mais próxima. Um gatilho proíbe consumir além da quantidade recebida, mesmo se alguém escrever SQL diretamente. As visões permitem conciliar o saldo; `sql/consultas/07_qualidade.sql` identifica lote negativo ou divergência entre venda e eventos.

O fluxo é operacional em tempo real: formulário → validação da API → transação SQLite → tabelas normalizadas → visões/consultas → painel. Não há ETL externo nesta versão. O protótipo não coleta dados pessoais de clientes. No uso real, cadastro de operadores exigiria base legal, minimização, controle de acesso, trilha de auditoria e política de retenção conforme LGPD. O servidor local escuta apenas em `127.0.0.1`. O arquivo SQLite deve ser copiado com mecanismo de backup consistente quando o banco estiver em uso; para múltiplas lojas, migrar para serviço de banco com autenticação, backups automáticos e permissões por loja.

## 4.6 Prova de conceito

Os arquivos do banco e da amostra estão em `sql/`. As seis consultas de negócio ficam em `sql/consultas/01_*.sql` até `06_*.sql`; a sétima consulta verifica qualidade. **Ainda falta executar, registrar os resultados e capturar evidências**, por orientação do usuário de não rodar a aplicação nesta etapa. Não afirmar no pitch que a prova de conceito foi validada antes dessa etapa.

## 4.7 Limites e crescimento 100×

SQLite é conveniente para uma operação local, mas a escrita concorrente e o controle de acesso seriam limites ao multiplicar lojas. O plano é migrar o mesmo modelo relacional para PostgreSQL, identificar cada loja, particionar eventos por período quando o volume justificar e criar agregados analíticos separados do caminho transacional. Precisaremos medir carga antes de escolher particionamento ou réplica. A fórmula de reposição é uma regra simples de sete dias: não captura sazonalidade, promoções ou incerteza. O aprendizado técnico a defender é que o saldo confiável vem da modelagem e das transações, e só então os alertas ficam úteis.

## Roteiro curto de demonstração, depois dos testes

1. Mostrar um produto em risco e explicar o ponto de reposição.
2. Registrar entrada de um lote e mostrar saldo e valor mudando.
3. Registrar venda e explicar a baixa pela validade mais próxima.
4. Registrar uma perda com motivo e mostrar rastreabilidade.
5. Abrir as consultas SQL e apresentar resultados reais, inclusive a verificação que deve retornar zero linhas.

Declarar no relatório o uso de IA na redação e no desenvolvimento, com o que cada integrante revisou. Incluir nomes, turma e duração definida pela professora antes da entrega.
