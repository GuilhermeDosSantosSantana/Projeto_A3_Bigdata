# CONFIA — Checkout Pix com Antifraude para Pequenos Lojistas

**Spec de design** · A3 — Análise de Dados e Big Data (USJT 2026/2)
**Data:** 23/11/2026 · **Status:** aguardando revisão

> O nome **CONFIA** é provisório e pode ser trocado sem impacto no design.

---

## 0. Escopo e o que este documento é

Este é o documento de design que antecede o plano de implementação. Ele cobre o roteiro
inteiro exigido pelo enunciado (seções 4.1 a 4.7) e serve de esqueleto para o relatório em PDF.

**O que vamos construir:** uma camada de checkout Pix com antifraude embutido, demonstrada
dentro de uma loja virtual funcional, com pagamento Pix real via intermediário de pagamento.

**O que NÃO vamos construir:** o trilho de pagamento. Ver seção 1.4 — essa decisão é
deliberada e é um argumento do projeto, não uma limitação dele.

---

## 1. Problema e visão da startup (roteiro 4.1)

### 1.1 A dor

O pequeno lojista brasileiro quer receber por Pix: a tarifa é uma fração da do cartão e o
dinheiro cai na hora. Então ele faz o óbvio — publica a própria chave Pix e pede que o cliente
**mande o comprovante**.

A partir daí ele tem três buracos, e nenhum dos três ele enxerga:

1. **Comprovante falso.** O comprovante de Pix é uma imagem. Falsificar é trivial e existem
   geradores prontos. O lojista confere no olho, despacha a mercadoria, e o dinheiro nunca
   entrou. É o golpe mais comum contra pequeno comércio online no Brasil.
2. **Conferência manual não escala.** Com 30 pedidos por dia, alguém passa a manhã cruzando
   extrato com pedido. Erro humano é certo e o custo é invisível porque está diluído.
3. **Pedido fraudulento com pagamento legítimo.** O pagamento entra de verdade, mas o pedido
   é fraude — triangulação, endereço de laranja, conta de terceiro. O lojista só descobre na
   contestação, quando a mercadoria já foi.

Quem tem porte contrata ClearSale ou similar. Quem fatura R$ 30 mil por mês não tem acesso,
não tem time de dados, e absorve a perda como "custo do negócio".

### 1.2 Público-alvo

Lojas virtuais de pequeno porte — faturamento entre R$ 20 mil e R$ 500 mil por mês — que já
vendem online e aceitam Pix de forma manual ou semiautomática.

### 1.3 Proposta de valor

Checkout Pix que **confirma sozinho** (webhook do intermediário, nunca imagem de comprovante)
e **classifica o risco do pedido** antes de liberar a separação, devolvendo veredito auditável
em menos de um segundo.

O lojista deixa de conferir comprovante e passa a tratar só a exceção.

### 1.4 Posicionamento: por que NÃO construímos o trilho de pagamento

Esta é uma decisão de arquitetura e é também um argumento de defesa do projeto.

Para mover dinheiro via Pix é preciso ser **participante do SPI**, o que exige autorização do
Banco Central, conexão à RSFN e certificação ICP-Brasil. Nenhuma empresa que não seja
instituição financeira faz isso — todas contratam um **intermediário de pagamento** (PSP).

Isso não é atalho. É o padrão da indústria, e traz três ganhos concretos:

- **Redução de escopo regulatório.** Não sendo participante do SPI, não precisamos de
  autorização do BACEN.
- **Não custodiamos credencial de pagamento.** Nunca vemos senha, token de conta ou dado de
  cartão. Para cartão isso é o que mantém a loja fora do escopo de PCI-DSS; para Pix é o que
  mantém o cliente fora do nosso banco de dados.
- **Separação de responsabilidade.** O PSP responde pelo trilho; nós respondemos pela
  inteligência. Cada um faz o que sabe.

**Onde o nosso valor está:** não no transporte do dinheiro, mas na decisão sobre o pedido.

### 1.5 O diferencial

Dois pontos, e nenhum deles é "detectar fraude", que já existe:

1. **Antifraude de Pix em e-commerce.** O antifraude de mercado nasceu para cartão, onde o
   instrumento é a resposta do emissor e existe chargeback. No Pix não há emissor para
   consultar e não há estorno automático — o controle tem que ser **o pedido**, não a
   transação. É um recorte diferente, não uma reimplementação.
2. **Acessível a quem hoje não tem.** O público-alvo é exatamente quem está fora do mercado
   de antifraude por preço e por porte.

### 1.6 Perguntas de negócio

| ID | Pergunta |
|----|----------|
| PN01 | Qual a taxa de aprovação, revisão e recusa por período e por faixa de valor? |
| PN02 | Quais pedidos compartilham dispositivo, endereço ou chave Pix — ou seja, quais formam rede de fraude? |
| PN03 | Qual o tempo de decisão (p50/p95/p99) e quantas decisões estouraram o SLA de 1 s? |
| PN04 | Qual regra mais dispara, e qual a taxa de falso-positivo de cada uma? |
| PN05 | Qual o valor financeiro preservado por pedidos recusados e depois confirmados como fraude? |
| PN06 | Quanto tempo passa entre a criação da cobrança Pix e a confirmação efetiva, por faixa de valor? |
| PN07 | Qual o perfil horário e o ticket médio do pedido fraudulento versus o legítimo? |

### 1.7 KPIs

- Taxa de detecção (*recall*) e taxa de falso-positivo
- Latência p99 da decisão (meta: ≤ 800 ms)
- Valor preservado em R$
- Percentual de pedidos que exigiram revisão humana (meta: < 5%)
- Taxa de confirmação automática de pagamento (meta: 100% — zero comprovante manual)

---

## 2. Diagnóstico dos dados (roteiro 4.2)

