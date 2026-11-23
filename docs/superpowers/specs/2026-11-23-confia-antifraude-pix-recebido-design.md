# CONFIA — Antifraude de Pix Recebido para Lojistas

**Spec de design** · A3 — Análise de Dados e Big Data (USJT 2026/2)
**Data:** 23/11/2026 · **Status:** aguardando revisão
**Substitui:** `2026-11-23-confia-checkout-pix-antifraude-design.md`

> Este documento substitui a versão anterior. O que mudou e por quê está na seção 0.2 —
> leia essa seção primeiro se você já leu a versão antiga.

---

## 0. Escopo

### 0.1 O que é e o que não é

**O que vamos construir:** um serviço que o lojista contrata, que observa os Pix que ele
**recebe**, decide se cada um é confiável antes da entrega da mercadoria, e avisa no celular
dele. Banco de dados único, modelagem defensável, prova de conceito com Pix de verdade em
sandbox.

**O que NÃO vamos construir:**
- o trilho de pagamento (seção 3.1);
- a geração da cobrança (seção 1.5 — decisão deliberada, não limitação);
- front-end nesta etapa. Regra de negócio e banco primeiro; a interface vem depois e à parte.

**O foco declarado:** o enunciado diz que a avaliação é sobre escolher o tipo de banco
adequado e organizar os dados com qualidade — 6,0 dos 10,0 pontos estão nos Eixos 1 e 2.
Este documento foi escrito com esse peso em mente. A seção 3 e a seção 5 são o núcleo.

### 0.2 O que mudou em relação à versão anterior

| Antes | Agora | Motivo |
|---|---|---|
| Persistência poliglota (5 stores) | **PostgreSQL único** | Custo de manutenção e risco de inconsistência. Seção 3. |
| Redis como componente de dia um | Redis como limiar documentado | Nada precisa viver só no cache nesta escala. Seção 3.5. |
| E-commerce como palco | **Loja física (QR da loja) + e-commerce**, mesmo schema | O caso presencial é o real; o e-commerce é atendido pelo mesmo modelo. Seção 5.4. |
| Nós gerávamos a cobrança | **Consumimos evento de pagamento** | O CONFIA entra na confirmação, não na originação. Seção 1.4. |
| Rede de fraude entre lojistas (Neo4j) | **Removida** | Compartilhar sinal entre controladores distintos é LGPD de risco. Seção 7.4. |
| Device fingerprint, geolocalização | **Removidos** | Não existe página nossa no fluxo presencial. Seção 2.2. |
| Recusa segura o pedido | **Recusa devolve o dinheiro** | Decisão de produto. Seção 4.3, RN16. |

A remoção do grafo e do fingerprint **estreita o conjunto de sinais**. O que sobra é
monitoramento transacional comportamental — que é exatamente o que antifraude bancário de
verdade usa. Está declarado como limitação em 10.

---

## 1. Problema e visão (roteiro 4.1)

### 1.1 A dor — e ela não é a que parece

A dor óbvia é o comprovante falso: o cliente mostra um print, o lojista entrega a mercadoria,
o dinheiro nunca entrou. Isso é real e é trivial de resolver — basta confirmar na fonte.

A dor **cara** é outra, e o lojista geralmente não sabe que ela existe:

> **O Pix entra de verdade, a mercadoria sai, e semanas depois o dinheiro é retirado da conta
> do lojista.**

Isso acontece pelo **MED — Mecanismo Especial de Devolução**. Quando alguém é vítima de golpe,
abre contestação no próprio banco, e o valor é debitado de quem recebeu. Se o dinheiro que
pagou a compra era produto de golpe — conta de laranja, vítima induzida a pagar, conta
invadida — o lojista é o elo final: ele recebeu, entregou, e vai ser debitado.

O lojista não tem como saber isso olhando o extrato. O Pix caiu. Está lá, confirmado. A
reversão vem depois, e aí a mercadoria já foi.

**Então o produto não é "confirmar que o Pix entrou". É prever qual Pix vai voltar.**

Essa reformulação é o que dá sentido a tudo: a confirmação resolve o golpe barato e é o piso;
a análise de risco resolve a perda cara e é o produto.

### 1.2 Público-alvo

Lojista de pequeno porte que recebe Pix direto no balcão ou na entrega — loja de bairro,
assistência técnica, revenda de eletrônico, loja de peças, varejo em feira. Faixa de R$ 20 mil
a R$ 500 mil por mês. Já aceita Pix, confere no olho ou no extrato, não tem time de dados.

Quem tem porte contrata antifraude de mercado. Esse público está fora por preço e por porte.

### 1.3 Proposta de valor

Três coisas, nessa ordem:

1. **Confirmação na fonte.** O lojista nunca mais confere comprovante. A confirmação vem do
   PSP, não de imagem enviada pelo cliente.
2. **Veredito de risco antes da entrega.** Em segundos, enquanto o cliente ainda está no
   balcão, o lojista sabe se aquele dinheiro tem perfil de reversão.
3. **Notificação no celular.** O lojista não abre painel. Chega no app: *"Recebido R$ 340,00.
   Aprovado."* ou *"Recebido R$ 2.800,00. Em análise — não entregue ainda."*

### 1.4 Posicionamento: por que não geramos a cobrança

O CONFIA entra **na confirmação**, não na originação. O QR Code continua sendo o da loja — o
estático colado no balcão ou o dinâmico que o sistema do lojista já gera. O cliente escaneia e
paga no app do banco dele, exatamente como já faz hoje.

Três consequências, todas a favor:

- **Zero atrito para o cliente.** Nenhum passo a mais, nenhuma tela nossa, nenhum aprendizado.
  O fluxo que ele já conhece.
- **Zero atrito de implantação.** O lojista não troca de maquininha, não troca de PSP, não
  reescreve o checkout. Ele autoriza o CONFIA a receber os eventos da conta dele.
- **Nunca tocamos em credencial de pagamento.** O cliente paga dentro do app do próprio banco.
  Nós recebemos um aviso do que já aconteceu.

**O que isso custa, declarado:** não temos nenhum sinal antes do pagamento. Sem dispositivo,
sem IP, sem geolocalização, sem comportamento de navegação. A análise é **puramente
transacional**. Ver 2.2 e 10.

### 1.5 Por que não construímos o trilho de pagamento

Para mover dinheiro via Pix é preciso ser participante do SPI: autorização do Banco Central,
conexão à RSFN, certificação ICP-Brasil. Nenhuma empresa fora do sistema financeiro faz isso —
todas contratam um **intermediário de pagamento (PSP)**.

Não é atalho, é o padrão da indústria, e traz ganhos concretos:

- **Redução de escopo regulatório** — não sendo participante do SPI, não dependemos de
  autorização do BACEN.
- **Não custodiamos credencial** — nunca vemos senha, token de conta ou dado de cartão.
- **Separação de responsabilidade** — o PSP responde pelo trilho; nós respondemos pela
  decisão.

### 1.6 O diferencial

Dois pontos, e nenhum é "detectar fraude", que já existe:

1. **O recorte é Pix recebido, não cartão.** Antifraude de mercado nasceu para cartão, onde
   existe autorização prévia do emissor e chargeback. No Pix não há emissor para consultar e a
   liquidação é imediata e irrevogável — a reversão vem depois, pelo MED. O controle não pode
   ser a transação; tem que ser **a entrega**. É um problema de forma diferente.
2. **O recebedor é o cliente, não o pagador.** Antifraude convencional protege quem paga. Aqui
   o contratante é quem recebe, e a perda que importa é a reversão futura. Inverte o sujeito.

### 1.7 Perguntas de negócio

| ID | Pergunta |
|----|----------|
| PN01 | Qual a distribuição de veredito (aprovado / em análise / recusado) por período, canal e faixa de valor? |
| PN02 | Qual regra mais dispara, e qual a precisão de cada uma contra o desfecho rotulado? |
| PN03 | Qual o tempo entre a chegada do webhook e a notificação ao lojista (p50/p95/p99)? |
| PN04 | Quanto em R$ foi preservado por recusas que depois se confirmaram como reversão? |
| PN05 | Qual o perfil de valor e horário do pagamento revertido versus o do pagamento legítimo? |
| PN06 | Quantos dias passam entre o recebimento e a contestação, por faixa de valor? |
| PN07 | Qual a taxa de recorrência do pagador por lojista, e o recorrente reverte menos? |
| PN08 | Quantos pagamentos exigiram análise humana, e qual o tempo médio de fila? |

### 1.8 KPIs

| KPI | Meta |
|---|---|
| Valor preservado (R$ de reversão evitada) | principal |
| Taxa de falso-positivo (recusado e depois legítimo) | < 3% |
| p95 do webhook até a notificação | ≤ 2 s |
| Pagamentos em análise humana | < 5% |
| Confirmação automática (zero comprovante manual) | 100% |

---

## 2. Diagnóstico dos dados (roteiro 4.2)

### 2.1 Fontes

| Fonte | Origem | Natureza |
|---|---|---|
| Evento de Pix recebido | **Webhook do PSP** | Semiestruturada — formato varia por PSP |
| Extrato / consulta de movimentação | API do PSP | Semiestruturada |
| Evento de devolução e contestação (MED) | API do PSP | Semiestruturada |
| Cadastro do lojista e conta recebedora | Interna | Estruturada |
| Catálogo de regras e pesos | Interna | Estruturada |
| Rótulo de desfecho dado pelo analista | Interna | Estruturada |
| Cobrança esperada (só canal e-commerce) | Sistema do lojista | Estruturada |
| `infoPagador` — texto livre que o pagador digita | Pagador | **Não estruturada** |

### 2.2 O que o evento de Pix realmente traz

Isto é importante porque define o teto do que dá para fazer:

| Campo | Disponível | Observação |
|---|---|---|
| `endToEndId` | sim | Identificador único da transação, atribuído pelo BACEN |
| `txid` | às vezes | Presente no QR dinâmico; **vazio no QR estático** |
| valor | sim | |
| horário | sim | |
| nome do pagador | sim | Mascarado parcialmente por alguns PSPs |
| documento do pagador | sim | CPF/CNPJ, frequentemente mascarado |
| `infoPagador` | sim | Texto livre, quase sempre vazio |
| chave recebedora | sim | |
| **dispositivo, IP, geolocalização** | **não** | Não existem no trilho Pix |

Sem dispositivo e sem IP, o conjunto de sinais é **comportamental e transacional**: velocidade,
valor contra o histórico, horário, recorrência, divergência de identidade, histórico de
devolução. É mais estreito que antifraude de e-commerce — e é exatamente o que monitoramento
transacional bancário usa. Declarado em 10.

### 2.3 Tipos de dado

- **Estruturado:** pagamento, análise, sinal, regra, alerta, desfecho, devolução.
- **Semiestruturado:** payload bruto do webhook — o campo que mais varia. Trocar de Asaas para
  Efí muda o formato inteiro, e guardar isso em coluna tipada exigiria migração a cada
  integração nova.
- **Não estruturado:** `infoPagador`.

### 2.4 Os 5 Vs — com números honestos

**Volume.** 50 lojistas × 120 pagamentos/dia ≈ 6 mil/dia ≈ **2,2 milhões de pagamentos/ano**.
Cada pagamento gera 9 linhas em `sinal_apurado` (uma por regra do catálogo, disparando ou não,
porque auditabilidade exige registrar o que **não** disparou) → **~20 milhões de linhas/ano** na
maior tabela. Mais a ingestão bruta, expurgada em 7 dias.

**Não é petabyte, e este relatório diz isso em vez de fingir escala.** O que justifica cuidado
de modelagem aqui não é o volume: é a veracidade e a variedade.

**Velocidade.** O cliente está no balcão esperando a mercadoria. Orçamento: **webhook recebido →
notificação no celular do lojista em p95 ≤ 2 s**. É mais folgado que um checkout síncrono porque
o pagamento já aconteceu — não há tela travada — mas é apertado o bastante para proibir varredura
de dado bruto no caminho da decisão. É o V que obriga o agregado materializado da seção 5.6.

**Variedade.** Payload do PSP em formato que muda por fornecedor e por versão; texto livre do
pagador; núcleo transacional rígido. Três naturezas no mesmo fluxo.

**Veracidade.** É o eixo central e aqui há problema técnico de verdade:

- **Rótulo atrasado, com número.** A contestação por MED pode chegar **até 90 dias** depois do
  recebimento. A base de treino e de avaliação é, por construção, incompleta para tudo que é
  recente. Isso enviesa qualquer métrica de precisão para otimista.
- **Nome mascarado.** Vários PSPs devolvem `J*** S*** S****`. A comparação de identidade opera
  sobre dado parcial.
- **Webhook duplicado e fora de ordem.** O PSP reentrega em falha. Sem idempotência, um
  pagamento vira dois.
- **QR estático não tem `txid`.** Não dá para amarrar o pagamento a uma cobrança específica no
  canal presencial. É limitação do trilho, não do nosso desenho.

**Valor.** Mensurável em R$ de reversão evitada (PN04) e em horas de conferência eliminadas.

### 2.5 Padrão de acesso

| Perfil | Padrão | Exigência |
|---|---|---|
| Decisão (por pagamento) | Leitura pontual + janelas agregadas | Latência — orçamento de 2 s |
| Ingestão de webhook | Escrita, append-only, em rajada | Vazão e idempotência |
| Analítico (PN01–PN08) | Varredura agregada de dezenas de milhões de linhas | Throughput |
| Fila de análise humana | Leitura de subconjunto pequeno e quente | Índice parcial |

Os dois primeiros perfis são atendidos pelo mesmo motor sem conflito nesta escala. O terceiro
é isolado por réplica de leitura (5.7).

---

## 3. Escolha do banco de dados (roteiro 4.3 — Eixo 1)

Esta é a seção de maior peso da avaliação. O argumento tem quatro camadas e elas se sustentam
em ordem.

### 3.1 Primeira camada — o critério que normalmente ninguém declara: custo de operação

A escolha de banco é quase sempre discutida por capacidade técnica. Na prática, o que decide
em produção é **quanto custa manter aquilo funcionando pelos próximos cinco anos.**

Cinco bancos não são cinco tecnologias. São:

- cinco procedimentos de backup e de restauração testada;
- cinco stacks de monitoramento e alerta;
- cinco ciclos de atualização e de correção de CVE;
- cinco conjuntos de modo de falha que alguém precisa conhecer de madrugada;
- e, acima de tudo, **cinco especialistas** — ou um generalista que vai ser raso em todos.

Para o público-alvo deste produto, isso é proibitivo. Um lojista que fatura R$ 80 mil por mês
não sustenta um produto cuja operação exige um time de plataforma.

**Com um motor só, o mesmo orçamento compra uma pessoa muito boa em vez de cinco medianas.**

### 3.2 Segunda camada — e esta é mais forte: correção

O custo é argumento econômico. Há um argumento técnico mais duro embaixo dele.

Não existe transação ACID entre motores heterogêneos. Com N stores, você tem N×(N−1)/2 pares
que podem divergir — com cinco stores, **dez fronteiras de inconsistência**. Cada fronteira
vira job de reconciliação: código que alguém escreve, testa, opera, e que falha calado.

Num sistema que decide sobre dinheiro, isso deixa de ser custo e vira **corretude**:

> "Pagamento gravado no Postgres, sinal de devolução prévia perdido no Mongo" = lojista
> entregou mercadoria que não devia ter entregado.

O argumento de manutenção e o de corretude apontam para o mesmo lado. É por isso que ele é
bom — e é a resposta pronta para *"mas por que você não usou um banco de grafo?"*.

### 3.3 Terceira camada — cobertura: o PostgreSQL dá conta

Argumento de custo sem cobertura técnica é desculpa. Então: cada necessidade, e o recurso
nativo que a atende.

| Necessidade | Recurso do PostgreSQL | Alternativa que seria usada |
|---|---|---|
| Payload de webhook em formato variável | `JSONB` + índice **GIN** | MongoDB |
| Série temporal de pagamentos e sinais | **Particionamento declarativo** por range de data + índice BRIN | TimescaleDB / InfluxDB |
| Agregado pré-calculado do perfil da loja | **Materialized view** + atualização agendada | Continuous aggregate |
| Janela de velocidade (N em M minutos) | **Window function** + índice composto | Redis |
| Percentil do histórico da loja | `percentile_cont` ordenado | Warehouse |
| Relação pagador ↔ loja ↔ conta | `JOIN`; e `WITH RECURSIVE` se a profundidade crescer | Neo4j |
| Idempotência do webhook | `UNIQUE` sobre chave natural — **durável, não volátil** | Redis |
| Busca aproximada sobre o payload bruto (investigação) | `pg_trgm` | Elasticsearch |
| Fila de análise humana | **Índice parcial** sobre o estado quente | Redis / SQS |

O caso do grafo merece nota: **sem compartilhamento de sinal entre lojistas (decisão de 7.4), a
relação pagador↔loja tem profundidade 1.** Isso é um `JOIN`, não um grafo. Não descartamos o
Neo4j por preferência — o problema não tem a forma que justificaria um banco de grafo. Essa é a
diferença entre descartar por opinião e descartar por análise.

### 3.4 Quarta camada — alternativas comparadas e descartadas

**MySQL 8** — é a alternativa séria, e é a que a banca vai perguntar.
Empata em muita coisa: tem window function desde a 8.0, tem particionamento, tem CTE recursiva,
tem JSON. Perde em três pontos que este projeto usa de fato:
1. **Índice sobre JSON.** O GIN do Postgres indexa o documento inteiro para consulta por
   contenção (`@>`). No MySQL é preciso saber de antemão qual caminho indexar e criar coluna
   gerada para cada um. Com payload que varia por PSP, isso vira migração a cada integração.
2. **Índice parcial.** `WHERE situacao = 'EM_ANALISE'` produz um índice minúsculo e quente no
   Postgres. MySQL não tem índice parcial — o índice carrega todas as linhas.
3. **Extensões.** `pg_trgm` para nome mascarado e `pg_cron` para o expurgo saem de graça.

**MongoDB** — resolveria o payload com elegância. Falha no núcleo: a análise depende de
percentil e janela sobre histórico, que no *aggregation framework* é mais verboso e mais lento
do que uma window function; e o registro de pagamento e devolução é exatamente o caso em que
garantia transacional forte não é negociável.

**Banco de grafo (Neo4j)** — descartado pela análise de 3.3: a profundidade real é 1.