### 2.1 Fontes

| Fonte | Origem | Natureza |
|---|---|---|
| Pedido, item, cliente, endereço | Interna (checkout) | Estruturada |
| Evento de telemetria do checkout | Interna (front) | Estruturada, alto volume |
| Webhook de confirmação de pagamento | **API do PSP** | Semiestruturada (varia por PSP) |
| Device fingerprint | Biblioteca no browser | Semiestruturada |
| Catálogo de produtos | Interna | Estruturada |
| Reputação de e-mail / domínio | APIs públicas | Semiestruturada |
| Geolocalização aproximada de IP | Base pública | Estruturada |
| Texto livre de endereço e observação | Usuário | **Não estruturada** |

### 2.2 Tipos de dado

- **Estruturados:** pedido, pagamento, ledger, catálogo
- **Semiestruturados:** payload de webhook (cada PSP tem seu formato), fingerprint, respostas
  de enriquecimento
- **Não estruturados:** endereço digitado em texto livre, observação do pedido

### 2.3 Os 5 Vs — com números honestos

**Volume.** A telemetria domina, não o pedido. Uma loja com 300 pedidos/dia gera ~300
registros de pedido, mas ~45.000 eventos de checkout (cada clique, foco de campo, tentativa
de pagamento). Em 12 meses e 50 lojas: **~16 milhões de eventos**. Não é petabyte, e o
relatório vai dizer isso em vez de fingir escala.

**Velocidade.** A decisão acontece com o cliente esperando a tela. Orçamento: **800 ms**.
É o V mais restritivo e é ele que obriga a separar o caminho quente do analítico.

**Variedade.** Quatro naturezas convivendo: relacional do pedido, série temporal da
telemetria, documento irregular do webhook e do fingerprint, grafo da rede de fraude.
O payload do PSP é o caso mais claro — trocar de Asaas para Efí muda o formato inteiro, e
armazenar isso em coluna tipada exigiria migração a cada integração nova.

**Veracidade.** É o eixo central, e aqui é problema técnico de verdade:
- **Rótulo atrasado e incompleto.** A fraude só vira rótulo quando há contestação, e boa
  parte nunca é contestada. A base de avaliação é enviesada por construção.
- **Endereço em texto livre** com abreviação, erro de digitação e CEP incorreto.
- **Fingerprint falsificável** — é sinal, não prova.
- **Webhook duplicado e fora de ordem.** O PSP reentrega em caso de falha. Sem idempotência,
  um pagamento vira dois.

**Valor.** Mensurável em R$ preservado e em horas de conferência manual eliminadas.

### 2.4 Crescimento e padrão de acesso

Três perfis de acesso **incompatíveis entre si**, e é isso que justifica mais de um banco:

| Perfil | Padrão | Exigência |
|---|---|---|
| Caminho de decisão | Leitura pontual, altíssima frequência | Latência < 50 ms |
| Ingestão de telemetria | Escrita sequencial, append-only | Vazão de escrita |
| Analítico (PN01–PN07) | Varredura agregada de milhões de linhas | Throughput, não latência |

Estimativa: ~1,3 M eventos/mês por 50 lojas, crescendo linearmente com o número de lojas.
Leitura domina no caminho quente; escrita domina na ingestão.

---

## 3. Escolha do banco de dados (roteiro 4.3 — Eixo 1)

### 3.1 Alternativas consideradas e descartadas

**Descartada 1 — Tudo em PostgreSQL.**
Tentadora: um motor, uma linguagem, operação simples, ACID em tudo. Foi descartada por dois
motivos concretos. (a) A consulta de rede de fraude — "este pedido está a quantos saltos de
um pedido confirmado como fraude, por dispositivo, endereço ou chave?" — é busca em
profundidade variável; em SQL vira `WITH RECURSIVE` que degrada rápido e fica ilegível.
(b) A carga analítica de varredura competiria pelo mesmo buffer do caminho quente de 800 ms.

**Descartada 2 — Tudo em MongoDB.**
Resolveria bem o webhook e o fingerprint. Falha no núcleo: baixa de estoque e confirmação de
pagamento exigem transação com garantia forte, e `$graphLookup` é limitado em profundidade e
desempenho para a consulta de rede.

**Descartada 3 — Data warehouse como banco único.**
Excelente para PN01–PN07, mas latência de segundos a dezenas de segundos. Incompatível com
decisão síncrona. Fica como **destino** do ELT, não como banco operacional.

### 3.2 Arquitetura escolhida — persistência poliglota

| Store | Papel | O que o obriga a existir |
|---|---|---|
| **PostgreSQL 16** | Pedido, item, pagamento, ledger, decisão, auditoria | Liberar pedido sem pagamento confirmado é inaceitável. ACID inegociável. |
| **TimescaleDB** (extensão do Postgres) | Telemetria de checkout, métrica de decisão | Hypertable particiona por tempo e tem agregado contínuo nativo. Tabela comum degrada nessa cardinalidade. |
| **MongoDB** | Payload do webhook, fingerprint, snapshot do carrinho | Formato muda por PSP e por versão. Coluna tipada exigiria migração a cada integração. |
| **Neo4j** | Rede de fraude: dispositivo, endereço, e-mail, chave compartilhados | Busca em profundidade variável. Em Cypher é uma linha; em SQL é um problema. |
| **Redis** | Sessão de checkout, idempotência de webhook, janela de velocidade, cache de decisão | Caminho quente com orçamento de 800 ms não vai ao disco. |

**Nota de decisão:** mantemos TimescaleDB como *extensão do PostgreSQL*, num só contêiner, em
vez de InfluxDB. Ganhamos série temporal real **sem perder `JOIN`** com as tabelas de pedido —
e essa é, por si, uma alternativa comparada-e-descartada pronta para a defesa.