**Chave-valor (Redis, DynamoDB) como banco principal** — sem consulta ad hoc não há PN01–PN08.
Inviável como sistema de registro.

**Data warehouse (BigQuery, ClickHouse) como banco único** — latência de segundos a dezenas de
segundos, incompatível com o orçamento de 2 s. Fica como **destino futuro de ELT**, não como
banco operacional. Ver 10.

### 3.5 O Redis e a pergunta "cadê o cache?"

A versão anterior trazia Redis como componente obrigatório. Não é — e a análise honesta mostra
por quê.

Tudo que o Redis faria aqui o Postgres faz: a idempotência vira `UNIQUE` sobre chave natural
(e fica **melhor**, porque é durável e sobrevive a reinício); a janela de velocidade vira
window function sobre índice composto; a expiração vira `pg_cron` apagando linha.

O custo de não ter cache é amplificação de escrita — cada contador vira WAL, *dead tuple* e
vacuum numa linha quente — e uma troca de ~0,1 ms por ~2 ms. **Nesta escala, com orçamento de
2 s, isso não dói.**

Então a posição é: **limiar documentado, não componente de dia um.**

> O Redis entra quando o contador de janela se tornar a linha mais escrita do banco — na
> prática, ao encostar no teto de vazão do RNF03 (200 pagamentos/segundo sustentados), ou
> quando o p95 da apuração de sinais passar de 300 ms, o que vier primeiro.

E se perguntarem "por que não tem cache?": porque ainda não precisa, e está escrito quando vai
precisar. Isso é decisão; o contrário é preferência.

**A regra que fecha o argumento:** um banco é onde o dado nasce; cache é onde ele passa. Se o
cache for apagado, o sistema fica mais lento — nunca errado. **Um sistema de registro só.**

### 3.6 Arquitetura escolhida

| Componente | Papel |
|---|---|
| **PostgreSQL 16** | Sistema de registro único — todas as tabelas, toda a análise |
| Réplica de leitura | Isola a carga analítica do caminho de decisão |
| `pg_cron` | Expurgo de retenção e atualização de agregado |
| *(futuro, com limiar)* Redis | Cache e janela, acima do limiar de 3.5 |
| *(futuro, com limiar)* Store colunar | Camada analítica, acima do limiar de 10 |

### 3.7 Teorema CAP

PostgreSQL em nó único com réplica de leitura é **CP**: diante de partição, prefere recusar a
operação a aceitar escrita inconsistente. É a escolha certa, porque o dado é financeiro —
registrar errado um recebimento é pior do que não registrar.

A disponibilidade é tratada **na aplicação, não no banco**, e isso é desenho explícito:

| Situação | Comportamento |
|---|---|
| Banco indisponível na chegada do webhook | PSP reentrega; o webhook responde 5xx e a reentrega é idempotente por RN17 |
| Agregado de perfil desatualizado | Sinal correspondente não pontua; análise marcada como DEGRADADA (RN03) |
| Análise estourou o orçamento de 2 s | Veredito parcial, teto em EM_ANALISE (RN21) |

**A consequência arquitetural vira regra de negócio** — RN03 e RN21 existem por causa desta
seção, não por acaso.

---

## 4. Catálogo de requisitos

### 4.1 Requisitos Funcionais (RF)

| ID | Requisito |
|----|-----------|
| RF01 | Cadastrar lojista e suas contas recebedoras (CRUD), com faixa de horário de operação |
| RF02 | Receber webhook de Pix recebido do PSP, de forma idempotente e assinada |
| RF03 | Persistir o payload bruto em área de ingestão, com expurgo automático por retenção |
| RF04 | Validar e normalizar o evento para o modelo canônico, qualquer que seja o PSP |
| RF05 | Pseudonimizar o dado identificável do pagador no momento da ingestão |
| RF06 | Apurar os sinais de risco do pagamento e calcular o score |
| RF07 | Emitir veredito (APROVADO / EM_ANALISE / RECUSADO) com motivos em linguagem humana |
| RF08 | Notificar o lojista do recebimento e do veredito |
| RF09 | Enfileirar pagamento em análise para triagem humana |
| RF10 | Permitir ao analista rotular o desfecho (LEGITIMO / FRAUDE / INCONCLUSIVO) |
| RF11 | Solicitar devolução ao PSP quando o veredito for RECUSADO |
| RF12 | Registrar contestação e devolução por MED informada pelo PSP |
| RF13 | Manter catálogo de regras versionado, com ativação, peso e simulação |
| RF14 | Conciliar extrato do PSP contra os pagamentos registrados, apontando divergência |
| RF15 | Registrar cobrança esperada no canal e-commerce, para conferência de valor |
| RF16 | Expor painel analítico respondendo PN01–PN08 |
| RF17 | Expor trilha de auditoria imutável de toda decisão e todo acesso a dado sensível |
| RF18 | Atender direitos do titular (acesso, correção, eliminação) |
| RF19 | Gerar massa sintética de pagamentos, com fraude plantada, para demonstração |
| RF20 | Expor API documentada (OpenAPI) consumível por web e por app |

### 4.2 Requisitos Não Funcionais (RNF)

| ID | Requisito |
|----|-----------|
| RNF01 | Latência: p95 do webhook até a notificação ≤ 2 s; p50 ≤ 500 ms |
| RNF02 | Degradação graciosa: sinal indisponível não impede veredito, apenas o marca |
| RNF03 | Vazão: 200 webhooks/s sustentados em hardware de desenvolvimento |
| RNF04 | Segurança: TLS em trânsito, criptografia em repouso, segredo fora do código |
| RNF05 | Privacidade: pseudonimização na ingestão; camada analítica nunca recebe identificável |
| RNF06 | Auditabilidade: toda decisão reconstruível (versão do catálogo + sinais + veredito) |
| RNF07 | Idempotência: reentrega de webhook não produz efeito duplicado |
| RNF08 | Explicabilidade: todo veredito traz em texto os sinais que o compuseram |
| RNF09 | Isolamento multi-inquilino: lojista nunca acessa dado de outro lojista |
| RNF10 | Portabilidade: ambiente completo sobe com um comando |
| RNF11 | Observabilidade: métrica, log estruturado e trace |
| RNF12 | Manutenibilidade: **um motor de banco**; schema versionado por migration |
| RNF13 | Conformidade: nenhuma credencial de pagamento trafega ou é armazenada |
| RNF14 | Retenção: expurgo automático verificável, não manual |

### 4.3 Regras de Negócio (RN)

O núcleo autoral do projeto. Pesos calibráveis e versionados (RF13).

**Decisão e composição**

| ID | Regra |
|----|-------|
| RN01 | Orçamento de análise: 2 s. Estourado, emite veredito parcial marcado como DEGRADADO. |
| RN02 | Score de 0 a 100, com teto em 100. ≤39 → APROVADO; 40–74 → EM_ANALISE; ≥75 → RECUSADO. |
| RN03 | Sinal indisponível não zera o score: renormaliza pelos pesos dos sinais apurados e registra a ausência. |
| RN14 | **Recusa exige dois sinais independentes.** Nenhum sinal sozinho recusa, por mais forte que seja. |
| RN21 | Veredito DEGRADADO tem teto em EM_ANALISE — nunca recusa com informação incompleta. |

**Sinais de risco** — todos derivados apenas do que o trilho Pix entrega (2.2)

| ID | Sinal | Peso |
|----|-------|------|
| RN04 | Pagador nunca pagou nesta loja **e** valor acima do p95 histórico dela | +25 |
| RN05 | Mesmo documento de pagador já apareceu com nome divergente nesta loja — comparação por hash do nome normalizado (ver nota abaixo) | +35 |
| RN06 | ≥3 pagamentos do mesmo documento para a mesma loja em 10 minutos | +25 |
| RN07 | Valor acima do p99 histórico da loja nos últimos 90 dias | +15 |
| RN08 | Padrão de sonda: pagamento ≤ R$ 5 do mesmo documento nos últimos 30 min, seguido de valor ≥ 20× o primeiro | +30 |
| RN09 | Pagador com devolução ou contestação anterior nesta loja | +40 |
| RN10 | Pagamento fora da faixa de horário de operação declarada pelo lojista | +10 |
| RN11 | Rajada na loja: volume em 15 min acima de 5× a mediana histórica da mesma faixa | +12 |
| RN12 | Mesmo documento pagando para ≥3 contas recebedoras **do mesmo lojista** em 24 h | +15 |

Calibração: os dois sinais mais fortes (RN09 +40 e RN05 +35) somam exatamente 75 — o piso de
recusa. Qualquer recusa exige, por construção, pelo menos dois sinais. Essa é a razão
aritmética por trás da RN14.

**Nota técnica sobre a RN05 — e é uma limitação de verdade.** O nome do pagador é
pseudonimizado (RN24), e **hash não admite comparação por similaridade**: `J*** SILVA` e
`JOAO SILVA` produzem hashes completamente diferentes, embora sejam a mesma pessoa. Como vários
PSPs devolvem o nome mascarado e a máscara varia, a comparação por igualdade de hash produziria
falso-positivo sempre que a máscara mudasse entre dois eventos.

O tratamento é em três camadas:

1. **Normalização agressiva antes do hash** (maiúsculas, sem acento, sem espaço duplo,
   mascaramento canonizado), de modo que a mesma grafia sempre produza o mesmo hash.
2. **A RN05 só é apurada quando ambos os nomes vêm sem máscara.** Se qualquer um dos dois estiver
   mascarado, o sinal é marcado como **indisponível** e a RN03 renormaliza o score — não
   pontua como divergência.
3. **Comparação por similaridade só na área bruta**, onde o texto original ainda existe (7 dias)
   e serve à investigação humana, nunca à decisão automática.

A consequência honesta: em PSPs que mascaram o nome por padrão, a RN05 praticamente não dispara,
e o sinal mais forte do catálogo depois da RN09 fica indisponível. Isso está declarado em 10 e é
critério relevante na escolha do PSP.

**Pagamento e entrega**

| ID | Regra |
|----|-------|
| RN13 | A liberação da entrega só é recomendada com pagamento confirmado **por evento do PSP**. Comprovante enviado pelo cliente nunca é aceito como prova. |
| RN15 | `(psp, end_to_end_id)` é único. Reentrega devolve o resultado original sem reprocessar. |
| RN16 | Veredito RECUSADO **solicita** devolução automática do valor ao pagador, com motivo registrado. A devolução é assíncrona e sujeita a saldo disponível (ver nota abaixo): fica em PENDENTE com retentativa até o PSP confirmar. Enquanto não concluída, a entrega permanece RETIDA. O lojista é notificado, não consultado antes. |
| RN17 | Veredito EM_ANALISE **não** devolve: enfileira para análise humana e recomenda segurar a entrega. |
| RN22 | Divergência entre valor recebido e valor esperado só é avaliada no canal E-COMMERCE, onde existe cobrança esperada (RF15). Quando ocorre, gera **divergência operacional, não sinal de risco** — o valor foi definido pelo sistema do lojista, então a diferença é erro de integração dele, não indício de fraude. No canal PRESENCIAL não há valor esperado e a regra não se aplica. |

**Nota técnica sobre a RN16 — restrição verificada na API do Asaas.** O estorno de Pix existe e
aceita devolução integral ou vários estornos parciais, mas **tentar estornar o valor integral
logo após o recebimento retorna erro 400**: o saldo precisa estar disponível na conta. E o
estorno tem ciclo próprio de status — `PENDING`, `CANCELLED`, `DONE` — sendo que só `DONE`
significa dinheiro devolvido.

Consequência de desenho: **a devolução não pode ser síncrona com o veredito.** A RN16 solicita e
acompanha; ela não conclui. Isso obriga três coisas no modelo:

1. `devolucao.situacao` carrega o ciclo do PSP, não um booleano.
2. `devolucao.tentativas` registra as retentativas, porque o erro 400 por saldo indisponível é
   esperado e recuperável — não é falha.
3. A entrega **continua RETIDA até a devolução concluir**. Liberar antes seria o pior dos mundos:
   mercadoria entregue e dinheiro ainda na conta, prestes a sair.

O webhook `PIX_REFUND` do Asaas fecha o ciclo e marca `concluida_em`.

**Confiança e maturidade**

| ID | Regra |
|----|-------|
| RN18 | Pagador com ≥3 pagamentos nesta loja nos últimos 180 dias, nenhum contestado, tem teto de score 39 — nunca é recusado automaticamente. |
| RN19 | Decisão é imutável. Revisão humana gera novo registro vinculado, nunca altera o anterior. |
| RN20 | Rotulagem de desfecho é obrigatória no fechamento do alerta e realimenta a calibração. |
| RN23 | Contestação recebida do PSP reabre o histórico do pagador e recalcula a reputação dele **naquele lojista**, de forma assíncrona. |

**Dados e privacidade**

| ID | Regra |
|----|-------|
| RN24 | Documento e nome do pagador são pseudonimizados por HMAC-SHA256 na ingestão. O valor original nunca é persistido fora da área de ingestão bruta. |
| RN25 | A área de ingestão bruta tem retenção de **7 dias** e expurgo automático. Depois disso, só resta o dado normalizado e pseudonimizado. |
| RN26 | Retenção: pagamento e devolução 5 anos (obrigação fiscal); sinal apurado 18 meses; ingestão bruta 7 dias. |
| RN27 | O pagador é identificado **por lojista**, nunca globalmente. Não existe reputação de pagador compartilhada entre lojistas. |
| RN28 | Analista vê dado pseudonimizado por padrão. Qualquer despseudonimização exige justificativa registrada e gera evento de auditoria. |

---

## 5. Organização e modelagem dos dados (roteiro 4.4 — Eixo 2)

### 5.1 Modelo conceitual (DER)

```
LOJISTA        (1) ──── (1..*) CONTA_RECEBEDORA
LOJISTA        (1) ──── (0..*) USUARIO
LOJISTA        (1) ──── (0..*) PAGADOR            ← por lojista, nunca global (RN27)
CONTA_RECEBEDORA (1) ── (0..*) PAGAMENTO
PAGADOR        (1) ──── (0..*) PAGAMENTO
PAGAMENTO      (1) ──── (0..1) COBRANCA_ESPERADA  ← só canal E-COMMERCE
PAGAMENTO      (1) ──── (0..1) ANALISE_RISCO
ANALISE_RISCO  (1) ──── (1..*) SINAL_APURADO
REGRA          (1) ──── (0..*) SINAL_APURADO
ANALISE_RISCO  (1) ──── (0..1) ALERTA
ALERTA         (1) ──── (0..1) DESFECHO
PAGAMENTO      (1) ──── (0..*) DEVOLUCAO
PAGAMENTO      (1) ──── (0..*) NOTIFICACAO
INGESTAO_WEBHOOK (1) ┄┄ (0..1) PAGAMENTO          ← relação lógica, SEM chave estrangeira
```

**Duas notas de cardinalidade que importam na leitura do modelo:**

- `PAGAMENTO ── (0..1) ANALISE_RISCO` é zero-ou-um, não um-para-um: o pagamento é gravado antes
  da análise rodar. Na prática toda linha acaba com análise, mas o modelo não pode exigir o que
  a ordem de execução não garante.
- A relação `INGESTAO_WEBHOOK ┄┄ PAGAMENTO` é **lógica, não física**. Não existe FK entre elas,
  e isso é deliberado: uma FK impediria o expurgo da RN25, porque o `DELETE` do bruto esbarraria
  na referência do pagamento permanente. O vínculo é reconstruível por `(psp, end_to_end_id)`
  enquanto o bruto existe, e some com ele — que é exatamente o comportamento desejado.

### 5.2 Modelo lógico — normalizado até a 3FN

```
lojista            (id_lojista PK, razao_social, cnpj_hash, psp, hora_abertura,
                    hora_fechamento, ativo, criado_em)

usuario            (id_usuario PK, id_lojista FK, email, senha_hash, papel, ativo,
                    criado_em)

conta_recebedora   (id_conta PK, id_lojista FK, chave_pix_hash, tipo_chave, apelido,
                    canal_padrao, ativa, criada_em)

pagador            (id_pagador PK, id_lojista FK, documento_hash, nome_hash,
                    primeiro_pagamento_em, ultimo_pagamento_em,
                    qtd_pagamentos, qtd_contestacoes)

ingestao_webhook   (id_ingestao PK, psp, origem_autenticada, confirmado_na_api, recebido_em,
                    payload JSONB, situacao_processamento, erro, expurgar_em)

pagamento          (id_pagamento PK, id_conta FK, id_pagador FK, psp, end_to_end_id,
                    txid, canal, valor, info_pagador, ocorrido_em, registrado_em,
                    situacao_entrega)

cobranca_esperada  (id_cobranca PK, id_conta FK, txid, valor_esperado, referencia_pedido,
                    criada_em, expira_em)

regra              (id_regra PK, codigo, versao, descricao, peso, expressao, ativa,
                    vigencia_inicio, vigencia_fim)

analise_risco      (id_analise PK, id_pagamento FK UNIQUE, veredito, score, degradada,
                    latencia_ms, versao_catalogo, analisado_em)

sinal_apurado      (id_sinal PK, id_analise FK, id_regra FK, disparou, contribuicao,
                    detalhe JSONB)

alerta             (id_alerta PK, id_analise FK UNIQUE, situacao, atribuido_a,
                    aberto_em, fechado_em)

desfecho           (id_desfecho PK, id_alerta FK UNIQUE, rotulo, justificativa,
                    registrado_por, registrado_em)

devolucao          (id_devolucao PK, id_pagamento FK, origem, valor, motivo,
                    id_externo_psp, situacao, tentativas, ultimo_erro,
                    solicitada_em, concluida_em)

notificacao        (id_notificacao PK, id_pagamento FK, id_usuario FK, canal_envio,
                    conteudo, enviada_em, lida_em)

auditoria          (id_auditoria PK, id_lojista FK, entidade, id_entidade, acao, ator,
                    justificativa, payload_hash, hash_anterior, ocorrido_em)
```

**Prova de 3FN**

- **1FN** — todos os atributos são atômicos. A faixa de horário do lojista foi decomposta em
  `hora_abertura` e `hora_fechamento` em vez de texto único. O payload semiestruturado está em
  `JSONB`, que é tipo nativo e consultável, não texto concatenado.