### 3.3 Teorema CAP

O sistema não escolhe um lado só, e é aí que está o argumento:

| Componente | Escolha | Justificativa |
|---|---|---|
| PostgreSQL (pedido, pagamento) | **CP** | Prefiro recusar a operação a aceitar inconsistência de pagamento |
| Redis (cache de decisão) | **AP** | Cache frio responde mais devagar, não responde errado |
| Neo4j (rede) | **AP com degradação** | Se cair, a regra de rede não pontua e o veredito sai marcado como degradado |
| MongoDB (payload) | **AP** | Perder enriquecimento atrasa análise, não quebra venda |
| TimescaleDB (telemetria) | **AP** | Telemetria é append-only e tolera atraso |

**A consequência arquitetural disso vira regra de negócio (RN03 e RN21):** o veredito é
composto por sinais independentes, tolera sinal ausente, e registra explicitamente qual faltou.

---

## 4. Catálogo de requisitos

### 4.1 Requisitos Funcionais (RF)

| ID | Requisito |
|----|-----------|
| RF01 | Manter catálogo de produtos (CRUD) com preço e estoque |
| RF02 | Montar carrinho e iniciar checkout, capturando telemetria da sessão |
| RF03 | Gerar cobrança Pix via API do intermediário, devolvendo QR Code e copia-e-cola |
| RF04 | Receber e processar webhook de confirmação de pagamento de forma idempotente |
| RF05 | Decidir risco do pedido (APROVAR / REVISAR / RECUSAR) com score e motivos |
| RF06 | Liberar automaticamente o pedido aprovado para separação |
| RF07 | Enfileirar pedido em revisão para triagem humana |
| RF08 | Permitir ao analista rotular o desfecho (FRAUDE / LEGÍTIMO / INCONCLUSIVO) |
| RF09 | Consultar a rede de fraude de um pedido (grafo navegável) |
| RF10 | Manter catálogo de regras versionado, com ativação e simulação |
| RF11 | Coletar device fingerprint no checkout |
| RF12 | Enriquecer pedido com reputação de e-mail, domínio e geolocalização de IP |
| RF13 | Exibir painel analítico respondendo PN01–PN07 |
| RF14 | Gerir consentimento e atender direitos do titular (acesso, correção, eliminação) |
| RF15 | Expor trilha de auditoria imutável de toda decisão |
| RF16 | Solicitar devolução via MED quando a fraude for confirmada após o pagamento |
| RF17 | Gerar massa sintética de pedidos e rede de fraude para demonstração |
| RF18 | Expor API documentada (OpenAPI) consumível por web e app |

### 4.2 Requisitos Não Funcionais (RNF)

| ID | Requisito |
|----|-----------|
| RNF01 | Latência: p99 da decisão ≤ 800 ms; p50 ≤ 150 ms |
| RNF02 | Disponibilidade: degradação graciosa — queda de store não essencial não derruba o checkout |
| RNF03 | Vazão: 200 decisões/s sustentadas em hardware de desenvolvimento |
| RNF04 | Segurança: TLS em trânsito, criptografia em repouso de dado pessoal, segredo fora do código |
| RNF05 | Privacidade: pseudonimização na ingestão; camada analítica nunca recebe dado identificável |
| RNF06 | Auditabilidade: toda decisão reconstruível (versão da regra + sinais + veredito), log append-only |
| RNF07 | Escalabilidade: serviço de decisão sem estado, escalável horizontalmente |
| RNF08 | Observabilidade: métrica, log estruturado e trace distribuído |
| RNF09 | Manutenibilidade: monorepo com contrato de tipos compartilhado, sem duplicação de schema |
| RNF10 | Portabilidade: ambiente completo sobe com um comando (`docker compose up`) |
| RNF11 | Idempotência: reentrega de webhook não produz efeito duplicado |
| RNF12 | Explicabilidade: todo veredito traz os sinais que o compuseram em linguagem humana |
| RNF13 | Conformidade: nenhuma credencial de pagamento trafega ou é armazenada pelo sistema |

### 4.3 Regras de Negócio (RN)

As RN são o núcleo autoral do projeto. Os pesos são calibráveis e versionados (RF10).

**Decisão e composição**

| ID | Regra |
|----|-------|
| RN01 | Orçamento de decisão é 800 ms. Estourado, devolve veredito parcial marcado como DEGRADADO. Timeout interno nunca trava a venda. |
| RN02 | Score de 0 a 100. ≤39 → APROVAR; 40–74 → REVISAR; ≥75 → RECUSAR. |
| RN03 | Sinal ausente não zera o score: renormaliza pelos pesos dos sinais presentes e registra a ausência. |
| RN13 | **Recusa exige dois sinais independentes.** Um sinal sozinho nunca recusa, por mais forte que seja. Evita falso-positivo catastrófico. |
| RN21 | Veredito DEGRADADO tem teto em REVISAR — nunca recusa automaticamente com informação incompleta. |

**Sinais de risco**

| ID | Regra | Peso |
|----|-------|------|
| RN04 | Pagador do Pix difere do titular do pedido (nome ou documento) | +30 |
| RN05 | E-mail criado há menos de 7 dias ou de domínio descartável | +18 |
| RN06 | Pedido a ≤2 saltos de pedido confirmado como fraude (dispositivo, endereço ou chave) | +25 (1 salto) / +12 (2 saltos) |
| RN07 | Valor acima do p95 histórico da loja nos últimos 90 dias | +10 |
| RN08 | Dispositivo associado a ≥3 clientes distintos | +20 |
| RN09 | ≥3 tentativas de checkout em 10 min a partir do mesmo dispositivo | +25 |
| RN10 | Endereço de entrega divergente do endereço de cobrança, em UF diferente | +12 |
| RN11 | Geolocalização do IP incompatível com a UF de entrega | +8 |
| RN12 | Pedido fora da faixa horária habitual da loja (02h–05h) | +8 |
| RN22 | Produto de alta liquidez (eletrônico, celular) acima de 2 unidades | +15 |

**Pagamento**

| ID | Regra |
|----|-------|
| RN14 | Pedido só é liberado com pagamento confirmado **por webhook do PSP**. Comprovante enviado pelo cliente nunca é aceito como prova. |
| RN15 | Cobrança Pix expira em 30 min; expirada, o estoque reservado é devolvido. |
| RN17 | `(psp, id_cobranca_externa)` é único. Reentrega devolve o resultado original sem reprocessar. |
| RN23 | Valor recebido menor que o valor da cobrança não confirma o pedido; gera divergência para tratamento manual. |

**Confiança e maturidade**

| ID | Regra |
|----|-------|
| RN16 | Cliente com ≥3 pedidos entregues sem contestação nos últimos 180 dias tem teto de score 39 — nunca é recusado, salvo se entrar na rede de fraude confirmada. |
| RN18 | Decisão é imutável. Revisão humana gera novo registro vinculado, nunca altera o anterior. |
| RN19 | Rotulagem de desfecho é obrigatória no fechamento do alerta e realimenta a calibração. |
| RN20 | Propagação de marcação de fraude recalcula a vizinhança até 2 saltos de forma assíncrona, fora do caminho quente. |

**Dados e privacidade**

| ID | Regra |
|----|-------|
| RN24 | Dado identificável do pagador recebido no webhook é pseudonimizado (HMAC-SHA256) na ingestão. O valor original nunca é persistido. |
| RN25 | Retenção: pedido e pagamento 5 anos (obrigação fiscal); telemetria bruta 90 dias; camada analítica apenas pseudonimizada. |
| RN26 | Analista vê dado pseudonimizado por padrão. Despseudonimizar exige justificativa registrada e gera evento de auditoria. |

---

## 5. Organização e modelagem dos dados (roteiro 4.4 — Eixo 2)

### 5.1 Modelo conceitual (DER)

Entidades e relacionamentos principais:

```
LOJA (1) ──── (0..*) PRODUTO
LOJA (1) ──── (0..*) PEDIDO
CLIENTE (1) ──── (0..*) PEDIDO
CLIENTE (1) ──── (0..*) ENDERECO
PEDIDO (1) ──── (1..*) ITEM_PEDIDO
PRODUTO (1) ──── (0..*) ITEM_PEDIDO
PEDIDO (1) ──── (0..1) PAGAMENTO
PEDIDO (1) ──── (0..1) DECISAO_RISCO
DECISAO_RISCO (1) ──── (1..*) SINAL_RISCO
REGRA (1) ──── (0..*) SINAL_RISCO
DECISAO_RISCO (1) ──── (0..1) ALERTA
ALERTA (1) ──── (0..1) DESFECHO
CLIENTE (0..*) ──── (0..*) DISPOSITIVO
PEDIDO (1) ──── (0..*) EVENTO_CHECKOUT
```

### 5.2 Modelo lógico — PostgreSQL, normalizado até a 3FN

```
loja          (id_loja PK, nome, cnpj_hash, psp, ativo, criado_em)
cliente       (id_cliente PK, id_loja FK, email_hash, documento_hash, nome_cifrado,
               primeiro_pedido_em, criado_em)
endereco      (id_endereco PK, id_cliente FK, cep, logradouro, numero, complemento,
               bairro, cidade, uf, tipo, normalizado_em)
produto       (id_produto PK, id_loja FK, sku, nome, preco, estoque, alta_liquidez)
pedido        (id_pedido PK, id_loja FK, id_cliente FK, id_endereco_entrega FK,
               id_endereco_cobranca FK, id_dispositivo FK, valor_total, situacao,
               criado_em, liberado_em)
item_pedido   (id_item PK, id_pedido FK, id_produto FK, quantidade, preco_unitario)
pagamento     (id_pagamento PK, id_pedido FK UNIQUE, psp, id_cobranca_externa,
               valor_cobrado, valor_recebido, situacao, criado_em, confirmado_em,
               expira_em, pagador_documento_hash, pagador_nome_hash)
dispositivo   (id_dispositivo PK, fingerprint_hash, primeiro_visto_em, ultimo_visto_em)
regra         (id_regra PK, codigo, versao, descricao, peso, expressao, ativa,
               vigencia_inicio, vigencia_fim)
decisao_risco (id_decisao PK, id_pedido FK UNIQUE, veredito, score, degradada,
               latencia_ms, versao_catalogo, decidido_em)
sinal_risco   (id_sinal PK, id_decisao FK, id_regra FK, disparou, contribuicao, detalhe)
alerta        (id_alerta PK, id_decisao FK UNIQUE, situacao, atribuido_a, aberto_em,
               fechado_em)
desfecho      (id_desfecho PK, id_alerta FK UNIQUE, rotulo, justificativa,
               registrado_por, registrado_em)
consentimento (id_consentimento PK, id_cliente FK, finalidade, base_legal,
               concedido_em, revogado_em)
auditoria     (id_auditoria PK, entidade, id_entidade, acao, ator, payload_hash,
               ocorrido_em)
```

**Prova de 3FN.** (1FN) Todos os atributos são atômicos; endereço foi decomposto em CEP,
logradouro, número, bairro, cidade e UF em vez de texto único. (2FN) Todas as chaves
primárias são simples e artificiais, eliminando dependência parcial; `item_pedido` guarda
`preco_unitario` porque é o preço **no momento da compra**, que é fato próprio do item e não
dependência do produto. (3FN) Não há dependência transitiva: o peso da regra vive em `regra`,
não replicado em `sinal_risco`; o nome do produto não é replicado em `item_pedido`.