- **2FN** — todas as chaves primárias são simples e artificiais, o que elimina dependência
  parcial por construção. `pagamento.valor` é fato do pagamento, não do pagador.
- **3FN** — não há dependência transitiva. O peso da regra vive em `regra` e não é replicado em
  `sinal_apurado`; `sinal_apurado.contribuicao` é o valor **aplicado naquela análise**, que pode
  diferir do peso atual porque o catálogo é versionado — é fato próprio da análise, não
  redundância. O nome do lojista não é replicado em `pagamento`.

**Nota sobre os contadores em `pagador`.** `qtd_pagamentos` e `qtd_contestacoes` são agregados
deriváveis e, em 3FN estrita, redundantes. São desnormalização consciente — justificada em 5.6.

### 5.3 Modelo físico — DDL relevante

```sql
-- Área de ingestão: recebe o payload cru, vive 7 dias, é expurgada (RN25)
CREATE TABLE ingestao_webhook (
    id_ingestao             BIGSERIAL PRIMARY KEY,
    psp                     VARCHAR(20)  NOT NULL,
    origem_autenticada      BOOLEAN      NOT NULL,   -- token conferido (6.4)
    confirmado_na_api       BOOLEAN,                 -- reconsulta bateu (6.4)
    payload                 JSONB        NOT NULL,
    situacao_processamento  VARCHAR(20)  NOT NULL DEFAULT 'PENDENTE',
    erro                    TEXT,
    recebido_em             TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expurgar_em             TIMESTAMPTZ  NOT NULL
                            GENERATED ALWAYS AS (recebido_em + INTERVAL '7 days') STORED,
    CONSTRAINT ck_ingestao_situacao
        CHECK (situacao_processamento IN ('PENDENTE','PROCESSADO','REJEITADO'))
);

-- Índice GIN: consulta o payload de qualquer PSP sem conhecer o caminho de antemão
CREATE INDEX idx_ingestao_payload ON ingestao_webhook USING GIN (payload);

-- Expurgo automático, verificável (RNF14)
SELECT cron.schedule('expurgo_ingestao', '0 3 * * *',
    $$DELETE FROM ingestao_webhook WHERE expurgar_em < now()$$);


-- Núcleo transacional, particionado por mês
CREATE TABLE pagamento (
    id_pagamento      BIGSERIAL,
    id_conta          BIGINT       NOT NULL REFERENCES conta_recebedora(id_conta),
    id_pagador        BIGINT       NOT NULL REFERENCES pagador(id_pagador),
    psp               VARCHAR(20)  NOT NULL,
    end_to_end_id     VARCHAR(40)  NOT NULL,
    txid              VARCHAR(40),                      -- nulo no QR estático (2.2)
    canal             VARCHAR(12)  NOT NULL,
    valor             NUMERIC(12,2) NOT NULL CHECK (valor > 0),
    info_pagador      TEXT,
    situacao_entrega  VARCHAR(20)  NOT NULL DEFAULT 'RETIDA',
    ocorrido_em       TIMESTAMPTZ  NOT NULL,
    registrado_em     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (id_pagamento, ocorrido_em),
    CONSTRAINT uq_pagamento_e2e UNIQUE (psp, end_to_end_id, ocorrido_em),   -- RN15
    CONSTRAINT ck_pagamento_canal CHECK (canal IN ('PRESENCIAL','ECOMMERCE')),
    CONSTRAINT ck_pagamento_entrega
        CHECK (situacao_entrega IN ('RETIDA','LIBERADA','DEVOLVIDA','CONTESTADA'))
) PARTITION BY RANGE (ocorrido_em);

CREATE TABLE pagamento_2026_11 PARTITION OF pagamento
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');


-- Identidade do pagador, escopada ao lojista (RN27)
CREATE TABLE pagador (
    id_pagador             BIGSERIAL PRIMARY KEY,
    id_lojista             BIGINT NOT NULL REFERENCES lojista(id_lojista),
    documento_hash         CHAR(64) NOT NULL,
    nome_hash              CHAR(64),
    primeiro_pagamento_em  TIMESTAMPTZ,
    ultimo_pagamento_em    TIMESTAMPTZ,
    qtd_pagamentos         INTEGER NOT NULL DEFAULT 0,
    qtd_contestacoes       INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT uq_pagador_lojista UNIQUE (id_lojista, documento_hash)
);


-- Agregado que alimenta RN04, RN07 e RN11 sem varrer dado bruto no caminho da decisão
CREATE MATERIALIZED VIEW perfil_loja_diario AS
SELECT cr.id_lojista,
       p.id_conta,
       date_trunc('day', p.ocorrido_em)                            AS dia,
       count(*)                                                    AS qtd,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY p.valor)       AS p95_valor,
       percentile_cont(0.99) WITHIN GROUP (ORDER BY p.valor)       AS p99_valor
FROM pagamento p
JOIN conta_recebedora cr ON cr.id_conta = p.id_conta
WHERE p.ocorrido_em >= now() - INTERVAL '90 days'
GROUP BY cr.id_lojista, p.id_conta, dia;

CREATE UNIQUE INDEX ON perfil_loja_diario (id_conta, dia);

SELECT cron.schedule('refresh_perfil', '*/15 * * * *',
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY perfil_loja_diario$$);
```

**Nota sobre a chave primária composta de `pagamento`.** O particionamento declarativo do
PostgreSQL exige que a chave da partição faça parte de toda restrição única. Por isso
`PRIMARY KEY (id_pagamento, ocorrido_em)` e `UNIQUE (psp, end_to_end_id, ocorrido_em)`. É
custo real do particionamento e está declarado — não escondido.

### 5.4 Os dois canais no mesmo schema

O lojista presencial e o e-commerce são atendidos pelas **mesmas tabelas**. O canal é atributo
de `pagamento`, não schema separado. Três razões:

1. Os sinais são os mesmos sinais. Velocidade é velocidade, reputação é reputação. Separar
   duplicaria todas as nove regras.
2. Um lojista pode ter os dois canais — loja física com venda pelo Instagram é o caso comum.
3. A diferença real é **uma só**: o e-commerce tem valor esperado, o presencial não.

Essa diferença única fica isolada em `cobranca_esperada`, que existe apenas no canal
E-COMMERCE e é o que torna a RN22 aplicável. No presencial o cliente escaneia o QR do balcão e
digita o valor — não há valor esperado para comparar, e a regra simplesmente não se aplica.
Isso não é lacuna: é o modelo refletindo a realidade do trilho.

**Fluxo comparado:**

| Etapa | PRESENCIAL | E-COMMERCE |
|---|---|---|
| Origem do QR | Estático, no balcão | Dinâmico, gerado pelo lojista |
| `txid` | ausente | presente |
| Valor esperado | não existe | registrado em `cobranca_esperada` |
| Momento da decisão | Cliente no balcão | Antes da separação |
| Ação do veredito | Entrega ou retém | Libera ou retém o pedido |
| RN22 aplicável | não | **sim** |

Todo o resto — ingestão, pseudonimização, apuração de sinais, score, alerta, devolução,
auditoria — é o mesmo caminho.

### 5.5 Dicionário de dados (núcleo)

**`pagamento`**

| Campo | Tipo | Descrição | Regras |
|---|---|---|---|
| id_pagamento | BIGSERIAL | Identificador | PK (composta com `ocorrido_em`) |
| id_conta | BIGINT | Conta recebedora | FK, obrigatório |
| id_pagador | BIGINT | Pagador, escopado ao lojista | FK, obrigatório (RN27) |
| end_to_end_id | VARCHAR(40) | Identificador BACEN da transação | Único por PSP (RN15) |
| txid | VARCHAR(40) | Identificador da cobrança | **Nulo no QR estático** |
| canal | VARCHAR(12) | Origem | PRESENCIAL, ECOMMERCE |
| valor | NUMERIC(12,2) | Valor recebido | > 0 |
| info_pagador | TEXT | Texto livre digitado pelo pagador | Quase sempre vazio; alimenta RN12 fraco |
| situacao_entrega | VARCHAR(20) | Estado da mercadoria | RETIDA, LIBERADA, DEVOLVIDA, CONTESTADA |
| ocorrido_em | TIMESTAMPTZ | Momento do Pix no PSP | Chave de partição |
| registrado_em | TIMESTAMPTZ | Momento da nossa ingestão | Diferença mede atraso do webhook |

**`analise_risco`**

| Campo | Tipo | Descrição | Regras |
|---|---|---|---|
| id_analise | BIGSERIAL | Identificador | PK |
| id_pagamento | BIGINT | Pagamento avaliado | FK, UNIQUE — uma análise por pagamento (RN19) |
| veredito | VARCHAR(12) | Resultado | APROVADO, EM_ANALISE, RECUSADO |
| score | SMALLINT | Pontuação | 0–100 (RN02) |
| degradada | BOOLEAN | Faltou sinal | default false; true limita a EM_ANALISE (RN21) |
| latencia_ms | INTEGER | Tempo de análise | PN03, RNF01 |
| versao_catalogo | VARCHAR(20) | Versão das regras aplicada | Obrigatório para reprodutibilidade (RNF06) |

**`pagador`** — campos sensíveis