### 5.3 Modelo físico — trechos relevantes do DDL

```sql
-- Núcleo transacional
CREATE TABLE pagamento (
    id_pagamento            BIGSERIAL PRIMARY KEY,
    id_pedido               BIGINT NOT NULL UNIQUE REFERENCES pedido(id_pedido),
    psp                     VARCHAR(20) NOT NULL,
    id_cobranca_externa     VARCHAR(120) NOT NULL,
    valor_cobrado           NUMERIC(12,2) NOT NULL CHECK (valor_cobrado > 0),
    valor_recebido          NUMERIC(12,2) CHECK (valor_recebido >= 0),
    situacao                VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    pagador_documento_hash  CHAR(64),
    pagador_nome_hash       CHAR(64),
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmado_em           TIMESTAMPTZ,
    expira_em               TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_pagamento_psp_externo UNIQUE (psp, id_cobranca_externa)  -- RN17
);

-- Série temporal (TimescaleDB)
CREATE TABLE evento_checkout (
    ocorrido_em   TIMESTAMPTZ NOT NULL,
    id_sessao     UUID        NOT NULL,
    id_loja       BIGINT      NOT NULL,
    tipo_evento   VARCHAR(40) NOT NULL,
    atributos     JSONB
);
SELECT create_hypertable('evento_checkout', 'ocorrido_em', chunk_time_interval => INTERVAL '1 day');

-- Agregado contínuo que alimenta RN07 sem varrer dado bruto no caminho quente
CREATE MATERIALIZED VIEW perfil_loja_diario
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', criado_em) AS dia,
       id_loja,
       count(*)                                        AS pedidos,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY valor_total) AS p95_valor
FROM pedido
GROUP BY dia, id_loja;
```

**Nota técnica importante:** uma hypertable do TimescaleDB **não pode ser alvo de chave
estrangeira**. Por isso `evento_checkout` não é referenciada por nenhuma tabela e carrega
`id_sessao` e `id_loja` de forma desnormalizada. Ver 5.6.

### 5.4 Dicionário de dados (núcleo)

**Tabela `pedido`**

| Campo | Tipo | Descrição | Regras |
|---|---|---|---|
| id_pedido | BIGSERIAL | Identificador do pedido | PK |
| id_loja | BIGINT | Loja a que pertence | FK, obrigatório |
| id_cliente | BIGINT | Comprador | FK, obrigatório |
| id_endereco_entrega | BIGINT | Endereço de entrega | FK, obrigatório |
| id_endereco_cobranca | BIGINT | Endereço de cobrança | FK, obrigatório; alimenta RN10 |
| id_dispositivo | BIGINT | Dispositivo do checkout | FK, nulo se telemetria bloqueada |
| valor_total | NUMERIC(12,2) | Soma dos itens | > 0; deve bater com a soma de `item_pedido` |
| situacao | VARCHAR(20) | Estado | AGUARDANDO_PAGAMENTO, PAGO, EM_ANALISE, LIBERADO, RECUSADO, EXPIRADO, CANCELADO |
| criado_em | TIMESTAMPTZ | Abertura do pedido | default `now()` |
| liberado_em | TIMESTAMPTZ | Liberação para separação | nulo até liberar; só preenchido se situacao=LIBERADO |

**Tabela `decisao_risco`**

| Campo | Tipo | Descrição | Regras |
|---|---|---|---|
| id_decisao | BIGSERIAL | Identificador | PK |
| id_pedido | BIGINT | Pedido avaliado | FK, UNIQUE — uma decisão por pedido (RN18) |
| veredito | VARCHAR(10) | Resultado | APROVAR, REVISAR, RECUSAR |
| score | SMALLINT | Pontuação | 0–100 (RN02) |
| degradada | BOOLEAN | Faltou algum sinal | default false; true limita a REVISAR (RN21) |
| latencia_ms | INTEGER | Tempo de decisão | alimenta PN03 e RNF01 |
| versao_catalogo | VARCHAR(20) | Versão das regras usada | obrigatório para reprodutibilidade (RNF06) |
| decidido_em | TIMESTAMPTZ | Momento da decisão | default `now()` |

**Tabela `pagamento`** — campos sensíveis

| Campo | Tipo | Descrição | Regras |
|---|---|---|---|
| pagador_documento_hash | CHAR(64) | HMAC-SHA256 do CPF do pagador | **Nunca o valor original** (RN24) |
| pagador_nome_hash | CHAR(64) | HMAC-SHA256 do nome normalizado | Usado só para comparar com o titular (RN04) |
| valor_recebido | NUMERIC(12,2) | Valor efetivamente creditado | Se < valor_cobrado, não confirma (RN23) |

> O dicionário completo cobre as 15 tabelas e será consolidado no relatório.

### 5.5 Chaves e índices — cada um com consumidor nomeado

| Índice | Consumidor |
|---|---|
| `uq_pagamento_psp_externo (psp, id_cobranca_externa)` | RN17 — idempotência do webhook |
| `pedido (id_cliente, criado_em DESC)` | Histórico do cliente para RN16 |
| `pedido (id_loja, criado_em DESC)` | Painel da loja, PN01 |
| `pedido (situacao) WHERE situacao = 'EM_ANALISE'` | Fila do analista (parcial, pequeno) |
| `cliente (email_hash)` UNIQUE por loja | Deduplicação e RN05 |
| `dispositivo (fingerprint_hash)` UNIQUE | RN08 — dispositivo em várias contas |
| `decisao_risco (decidido_em DESC)` | PN03, painel de latência |
| `evento_checkout (id_sessao, ocorrido_em DESC)` | Reconstrução da sessão; RN09 |

Índice sem consulta que o use é custo de escrita sem retorno — por isso cada linha acima
nomeia quem o consome.

### 5.6 Normalização versus desnormalização

Duas desnormalizações **conscientes**, ambas justificadas:

1. **`evento_checkout` carrega `id_loja`.** Normalizado, viria por `JOIN` com `pedido`. Não
   pode: hypertable não aceita ser alvo de FK, e a consulta analítica varreria milhões de
   linhas para resolver o `JOIN`. Custo: redundância. Benefício: a consulta analítica fica
   viável.
2. **`item_pedido.preco_unitario`.** Parece redundante com `produto.preco`, mas não é — é o
   preço **no momento da compra**. Sem ele, mudar o preço do produto reescreveria o histórico
   de todos os pedidos. Isso é 3FN correta, não desnormalização.

### 5.7 Estratégia de crescimento

- **Particionamento:** `evento_checkout` particionada por dia (chunk do Timescale). Retenção
  automática de 90 dias (RN25) via política nativa.
- **Agregado contínuo:** `perfil_loja_diario` evita varrer dado bruto no caminho quente.
- **Replicação:** réplica de leitura do PostgreSQL dedicada à carga analítica, isolando o
  caminho de decisão.
- **Escala horizontal:** serviço de decisão sem estado (RNF07); o estado quente vive no Redis.
- **Além de 100× :** a 1,6 bilhão de eventos, migrar a camada analítica para store colunar
  dedicado (ClickHouse ou BigQuery) via ELT. Ver seção 10.

---

## 6. Segurança

Tratada explicitamente porque o produto **é** um controle de segurança — e porque um
antifraude é, ele próprio, alvo.

### 6.1 Modelo de ameaça

| Ameaça | Vetor | Controle |
|---|---|---|
| Comprovante falso | Cliente envia imagem forjada | RN14 — comprovante nunca é aceito; só webhook |
| Webhook forjado | Atacante chama nosso endpoint fingindo ser o PSP | Validação de assinatura HMAC do PSP + allowlist de IP + TLS |
| Reentrega / replay | Webhook duplicado | RN17 — chave de idempotência; janela de replay |
| **Vazamento do catálogo de regras** | Insider ou acesso indevido | Regras e pesos têm acesso restrito; leitura é auditada. Quem conhece as regras, evade. |
| **Envenenamento do grafo** | Atacante cria pedidos legítimos para "limpar" um dispositivo | RN16 exige histórico **entregue sem contestação**, não só pedidos criados |
| **Ameaça interna** | Analista marca fraude como legítima | Rotulagem é auditada e atribuída (RN19); divergência estatística por analista é monitorada |
| Enumeração de pedidos | IDs sequenciais | Identificador público é UUID; o BIGSERIAL não sai da API |
| Exfiltração de dado pessoal | Acesso ao banco analítico | Camada analítica só recebe pseudonimizado (RNF05) |

### 6.2 Controles

- **Em trânsito:** TLS em tudo; verificação de assinatura em todo webhook.
- **Em repouso:** criptografia de disco; `nome_cifrado` com chave gerenciada fora do código.
- **Segredos:** variáveis de ambiente e arquivo `.env` fora do versionamento; nenhuma chave de
  API no repositório. O repositório de exemplo traz `.env.example` com valores falsos.
- **Autenticação e autorização:** JWT com papéis — `LOJISTA`, `ANALISTA`, `ADMIN`. O analista
  não vê dado identificável por padrão (RN26).
- **Auditoria:** tabela `auditoria` append-only, sem `UPDATE` nem `DELETE` concedidos à
  aplicação; `payload_hash` encadeado para detectar adulteração.
- **Superfície de pagamento:** nenhuma credencial de pagamento transita pelo sistema (RNF13) —
  o cliente paga no app do próprio banco, nunca em tela nossa.

### 6.3 Decisão de escopo

Para o protótipo usamos **JWT com guards do NestJS**, não Keycloak. Keycloak é a
resposta de produção e está citado na seção 10. Isso é escolha consciente de escopo, declarada.

---

## 7. Qualidade e governança dos dados (roteiro 4.5)

### 7.1 Dimensões de qualidade

| Dimensão | Como é garantida |
|---|---|
| **Completude** | `NOT NULL` nos campos essenciais; pedido sem endereço não é aceito; taxa de fingerprint ausente é monitorada |
| **Consistência** | `valor_total` reconciliado com a soma de `item_pedido`; `valor_recebido` com `valor_cobrado` (RN23) |
| **Unicidade** | `UNIQUE` em `(psp, id_cobranca_externa)`, `email_hash` por loja, `fingerprint_hash` |
| **Validade** | CEP validado por formato e por base pública; UF em domínio fechado; `CHECK` em valores; situação em enum |
| **Atualidade** | `confirmado_em` comparado a `criado_em` (PN06); telemetria com carimbo de origem e de ingestão para medir atraso |

### 7.2 Tratamento de dado sujo e duplicado

Defeitos esperados e seu tratamento:

| Defeito | Tratamento |
|---|---|
| Endereço em texto livre com abreviação e erro | Normalização por CEP contra base pública; `normalizado_em` registra quando |
| CEP inexistente | Pedido entra em REVISAR, não é recusado |
| Webhook duplicado | Idempotência por chave natural (RN17) |
| Webhook fora de ordem | Máquina de estados do pagamento só avança; transição inválida é ignorada e logada |
| Fingerprint ausente (bloqueador de script) | Sinal ausente, score renormalizado (RN03), decisão marcada como degradada |
| E-mail com erro de digitação | Comparação por distância de edição contra e-mails da mesma loja |
| Cliente duplicado | Deduplicação por `email_hash` + `documento_hash` |

**Para a demonstração**, o gerador (RF17) injeta esses defeitos em **quantidade conhecida**.
Isso permite *medir* a eficácia da limpeza em vez de apenas afirmá-la — e produz a evidência
numérica que esta seção pede.