| Campo | Tipo | Descrição | Regras |
|---|---|---|---|
| documento_hash | CHAR(64) | HMAC-SHA256 do CPF/CNPJ | **Nunca o valor original** (RN24) |
| nome_hash | CHAR(64) | HMAC-SHA256 do nome normalizado | Compara identidade sem revelar (RN05) |
| id_lojista | BIGINT | Escopo da identidade | Impede reputação global (RN27) |

> O dicionário completo cobre as 15 tabelas e será consolidado no relatório final.

### 5.6 Índices — cada um com consumidor nomeado

| Índice | Quem consome |
|---|---|
| `uq_pagamento_e2e (psp, end_to_end_id, ocorrido_em)` | RN15 — idempotência do webhook |
| `pagamento (id_pagador, ocorrido_em DESC)` | RN04, RN06, RN08, RN18 — histórico do pagador |
| `pagamento (id_conta, ocorrido_em DESC)` | RN07, RN11 e PN01 — perfil da loja |
| `pagamento (situacao_entrega) WHERE situacao_entrega = 'RETIDA'` | Fila de retenção — **índice parcial**, pequeno e quente |
| `alerta (situacao) WHERE situacao = 'ABERTO'` | RF09 — fila do analista, **parcial** |
| `pagador (id_lojista, documento_hash)` UNIQUE | Resolução de identidade na ingestão |
| `ingestao_webhook USING GIN (payload)` | RF14 — conciliação e investigação de payload |
| `sinal_apurado (id_regra, disparou)` | PN02 — precisão por regra |
| `analise_risco (analisado_em DESC)` | PN03 — painel de latência |
| `devolucao (id_pagamento, origem)` | RN09, RN23 — histórico de contestação |

Índice sem consulta que o use é custo de escrita sem retorno. Por isso cada linha nomeia quem
o consome — e por isso os dois índices de fila são **parciais**: a fila tem dezenas de linhas
num universo de milhões.

### 5.7 Normalização versus desnormalização

Duas desnormalizações conscientes, ambas com justificativa e custo declarados:

1. **`pagador.qtd_pagamentos` e `qtd_contestacoes`.** São deriváveis por agregação. Mantidos
   materializados porque a RN18 e a RN09 são consultadas **dentro do orçamento de 2 s**, em todo
   pagamento. Calcular por agregação exigiria varrer o histórico do pagador a cada evento.
   **Custo:** precisam ser atualizados na mesma transação do pagamento, ou divergem.
   **Mitigação:** atualização por trigger na mesma transação, e job noturno de reconciliação
   que compara o contador com a contagem real e registra divergência.

2. **`sinal_apurado.contribuicao`.** Parece redundante com `regra.peso`, mas não é: é o peso
   **aplicado naquela análise**, sob a versão do catálogo vigente naquele momento. Sem ele,
   mudar um peso reescreveria o histórico de todas as decisões passadas, e a auditoria de RNF06
   deixaria de ser reconstruível. Isso é 3FN correta, não desnormalização.

### 5.8 Estratégia de crescimento

- **Particionamento:** `pagamento` e `sinal_apurado` particionadas por mês. Partição antiga vira
  candidata a `DETACH` e arquivamento frio após a retenção fiscal.
- **Índice BRIN** em `sinal_apurado(id_analise)`: a tabela é append-only e correlacionada com a
  ordem física, caso em que o BRIN ocupa uma fração do B-tree.
- **Agregado materializado:** `perfil_loja_diario`, atualizado a cada 15 min, evita varrer
  pagamento bruto no caminho da decisão.
- **Réplica de leitura:** carga analítica (PN01–PN08) isolada do caminho de decisão.
- **Expurgo:** `pg_cron` diário sobre `ingestao_webhook` (RN25) e mensal sobre `sinal_apurado`
  fora da retenção de 18 meses (RN26).
- **Limiar de cache:** 3.5. **Limiar de store colunar:** seção 10.

---

## 6. Segurança

Tratada em seção própria porque o produto **é** um controle de segurança — e porque um
antifraude é, ele próprio, alvo.

### 6.1 Modelo de ameaça

| Ameaça | Vetor | Controle |
|---|---|---|
| Comprovante falso | Cliente mostra print forjado | RN13 — comprovante nunca é prova; só evento do PSP |
| Webhook forjado | Atacante chama nosso endpoint fingindo ser o PSP | **O Asaas não assina os webhooks** (6.4). Controle primário: nunca confiar no corpo — reconsultar o pagamento na API antes de decidir. Secundários: token compartilhado comparado em tempo constante, allowlist de IP, TLS |
| Reentrega / replay | Webhook duplicado ou reenviado | RN15 — idempotência por chave natural durável |
| **Vazamento do catálogo de regras** | Acesso indevido ou insider | Pesos e limiares com acesso restrito e leitura auditada. **Quem conhece as regras, evade.** É a ameaça mais subestimada de qualquer antifraude. |
| **Lavagem de reputação** | Fraudador faz pagamentos pequenos e legítimos para ganhar o teto da RN18 | RN18 exige 180 dias **e** ausência de contestação — e contestação chega em até 90 dias, então a janela de maturação é maior que a de lavagem |
| **Ameaça interna** | Analista rotula fraude como legítima | RN20 — rotulagem atribuída e auditada; divergência estatística por analista monitorada |
| Vazamento entre inquilinos | Lojista acessa dado de outro | RNF09 — escopo por `id_lojista` em toda consulta; RN27 impede identidade global |
| Enumeração | Identificador sequencial exposto | Identificador público é UUID; o BIGSERIAL não sai da API |
| Exfiltração de dado pessoal | Acesso ao banco | Pseudonimização na ingestão (RN24); despseudonimização auditada (RN28) |
| Adulteração de trilha | Alteração de registro de auditoria | `auditoria` append-only, sem `UPDATE`/`DELETE` concedidos à aplicação; `hash_anterior` encadeado |

### 6.2 Controles

- **Em trânsito:** TLS em tudo; autenticação de origem verificada antes de qualquer
  processamento. `origem_autenticada` é persistida — webhook não autenticado é registrado e
  rejeitado, nunca silenciosamente descartado.
- **Em repouso:** criptografia de disco; chave HMAC de pseudonimização em cofre **separado do
  banco** — se o banco vazar sem a chave, o hash não é reversível por linkage.
- **Segredos:** variáveis de ambiente, `.env` fora do versionamento, `.env.example` com valores
  falsos. Nenhuma chave de API no repositório.
- **Autenticação e autorização:** JWT com papéis — `LOJISTA`, `ANALISTA`, `ADMIN`. Analista não
  vê dado identificável por padrão (RN28).
- **Banco:** a aplicação roda com usuário sem `DROP`, sem `DELETE` em `auditoria`, e sem acesso
  de escrita à réplica.
- **Superfície de pagamento:** nenhuma credencial de pagamento transita pelo sistema (RNF13).
  O cliente paga no app do próprio banco; nós recebemos aviso do que já aconteceu.

### 6.3 Decisões de escopo declaradas

- **JWT com guards, não Keycloak.** Keycloak é a resposta de produção, citada em 10.
- **Cofre de chave simulado por variável de ambiente no protótipo.** Em produção é KMS ou Vault.

Ambas são escolhas conscientes de escopo e estão declaradas em vez de omitidas.

### 6.4 O webhook do Asaas não é assinado — e o que fazemos a respeito

Isto é restrição real do fornecedor escolhido, verificada na documentação, não hipótese.

O Asaas **não assina** os webhooks: não há HMAC e não há carimbo de tempo. A autenticação é um
**token estático compartilhado**, enviado no cabeçalho `asaas-access-token`, que o receptor
compara com o valor configurado. Isso é materialmente mais fraco que assinatura, por três
motivos:

1. **Sem integridade de payload.** Quem souber o token pode forjar qualquer corpo — inclusive um
   `PAYMENT_RECEIVED` de R$ 50 mil que nunca existiu.
2. **Sem proteção contra replay.** O token é o mesmo sempre; não há *nonce* nem janela temporal.
3. **O segredo viaja em todo request.** Um log de cabeçalhos mal configurado vaza o token
   permanentemente, e não há rotação automática.

**O controle que resolve isso é arquitetural, não criptográfico:**

> **O webhook é tratado como aviso para ir olhar, nunca como fonte da verdade.**
> Ao receber o evento, o sistema **reconsulta o pagamento na API do Asaas** com a própria
> credencial e decide sobre o que a API respondeu — não sobre o que o corpo do webhook afirmou.

Com isso, um webhook forjado não produz efeito: ou a consulta não encontra o pagamento, ou
encontra com valor diferente, e em ambos os casos o evento vira `REJEITADO` em
`ingestao_webhook` com o payload preservado para investigação. O custo é uma chamada de API por
evento — perfeitamente dentro do orçamento de 2 s do RNF01.

Controles secundários: comparação do token em **tempo constante** (evita *timing attack*),
allowlist de IP de origem, TLS, e proibição explícita de registrar cabeçalhos em log.

**Isto é, por si, um bom argumento de defesa:** mostra que avaliamos a segurança do fornecedor em
vez de presumi-la, e que a mitigação não depende de um recurso que ele não oferece.

---

## 7. Qualidade e governança (roteiro 4.5)

### 7.1 Dimensões de qualidade

| Dimensão | Como é garantida |
|---|---|
| **Completude** | `NOT NULL` no essencial; taxa de `txid` ausente monitorada por canal (esperada ~100% no presencial) |
| **Consistência** | Contador de `pagador` reconciliado contra a contagem real por job noturno (5.7); soma de `contribuicao` reconciliada com `analise_risco.score` |
| **Unicidade** | `UNIQUE (psp, end_to_end_id, ocorrido_em)`; `UNIQUE (id_lojista, documento_hash)` |
| **Validade** | `CHECK` em valor, canal, veredito e situação; domínio fechado por enum textual com restrição |
| **Atualidade** | `registrado_em − ocorrido_em` mede o atraso do webhook e alimenta PN03 |

### 7.2 Dado sujo e duplicado

| Defeito | Tratamento |
|---|---|
| Webhook duplicado | Idempotência por chave natural (RN15) — a segunda chegada devolve o resultado original |
| Webhook fora de ordem | Máquina de estados de `situacao_entrega` só avança; transição inválida é ignorada e logada |
| Nome do pagador mascarado | RN05 marcada como indisponível e score renormalizado (RN03) — nunca tratada como divergência. Ver a nota técnica em 4.3 |
| Mesmo CPF com grafias diferentes de nome | Normalização canônica (maiúsculas, sem acento, sem espaço duplo) antes do hash |
| `txid` ausente no presencial | Esperado, não é defeito: `txid` é nulável e a RN22 não se aplica (5.4) |
| Payload de PSP em formato novo | Validação de schema na normalização; rejeito vai para `situacao_processamento = 'REJEITADO'` com o payload preservado para análise |
| Valor divergente no e-commerce | Divergência registrada; **é erro do sistema do lojista, não fraude** — gera alerta operacional, não sinal de risco |

**Para a demonstração**, o gerador (RF19) injeta esses defeitos em **quantidade conhecida**.
Isso permite *medir* a eficácia do tratamento em vez de afirmá-la — e produz a evidência
numérica que esta seção exige.

### 7.3 Fluxo de ingestão

```
  [Webhook do PSP]
         │
         ▼
  Conferência do token (tempo constante) ── falha ──> ingestao_webhook (REJEITADO, registrado)
         │
         ▼
  ingestao_webhook  ← payload cru, JSONB, vive 7 dias     ① TABELA INTERMEDIÁRIA
         │
         ▼
  RECONSULTA NA API DO PSP (6.4) ── divergiu ──> REJEITADO, payload preservado
         │   ← a verdade vem daqui, não do corpo do webhook
         ▼
  Validação e normalização (schema por PSP) ── falha ──> REJEITADO, payload preservado
         │
         ▼
  Pseudonimização HMAC (RN24)   ← aqui o dado identificável morre
         │
         ▼
  pagador (resolve ou cria, escopado ao lojista)
         │
         ▼
  pagamento  ← sistema de registro                        ② TABELA DEFINITIVA
         │
         ├──> apuração de sinais ──> sinal_apurado ──> analise_risco
         │                                                   │
         │                              ┌────────────────────┤
         │                   RECUSADO ──┤                    ├── EM_ANALISE ──> alerta
         │                              │                    │
         │                              ▼                    ▼
         │                          devolucao            APROVADO
         │                                                   │
         └──────────────────> notificacao <──────────────────┘
         │
         ▼  (pg_cron, diário, 03h)
  DELETE FROM ingestao_webhook WHERE expurgar_em < now()     ③ O DADO BRUTO SOME
```

**O ciclo ①→②→③ é o momento central da demonstração e da governança ao mesmo tempo.** Dá para
mostrar na tela: a linha bruta aparece em `ingestao_webhook` com o CPF em claro dentro do
`JSONB`, é normalizada para `pagamento` já com hash, e some no expurgo. Um gesto, duas
evidências — modelagem em 4.4 e minimização em 4.5.

**Híbrido por necessidade:** tempo real no caminho da decisão (velocidade é requisito), lote no
analítico e no expurgo (volume é requisito). A pseudonimização acontece **antes** de qualquer
escrita definitiva — nenhuma tabela permanente jamais vê o dado original.

### 7.4 LGPD

**Dados pessoais envolvidos:** nome e CPF/CNPJ do pagador, vindos do webhook; e-mail dos
usuários do lojista. Nada mais. Não coletamos endereço, telefone, data de nascimento ou
qualquer dado que não alimente uma RN.

**Base legal** — e a distinção importa:

| Finalidade | Base legal |
|---|---|
| Registrar e conciliar o recebimento | **Execução de contrato** (art. 7º, V) — com o lojista |
| Prevenção à fraude | **Legítimo interesse** (art. 7º, IX), com teste de proporcionalidade documentado |
| Retenção fiscal de 5 anos | **Cumprimento de obrigação legal** (art. 7º, II) |

Apoiar a prevenção à fraude em **consentimento** seria errado e frágil: o titular poderia
revogar e inviabilizar justamente o controle. O art. 7º, IX existe para isso, e usá-lo exige o
teste de proporcionalidade — que está feito: a finalidade é legítima, o meio é adequado, e a
pseudonimização na ingestão é a medida que minimiza o impacto ao titular.

**Por que não há compartilhamento de sinal entre lojistas.** Foi avaliado e **descartado**. Uma
rede de reputação entre lojistas seria o maior diferencial do produto — e é também o maior
risco. Cada lojista é controlador autônomo; compartilhar reputação de pagador entre eles é
comunicação de dado pessoal entre controladores distintos, exigiria base legal própria,
transparência ao titular e provavelmente decisão da ANPD sobre proporcionalidade. Pseudonimizar
não resolve: o hash é **identificador comportamental** e permite relacionar a mesma pessoa
entre controladores, o que é tratamento de dado pessoal ainda assim.

A RN27 implementa a decisão no modelo: `pagador` tem FK para `lojista`, e a chave única é
`(id_lojista, documento_hash)`. **A impossibilidade está no schema, não só na política** — não é
possível, por construção, consultar reputação global. Esse é o ponto: o controle de privacidade
mais forte é o que o modelo de dados torna impossível.

**Minimização.** Cada campo do dicionário existe porque uma regra o consome. O exercício inverso
foi feito: campos sem consumidor foram removidos do modelo.

**Pseudonimização.** HMAC-SHA256 na ingestão (RN24), chave em cofre separado do banco. A área
bruta, único lugar onde o original existe, tem 7 dias de vida e expurgo automático verificável.

**Direitos do titular.** RF18 cobre acesso, correção e eliminação. A eliminação respeita a
retenção fiscal de 5 anos: os dados são bloqueados, não apagados, e o titular é informado da
base legal — que é a resposta correta, não uma evasiva.

**Riscos residuais declarados:**
1. O hash permite *linkage* se o atacante tiver a base de CPFs **e** a chave HMAC. Mitigado por
   guarda da chave em cofre separado, mas não eliminado.
2. O pagador não tem relação contratual conosco e provavelmente não sabe que seu pagamento foi
   analisado. Isso é inerente ao legítimo interesse e exige transparência na política de
   privacidade do lojista — não resolvemos no código.
3. Rótulo enviesado (2.4) significa que a métrica de precisão que reportamos é otimista.

### 7.5 Backup, acesso e riscos operacionais

- **Backup:** dump diário com retenção de 30 dias + WAL archiving para *point-in-time recovery*.
  Com um motor só, há **um** procedimento de backup — que é precisamente o argumento de 3.1
  aparecendo como benefício concreto.
- **Restauração testada:** restauração verificada mensalmente, não apenas backup gerado. Backup
  não testado não é backup.
- **Controle de acesso:** papéis distintos no banco; a aplicação não tem `DROP` nem `DELETE` em
  `auditoria`.
- **Riscos:** indisponibilidade do PSP (fila de conciliação por RF14 cobre a lacuna); atraso de
  rótulo enviesando a avaliação (2.4 e 10); dependência de um único PSP (mitigada pela
  normalização de 7.3 — trocar de PSP muda só o normalizador, não o schema).

---

## 8. Arquitetura da aplicação

### 8.1 Monorepo TypeScript

```
confia/
├── apps/
│   ├── api/          NestJS — webhook, normalização, motor de risco, API
│   └── web/          (depois) Next.js — console do lojista e do analista
├── packages/
│   ├── contracts/    Schemas Zod + tipos — FONTE ÚNICA do contrato
│   ├── rules/        Catálogo de regras e motor de score
│   └── db/           Migrations + acesso ao PostgreSQL
└── docker-compose.yml
```

`packages/contracts` é o que elimina a gambiarra: API, web e futuro app importam **o mesmo
tipo**. Um campo renomeado quebra o build dos três em vez de quebrar em produção.

**Nesta etapa construímos `api`, `rules`, `db` e `contracts`.** O `web` vem depois, à parte,
consumindo o contrato já pronto.

### 8.2 O que é notificação

O lojista não abre painel. A notificação é o produto na mão dele:

> **CONFIA** · Recebido **R$ 2.840,00** de J\*\*\* S\*\*\*
> ⚠️ **Em análise** — não entregue ainda
> *Primeiro pagamento deste cliente · valor acima do seu padrão*

A tabela `notificacao` registra o que foi enviado, para quem e quando foi lido — o que importa
porque "o lojista entregou mesmo tendo sido avisado" é fato que precisa ficar registrado.

### 8.3 Contrato de API