### 7.3 Fluxo de ingestão (ETL/ELT)

```
  [Checkout / Webhook do PSP]
            │  (tempo real)
            ▼
  Validação de schema (Zod) ── rejeito ──> fila de quarentena
            │
            ▼
  Pseudonimização (RN24)  ← aqui o dado identificável morre
            │
            ├──> PostgreSQL   (pedido, pagamento — ACID, síncrono)
            ├──> MongoDB      (payload bruto do webhook, fingerprint)
            ├──> Redis        (estado quente da sessão)
            └──> Redis Stream ──> consumidor assíncrono
                                      ├──> TimescaleDB (telemetria)
                                      └──> Neo4j (nós e arestas da rede)
            │
            ▼  (lote, noturno)
  Agregado contínuo + camada analítica (só pseudonimizado)
```

Híbrido por necessidade: **tempo real** no caminho da decisão (velocidade é requisito), **lote**
no analítico (volume é requisito). A pseudonimização acontece *antes* de qualquer fan-out —
nenhum store a jusante jamais vê o dado original.

### 7.4 LGPD

**Dados pessoais envolvidos:** nome, e-mail, CPF, endereço, IP e identificador de dispositivo
do comprador; nome e CPF parcial do pagador, vindos do webhook.

**Base legal** — e aqui a distinção importa:

| Finalidade | Base legal |
|---|---|
| Executar o pedido e a entrega | **Execução de contrato** (art. 7º, V) — não é consentimento |
| Prevenção à fraude | **Legítimo interesse** (art. 7º, IX), com teste de proporcionalidade documentado |
| Retenção fiscal | **Cumprimento de obrigação legal** (art. 7º, II) |
| Telemetria de comportamento | **Consentimento** (art. 7º, I) — e só esta exige consentimento |

Apoiar tudo em consentimento seria errado e frágil: o titular poderia revogar e inviabilizar a
prevenção à fraude, que é interesse legítimo do controlador.

**Minimização.** Não coletamos data de nascimento, gênero, telefone ou qualquer dado que não
alimente uma RN. Cada campo do dicionário existe porque uma regra o consome.

**Anonimização e pseudonimização.** Pseudonimização irreversível por HMAC na ingestão (RN24).
A camada analítica é anonimizada de fato — agregada, sem identificador.

**Direitos do titular.** RF14 cobre acesso, correção e eliminação. Eliminação respeita a
retenção fiscal de 5 anos (RN25): os dados são bloqueados, não apagados, e o titular é
informado da base legal.

**Segurança.** Seção 6.

**Riscos residuais declarados:** (a) o hash permite *linkage* se o atacante tiver a base de CPFs
e a chave HMAC — mitigado por guarda da chave em cofre separado; (b) o endereço de entrega é
identificável por natureza e não pode ser pseudonimizado sem inviabilizar a entrega.

### 7.5 Backup, acesso e riscos

- **Backup:** dump diário do PostgreSQL com retenção de 30 dias; WAL archiving para
  *point-in-time recovery*. MongoDB e Neo4j são reconstituíveis a partir do PostgreSQL e do
  payload bruto — não são fonte da verdade.
- **Teste de restauração:** restauração verificada, não apenas backup gerado. Backup não
  testado não é backup.
- **Controle de acesso:** papéis distintos no banco — a aplicação não tem `DROP` nem `DELETE`
  em `auditoria`.
- **Riscos:** indisponibilidade do PSP (fila de reconciliação ativa), *label lag* enviesando a
  avaliação (declarado em 10), dependência de API pública de terceiro para enriquecimento
  (degradação graciosa por RN03).

---

## 8. Arquitetura da aplicação — um sistema só

### 8.1 Monorepo TypeScript

Atende diretamente ao requisito de "juntar tudo num sistema só, sem gambiarra":

```
confia/
├── apps/
│   ├── api/          NestJS — API, decisão, ingestão, integração PSP
│   ├── web/          Next.js — vitrine + checkout + console do lojista/analista
│   └── mobile/       (fase 2) React Native / Expo
├── packages/
│   ├── contracts/    Schemas Zod + tipos — FONTE ÚNICA do contrato
│   ├── rules/        Catálogo de regras e motor de score
│   └── db/           Prisma schema + clientes Mongo/Neo4j/Redis
└── docker-compose.yml
```

`packages/contracts` é a peça que elimina a gambiarra: web, app e API importam **o mesmo tipo**.
Um campo renomeado quebra o build dos três, em vez de quebrar em produção.

### 8.2 O site

Duas superfícies distintas, e é importante não confundi-las:

**Vitrine + checkout (o veículo de demonstração)** — catálogo, carrinho, checkout com QR Code
Pix, tela de aguardando pagamento que atualiza sozinha ao chegar o webhook.

**Console (o produto)** — fila de pedidos em análise, detalhe do pedido com os sinais que
compuseram o score em linguagem humana, **explorador do grafo** da rede de fraude, catálogo de
regras com simulação, painel analítico com PN01–PN07, trilha de auditoria.

### 8.3 Contrato de API

Gerado via `@nestjs/swagger` → OpenAPI 3. Versionado em `/api/v1`. Nenhuma lógica de tela no
servidor (RNF09), para que web e app consumam o mesmo contrato.

---

## 9. Prova de conceito (roteiro 4.6)

### 9.1 Ambiente

`docker compose up` sobe PostgreSQL+TimescaleDB, MongoDB, Neo4j, Redis, API e web. Migrations
via Prisma; seed via RF17.

### 9.2 Massa de dados

- **Sintética:** 50 lojas, 8.000 clientes, 25.000 pedidos, ~16 M eventos de checkout em 12
  meses, com **rede de fraude plantada** (anéis compartilhando dispositivo e endereço) e
  defeitos injetados em quantidade conhecida (7.2).