OpenAPI 3 gerado via `@nestjs/swagger`, versionado em `/api/v1`. Nenhuma lógica de tela no
servidor, para que web e app consumam o mesmo contrato.

---

## 9. Prova de conceito (roteiro 4.6)

### 9.1 Ambiente

`docker compose up` sobe PostgreSQL 16 (com `pg_cron` e `pg_trgm`) e a API. **Dois contêineres.**
Na versão anterior eram seis — e essa redução é, ela própria, a demonstração prática do
argumento de 3.1.

### 9.2 Massa de dados

- **Sintética (RF19):** 50 lojistas, 12 mil pagadores, 2,2 milhões de pagamentos em 12 meses,
  ~20 milhões de sinais apurados, com **fraude plantada**: pagadores com padrão de sonda,
  documentos com nome divergente, contestações distribuídas com atraso realista de até 90 dias
  (2.4), e defeitos injetados em quantidade conhecida (7.2).
- **Real:** pagamentos Pix de verdade no **sandbox do PSP**, feitos ao vivo.

### 9.3 Pix real — como fica

Sandbox do PSP durante todo o projeto, inclusive na apresentação. O ambiente de homologação
gera QR Code válido e dispara webhook de verdade — o caminho completo é exercitado, só o
dinheiro é que não é real.

**Ponto de atenção que resolvemos em vez de esconder:** em produção o webhook traz nome e CPF
reais do pagador, e o enunciado proíbe dado pessoal real no protótipo. A RN24 pseudonimiza na
ingestão e a RN25 expurga o bruto em 7 dias — então **o próprio controle de minimização descrito
em 7.4 é o que tornaria a operação real conforme**. Isso vira evidência da seção de governança
em vez de problema. No sandbox a questão nem se coloca, porque os dados são fictícios por
construção.

### 9.4 Consultas que respondem às perguntas de negócio

Todas em PostgreSQL, todas sobre o mesmo motor.

| # | Pergunta | Técnica |
|---|---|---|
| 1 | PN01 — veredito por período, canal e faixa de valor | `GROUP BY` com `width_bucket` sobre valor |
| 2 | PN02 — precisão por regra | `sinal_apurado` × `desfecho`, agregação condicional com `FILTER` |
| 3 | PN03 — latência p50/p95/p99 | `percentile_cont` sobre `latencia_ms` |
| 4 | PN04 — valor preservado | Soma de recusados cujo pagador depois acumulou contestação |
| 5 | PN05 — perfil do revertido vs. legítimo | Histograma horário e de valor por rótulo, `date_part` + `width_bucket` |
| 6 | PN06 — dias até a contestação | `devolucao.solicitada_em − pagamento.ocorrido_em`, por faixa |
| 7 | PN07 — recorrência e reversão | Window function `count() OVER (PARTITION BY id_pagador ORDER BY ocorrido_em)` |
| 8 | PN08 — fila de análise humana | `alerta` com `fechado_em − aberto_em` |

As consultas 5 e 7 usam window function e as 1 e 5 usam `width_bucket` — são exatamente os
recursos que sustentam o argumento de 3.3 de que um motor relacional dá conta da carga
analítica deste projeto.

### 9.5 Roteiro da demonstração ao vivo

1. **Abrir o banco.** Mostrar as 15 tabelas, o particionamento de `pagamento`, os dois índices
   parciais e a materialized view. Esta é a parte que vale os 6,0 pontos dos dois eixos.
2. **Pagar um Pix no sandbox**, pelo celular, escaneando o QR.
3. **Mostrar `ingestao_webhook`** — a linha bruta chegando, com o payload inteiro em `JSONB`.
4. **Mostrar `pagamento`** — a mesma transação já normalizada e com o documento em hash.
5. **Mostrar a notificação** — `APROVADO`, com a latência em ms.
6. **Disparar um pagamento com padrão de fraude** — documento com contestação prévia e padrão de
   sonda. **RECUSADO.** Abrir `sinal_apurado` e mostrar quais regras dispararam, com peso.
7. **Mostrar a devolução** registrada automaticamente (RN16).
8. **Reenviar o mesmo webhook** e mostrar que nada duplicou (RN15).
9. **Rodar o expurgo** e mostrar a linha bruta desaparecendo (RN25) — enquanto o pagamento
   normalizado permanece.
10. **Rodar as 8 consultas** e mostrar os resultados.

Os passos 1, 9 e 10 são os que endereçam diretamente a rubrica. Os demais são o que torna a
apresentação convincente.

---

## 10. Limitações e próximos passos (roteiro 4.7)

**Onde esta escolha pode falhar, declarado honestamente:**

- **Sinal transacional apenas.** Sem dispositivo, IP ou geolocalização, não detectamos o que
  antifraude de e-commerce detecta. É consequência direta de não estarmos no fluxo de pagamento
  (1.4) — e é o preço do atrito zero.
- **Fraudador de primeira viagem.** Documento limpo, primeira compra, valor dentro do padrão da
  loja: nenhuma regra dispara. É o limite estrutural de qualquer abordagem baseada em
  histórico.
- **Rótulo atrasado em até 90 dias.** Toda métrica de precisão que reportarmos é otimista por
  construção. Limitação de método, não de implementação — vale para o mercado inteiro.
- **Sem rede entre lojistas.** Decisão deliberada (7.4), mas custa detecção: um fraudador que
  rode a mesma tática em vinte lojas diferentes é visto como estreante em cada uma.
- **Volume.** A ~100× (2 bilhões de sinais/ano), a carga analítica no mesmo motor do operacional
  deixa de ser adequada mesmo com réplica. Migração da camada analítica para store colunar via
  ELT. **Limiar:** quando a consulta de PN02 passar de 30 s na réplica.
- **Cache.** Limiar em 3.5: ao encostar nos 200 pagamentos/s do RNF03, ou com p95 de apuração
  acima de 300 ms, Redis entra.
- **Nome mascarado inutiliza a RN05.** Em PSPs que mascaram o nome do pagador por padrão, o
  segundo sinal mais forte do catálogo fica indisponível na prática (nota técnica em 4.3), e o
  score passa a depender mais da RN09. É critério de escolha do PSP, não detalhe de
  implementação.
- **Regras determinísticas.** Explicáveis e defensáveis, mas não aprendem. O passo natural é usar
  o rótulo de desfecho (RN20) para calibrar os pesos — e só então, com base rotulada suficiente
  e o viés de 2.4 tratado, avaliar um modelo.
- **Escopo de autenticação.** JWT no protótipo; Keycloak em produção.
- **Devolução automática no RECUSADO** é decisão de protótipo. Em produção, devolver
  automaticamente cria vetor de ataque — um fraudador poderia forçar devoluções para mover
  dinheiro. A resposta real seria retenção com prazo, não devolução imediata. **Declarado como
  simplificação consciente.**

---

## 11. Stack e reuso

Construímos a lógica de domínio; compramos a infraestrutura.

| Necessidade | Solução |
|---|---|
| Trilho Pix | **Asaas** (sandbox) — decidido; ver 6.4 e a nota da RN16 para as restrições |
| Banco de dados | **PostgreSQL 16** + `pg_cron` + `pg_trgm` |
| Framework de API | NestJS |
| Acesso a dados | Prisma (ou Kysely, se o particionamento exigir SQL mais direto) |
| Contrato e validação | Zod |
| Dados sintéticos BR | Faker |
| Observabilidade | OpenTelemetry + Prometheus |
| Infra local | Docker Compose — **dois contêineres** |
| Web (depois) | Next.js |

**Decisões conscientes de escopo:** sem Kafka; sem Redis no dia um (limiar em 3.5); sem
Keycloak no protótipo; sem machine learning (regras explicáveis servem melhor à auditoria e à
arguição).

**O que é autoral:** o catálogo de RN e sua calibração aritmética, o motor de decisão com
degradação graciosa, o modelo de dados de motor único com o ciclo de ingestão efêmera, o escopo
de identidade por lojista como controle de privacidade estrutural, o gerador de massa com
fraude plantada e atraso de rótulo realista, e as oito consultas analíticas. É sobre isso que
os Eixos 1 e 2 são avaliados.

---

## 12. Declaração de uso de IA

Assistente de IA generativa utilizado como apoio na estruturação deste documento, na comparação
de alternativas de persistência e na redação. Todas as decisões técnicas, pesos de regra e
modelagem foram revisados e são de domínio da equipe, que responde integralmente por qualquer
estrutura ou linha de código apresentada.

---

## Pendências antes do plano de implementação

1. ~~Escolher o PSP.~~ **Decidido: Asaas.** Duas restrições dele já estão absorvidas no desenho —
   webhook não assinado (6.4) e devolução assíncrona dependente de saldo (nota da RN16).
2. **Verificar empiricamente, no sandbox, se o `PAYMENT_RECEIVED` do Asaas traz o nome e o
   documento do pagador, e se vêm mascarados.** A documentação pública não especifica, e é isso
   que decide se a RN05 funciona na prática (nota técnica em 4.3). É a primeira coisa a fazer na
   implementação: um webhook de teste e uma inspeção do JSON bruto respondem.
3. **Confirmar o nome do produto.** CONFIA segue provisório.
4. **Confirmar a data de entrega da A3 de Big Data** — o enunciado veio com o cronograma em
   branco.
5. **Confirmar o número de integrantes** da equipe (o enunciado permite até 5).