- **Real:** uma cobrança Pix de verdade, paga ao vivo.

### 9.3 Pix real — como fica

O sistema gera a cobrança pela API do intermediário, o pagamento é feito **no app do banco de
quem paga**, e a confirmação chega por webhook. Duas formas de rodar:

| Modo | O que é | Quando usar |
|---|---|---|
| **Sandbox** | Ambiente de homologação do PSP, sem dinheiro real | Desenvolvimento e ensaio |
| **Produção R$ 0,01** | Conta real do PSP, cobranças de um centavo | A demonstração ao vivo |

**Ponto de atenção que resolvemos, não escondemos:** em produção, o webhook traz nome e CPF
reais do pagador, e o enunciado proíbe dado pessoal real no protótipo. A RN24 pseudonimiza na
ingestão — o valor original nunca é persistido. Ou seja, **o próprio controle de minimização
que descrevemos em 7.4 é o que torna a demo conforme**, e isso vira evidência da seção de
governança em vez de problema.

### 9.4 Consultas que respondem às perguntas de negócio

| # | Pergunta | Store | Técnica |
|---|---|---|---|
| 1 | PN01 — aprovação/revisão/recusa por período | PostgreSQL | agregação com `GROUP BY` e faixa de valor |
| 2 | PN02 — rede de fraude de um pedido | **Neo4j** | `MATCH p=(ped)-[*1..2]-(f) WHERE f.fraude` |
| 3 | PN03 — latência p50/p95/p99 | TimescaleDB | `percentile_cont` sobre `latencia_ms` |
| 4 | PN04 — disparo e falso-positivo por regra | PostgreSQL | `sinal_risco` × `desfecho` |
| 5 | PN05 — valor preservado | PostgreSQL | soma de recusados com desfecho FRAUDE |
| 6 | PN06 — tempo até confirmação do Pix | TimescaleDB | `confirmado_em - criado_em` por faixa |
| 7 | PN07 — perfil do pedido fraudulento | TimescaleDB + agregado | histograma horário por rótulo |

### 9.5 Roteiro da demonstração ao vivo

1. Abrir a vitrine. Alguém da turma faz um pedido.
2. Pagar o Pix de R$ 0,01 **pelo celular**, no app do próprio banco.
3. A tela vira sozinha — o webhook chegou. Mostrar no console: score, sinais, **APROVADO**,
   pedido liberado, latência em ms.
4. Fazer um segundo pedido com padrão de fraude (mesmo dispositivo, e-mail novo, entrega em
   outra UF, 3 eletrônicos).
5. **RECUSADO.** Abrir os sinais que dispararam e o grafo mostrando o vínculo com o anel
   plantado.
6. Mostrar a trilha de auditoria da decisão e a reentrega do webhook não duplicando nada.

---

## 10. Limitações e próximos passos (roteiro 4.7)

**Onde a escolha atual pode falhar:**

- **Label lag.** A avaliação do modelo é otimista por construção: só sabemos de fraude que foi
  contestada. Isso é limitação de método, não de implementação, e vale para o mercado inteiro.
- **Volume.** A 100× (1,6 bilhão de eventos), o TimescaleDB no mesmo motor do OLTP deixa de
  ser adequado; a camada analítica migra para store colunar dedicado via ELT.
- **Neo4j como ponto único.** Numa escala maior, a rede exigiria particionamento de grafo —
  problema notoriamente difícil.
- **Regras determinísticas.** São explicáveis e defensáveis, mas não aprendem. O passo natural
  é usar o rótulo de desfecho (RN19) para calibrar pesos — e só então avaliar um modelo.
- **Escopo de autenticação.** JWT no protótipo; Keycloak em produção.
- **Fraude de primeira vez.** Nenhum sinal de rede ajuda contra um fraudador estreante com
  dispositivo limpo. É o limite estrutural da abordagem.

---

## 11. Stack e reuso

Construímos a lógica de domínio; compramos a infraestrutura.

| Necessidade | Solução pronta |
|---|---|
| Trilho Pix | Asaas ou Efí (sandbox e produção) |
| Framework de API | NestJS |
| Web | Next.js |
| ORM relacional | Prisma |
| Grafo | Neo4j + biblioteca GDS |
| Documentos | MongoDB + Mongoose |
| Cache e stream | Redis + ioredis |
| Contrato e validação | Zod |
| Device fingerprint | FingerprintJS (open source) |
| Dados sintéticos BR | Faker |
| Observabilidade | OpenTelemetry + Prometheus + Grafana |
| Infra local | Docker Compose |

**Decisões conscientes de escopo:** sem Kafka (Redis Streams basta nesta escala e poupa um
contêiner); sem Keycloak no protótipo; sem modelo de machine learning (regras explicáveis são
melhores para auditoria do risco e para a arguição).

**O que é autoral:** o catálogo de RN e seus pesos, o orquestrador de decisão com degradação
graciosa, o modelo de dados poliglota, o gerador de população e rede de fraude, e as consultas
analíticas. É sobre isso que os Eixos 1 e 2 são avaliados.

---

## 12. Declaração de uso de IA

Assistente de IA generativa utilizado como apoio na estruturação deste documento de design, na
comparação de alternativas de persistência e na redação. Todas as decisões técnicas, pesos de
regra e modelagem foram revisados e são de domínio da equipe, que responde integralmente por
qualquer estrutura ou linha de código apresentada.

---

## Pendências antes do plano de implementação

1. Escolher o PSP: **Asaas** (só API key; confirmação de pagamento no sandbox é pela interface)
   ou **Efí** (certificado mTLS; simula status via API).
2. Confirmar o nome do produto.
3. Confirmar a data de entrega da A3 de Big Data — o enunciado veio com o cronograma em branco.
