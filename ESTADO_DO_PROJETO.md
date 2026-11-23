# CONFIA — Estado do Projeto

**A3 · Análise de Dados e Big Data · USJT 2026/2**
**Atualizado em:** 23/11/2026

> **Atualização de entrega (23/11/2026):** a A3 agora possui relatório final em
> `output/pdf/CONFIA_relatorio_A3.pdf`, protótipo relacional reproduzível em `sql/`,
> oito consultas executadas com resultados em `evidencias/resultados.json` e roteiro
> de apresentação em `PITCH.md`. O comando `npm run demo` foi verificado localmente.
> O plano de 17 tarefas abaixo permanece como visão de produto futuro; a integração
> com Asaas e o aplicativo em tempo real não fazem parte desta prova de conceito.
> Consulte `README.md` para reprodução. A seção 6 registra pendências históricas
> do plano de produto, não bloqueios da entrega da A3.

> Este documento existe para você retomar o projeto sem refazer nada e sem repetir discussão já
> encerrada. Leia a seção 3 antes de propor qualquer mudança de rumo — ela registra o que já foi
> descartado e por quê.

---

## 1. Onde está tudo

Todos os arquivos estão em `C:\Users\gsantana5\Documents\A3_BigData\`.

| Arquivo | O que é | Estado |
|---|---|---|
| `ESTADO_DO_PROJETO.md` | Este documento | — |
| `docs/superpowers/specs/2026-11-23-confia-antifraude-pix-recebido-design.md` | **O spec válido.** Desenho completo, aprovado | Aprovado |
| `docs/superpowers/specs/2026-11-23-confia-checkout-pix-antifraude-design.md` | Versão antiga (cinco bancos + e-commerce). Mantida como histórico | **Superado — não usar** |
| `docs/superpowers/plans/2026-11-23-confia-antifraude-pix-recebido.md` | Plano de implementação, 17 tasks em TDD | Pronto, não iniciado |

### Situação do controle de versão

**Repositório local criado e com o primeiro commit feito** (`b21517b`), contendo os quatro
documentos e o `.gitignore`. A raiz do repositório é a própria pasta do projeto.

Antes disso o único repositório que alcançava essa pasta tinha raiz em `C:\Users\gsantana5` — a
pasta de usuário inteira — e zero commits. Era um risco: um `git add .` ali tentaria versionar
`AppData`, `Downloads` e `OneDrive`. Por isso o projeto ganhou repositório próprio.

**Ainda não existe remoto. Nada foi enviado para o GitHub e não há link para compartilhar.**
Para o grupo ter acesso, falta criar um repositório no GitHub e apontá-lo como `origin`:

```bash
gh repo create confia-a3-bigdata --private --source=. --remote=origin --push
```

O `.gitignore` já protege `.env` e `.claude/settings.local.json` — nenhuma credencial do Asaas
pode entrar no repositório por acidente (RNF04 e seção 6.2 do spec).

---

## 2. O que é o projeto

**CONFIA** — um serviço que o lojista contrata, que observa os Pix que ele **recebe**, decide se
cada um é confiável antes da entrega da mercadoria, e avisa no celular dele.

### A dor, na formulação final

A dor óbvia é o comprovante falso: o cliente mostra um print, o lojista entrega, o dinheiro
nunca entrou. Isso é real e é trivial de resolver.

A dor **cara** é outra:

> O Pix entra de verdade, a mercadoria sai, e semanas depois o dinheiro é retirado da conta do
> lojista.

Isso acontece pelo **MED (Mecanismo Especial de Devolução)**. Quando alguém é vítima de golpe,
contesta no banco e o valor é debitado de quem recebeu. Se o dinheiro que pagou a compra era
produto de golpe — conta de laranja, vítima induzida, conta invadida — o lojista é o elo final:
recebeu, entregou, e vai ser debitado. O extrato não avisa.

**Então o produto não é "confirmar que o Pix entrou". É prever qual Pix vai voltar.**

Essa reformulação é o centro de tudo. Confirmar o recebimento resolve o golpe barato e é o piso;
a análise de risco resolve a perda cara e é o produto.

### Como funciona

1. O cliente escaneia o QR Code da loja — o estático do balcão ou o dinâmico que o sistema do
   lojista gera. **Nada muda para o cliente.**
2. Ele paga no app do próprio banco, como já faz hoje.
3. O Asaas (nosso intermediário) avisa o CONFIA por webhook.
4. O CONFIA **reconsulta o pagamento na API do Asaas** (o corpo do webhook nunca é fonte da
   verdade), normaliza, pseudonimiza o pagador, apura nove sinais de risco e emite veredito.
5. Chega notificação no celular do lojista: *"Recebido R$ 340,00. Aprovado."* ou *"Recebido
   R$ 2.800,00. Em análise — não entregue ainda."*

---

## 3. O caminho até aqui — o que já foi descartado e por quê

Esta seção é a mais importante do documento. São decisões fechadas; reabrir qualquer uma delas é
refazer trabalho.

### Ideias de produto descartadas

| Ideia | Por que caiu |
|---|---|
| Sistema médico / clínica | Reaproveitaria o tema do MediFlow, mas não tem nada demonstrável ao vivo |
| Controle de medicamento + antifraude Pix | Dois problemas colados sem relação; o Pix era enxerto |
| **FarmaVigil** — portal de medicamentos para médico | Complexo de montar, impossível de demonstrar na hora |
| **Sentinela** — monitoramento cardíaco | Bom projeto, mas exigiria simular aparelho; nada palpável na apresentação |
| Reforma tributária + teste na SEFAZ + DANFE | Chegou a ser levantado e abandonado em favor do CONFIA |

**O padrão que fez tudo isso cair:** o critério decisivo virou *"o que a gente consegue mostrar
funcionando na hora"*. Tudo que não passa nesse teste foi descartado.

### Decisões técnicas fechadas

| Decisão | O que foi descartado | Razão |
|---|---|---|
| **TypeScript** | Python/FastAPI, Java/Spring Boot | Linguagem confortável para você; monorepo com tipos compartilhados atende literalmente "um sistema só sem gambiarra". Custo aceito: perder o Spring Data |
| **PostgreSQL único** | Persistência poliglota (Postgres + TimescaleDB + MongoDB + Neo4j + Redis) | Custo de manutenção e risco de inconsistência. Ver seção 4 |
| **Sem Redis no dia um** | Redis como componente obrigatório | Nada precisa viver só no cache nesta escala. Virou limiar documentado |
| **Sem banco de grafo** | Neo4j para rede de fraude | Sem compartilhamento entre lojistas, a relação pagador↔loja tem profundidade 1. Isso é um `JOIN`, não um grafo |
| **Loja física (QR do balcão)** | E-commerce como palco principal | E-commerce já tem solução pronta; o caso presencial é o real. O e-commerce continua atendido pelo mesmo schema |
| **Consumimos evento, não geramos cobrança** | CONFIA gerando o QR | O CONFIA entra na confirmação. Zero atrito para o cliente e para a implantação |
| **Sem rede de reputação entre lojistas** | Compartilhar sinal de fraude entre lojas | Risco de LGPD — comunicação de dado pessoal entre controladores distintos. Decisão sua, e está certa |
| **Sem device fingerprint / geolocalização** | Sinais de dispositivo e IP | Não existem no trilho Pix. Consequência de não estarmos no fluxo de pagamento |
| **Regras determinísticas, sem machine learning** | Modelo preditivo | Explicáveis, auditáveis, defensáveis na arguição. ML viria depois, com base rotulada |
| **Asaas em sandbox** | Efí; produção com R$ 0,01 | Só precisa de API key. O clique manual de confirmação no sandbox funciona a favor na demo |
| **Sem Kafka, sem Keycloak** | — | Escopo consciente, declarado no spec |

### Uma reversão que vale registrar

Em algum momento eu disse que **Pix real era impossível**, e depois voltei atrás. As duas coisas
estavam certas em contextos diferentes: em antifraude *bancário* você não intercepta a
autorização do SPI de fora; em *comércio* o ponto de controle é "liberar a entrega", que acontece
depois do pagamento e que o lojista controla. Se alguém do grupo levantar isso, essa é a resposta.

---

## 4. O argumento do banco — o que mais vale ponto

A rubrica dá **3,0 para a escolha do banco (Eixo 1)** e **3,0 para organização e modelagem
(Eixo 2)**. Juntos são 6,0 dos 10,0. O enunciado é explícito:

> "O foco da A3 não é o app bonito nem o plano de negócios: é mostrar que vocês sabem escolher o
> tipo de banco de dados adequado ao problema e organizar os dados com qualidade."

O argumento está montado em quatro camadas, nessa ordem — e é nessa ordem que ele se sustenta
sob pergunta.

### Camada 1 — custo de operação

Cinco bancos não são cinco tecnologias. São cinco procedimentos de backup e restauração testada,
cinco stacks de monitoramento, cinco ciclos de CVE, cinco conjuntos de modo de falha que alguém
precisa conhecer de madrugada, e **cinco especialistas** — ou um generalista raso em todos.

Para um lojista que fatura R$ 80 mil por mês, isso é proibitivo. **Com um motor só, o mesmo
orçamento compra uma pessoa muito boa em vez de cinco medianas.**

### Camada 2 — corretude (mais forte que a primeira)

Não existe transação ACID entre motores heterogêneos. Com cinco stores você tem **dez fronteiras
de inconsistência**, e cada uma vira job de reconciliação — código que alguém escreve, testa,
opera, e que falha calado.

Num sistema que decide sobre dinheiro isso deixa de ser custo e vira corretude:

> "Pagamento gravado no Postgres, sinal de devolução prévia perdido no Mongo" = lojista entregou
> mercadoria que não devia.

### Camada 3 — cobertura

| Necessidade | Recurso do PostgreSQL | O que seria usado |
|---|---|---|
| Payload de webhook variável | `JSONB` + índice GIN | MongoDB |
| Série temporal | Particionamento declarativo + BRIN | TimescaleDB |
| Agregado de perfil | Materialized view + `pg_cron` | Continuous aggregate |
| Janela de velocidade | Window function | Redis |
| Percentil do histórico | `percentile_cont` | Warehouse |
| Relação pagador↔loja | `JOIN` (profundidade 1) | Neo4j |
| Idempotência | `UNIQUE` — **durável, não volátil** | Redis |
| Fila de análise | Índice parcial | Redis / SQS |

### Camada 4 — alternativas comparadas

**MySQL 8** é a alternativa séria e é a que vão perguntar (o MediFlow usa MySQL). Empata em
window function, particionamento e CTE recursiva. Perde em três pontos que usamos de fato:
índice sobre JSON (o GIN indexa o documento inteiro; no MySQL é preciso coluna gerada por
caminho), ausência de índice parcial, e as extensões `pg_trgm` e `pg_cron`.

### As duas frases para decorar

> **Um banco é onde o dado nasce; cache é onde ele passa.** Se o cache for apagado, o sistema
> fica mais lento — nunca errado. Um sistema de registro só.

> Não usamos banco de grafo porque **a profundidade real do problema é 1**. Descartado por
> análise, não por preferência.

### A resposta para "e se crescer?"

Não defender que um banco é sempre melhor. Defender: **um banco até um limiar medido forçar a
divisão, e o limiar está escrito.**

- Redis entra ao encostar em 200 pagamentos/s ou com p95 de apuração acima de 300 ms.
- Store colunar entra quando a consulta PN02 passar de 30 s na réplica.

Ter o gatilho documentado é o que separa decisão de preferência.

---

## 5. O que já está feito

### Requisitos — catálogo completo

**20 RF, 14 RNF, 28 RN.** As RN são o núcleo autoral. As que mais importam:

| ID | Regra |
|---|---|
| **RN02** | Score 0–100. ≤39 APROVADO · 40–74 EM_ANALISE · ≥75 RECUSADO |
| **RN03** | Sinal indisponível não zera o score: renormaliza pelos pesos apurados e registra a ausência |
| **RN13** | Liberação só com pagamento confirmado **por evento do PSP**. Comprovante do cliente nunca é prova |
| **RN14** | **Recusa exige dois sinais independentes.** Nenhum sinal sozinho recusa |
| **RN16** | RECUSADO **solicita** devolução — assíncrona, sujeita a saldo, com retentativa. A entrega fica RETIDA até concluir |
| **RN21** | Veredito degradado tem **teto em EM_ANALISE** — nunca recusa com informação incompleta |
| **RN24** | Documento e nome do pagador pseudonimizados por HMAC-SHA256 na ingestão |
| **RN25** | Ingestão bruta tem **7 dias** de retenção e expurgo automático |
| **RN27** | Pagador identificado **por lojista**, nunca globalmente |

**Os nove sinais e seus pesos** (somam 207):

| ID | Sinal | Peso |
|---|---|---|
| RN09 | Pagador com devolução ou contestação anterior nesta loja | **40** |
| RN05 | Mesmo documento já apareceu com nome divergente | **35** |
| RN08 | Padrão de sonda: ≤ R$ 5 seguido de valor ≥ 20× em 30 min | 30 |
| RN04 | Pagador novo **e** valor acima do p95 da loja | 25 |
| RN06 | ≥3 pagamentos do mesmo documento em 10 min | 25 |
| RN07 | Valor acima do p99 dos últimos 90 dias | 15 |
| RN12 | Mesmo documento para ≥3 contas do mesmo lojista em 24 h | 15 |
| RN11 | Rajada na loja: 5× a mediana da faixa em 15 min | 12 |
| RN10 | Fora da faixa de horário declarada pelo lojista | 10 |

**A calibração não é arbitrária:** RN09 (40) + RN05 (35) = exatamente 75, o piso de recusa. Por
construção, toda recusa exige pelo menos dois sinais. É a razão aritmética por trás da RN14.

### Banco — 15 tabelas modeladas

`lojista` · `usuario` · `conta_recebedora` · `pagador` · `ingestao_webhook` · `pagamento` ·
`cobranca_esperada` · `regra` · `analise_risco` · `sinal_apurado` · `alerta` · `desfecho` ·
`devolucao` · `notificacao` · `auditoria`

Com modelo conceitual, lógico e físico, prova de 3FN, dicionário de dados, e **cada índice com o
consumidor nomeado** — índice sem consulta que o use é custo de escrita sem retorno.

**Dois detalhes técnicos que renderam decisão:**

- `pagamento` é particionada por mês, o que obriga chave primária composta
  `(id_pagamento, ocorrido_em)` — o particionamento declarativo exige a chave da partição em toda
  restrição única. Custo real, declarado.
- **Não há FK entre `ingestao_webhook` e `pagamento`**, de propósito: uma FK impediria o expurgo
  da RN25, porque o `DELETE` do bruto esbarraria na referência.

### O ciclo das tabelas intermediárias — o melhor momento da demo

```
webhook → ingestao_webhook (CPF em claro no JSONB, 7 dias)
        → reconsulta na API do Asaas
        → pseudonimização HMAC
        → pagamento (já com hash)
        → pg_cron expurga o bruto → o dado original some
```

Dá para mostrar acontecendo na tela. **Um gesto, dois pontos da rubrica** — modelagem (4.4) e
minimização de dados (4.5).

### Segurança — tratada com seção própria

Modelo de ameaça com dez vetores. Os três que valem a leitura porque tratam o antifraude **como
alvo**: vazamento do catálogo de regras (quem conhece as regras, evade), lavagem de reputação
(fraudador faz pagamentos limpos para ganhar o teto da RN18) e ameaça interna (analista que
rotula fraude como legítima).

**O achado que mudou o desenho:** o webhook do Asaas **não é assinado** — não há HMAC nem carimbo
de tempo, só um token estático no cabeçalho. Verificado na documentação. A mitigação é
arquitetural: *o webhook é aviso para ir olhar, nunca fonte da verdade* — reconsultamos o
pagamento na API antes de decidir. Isso vira argumento de defesa: mostra que avaliamos a segurança
do fornecedor em vez de presumi-la.

### LGPD

| Finalidade | Base legal |
|---|---|
| Registrar e conciliar o recebimento | Execução de contrato (art. 7º, V) |
| **Prevenção à fraude** | **Legítimo interesse (art. 7º, IX)** — não consentimento |
| Retenção fiscal de 5 anos | Obrigação legal (art. 7º, II) |

Apoiar prevenção à fraude em consentimento seria errado e frágil: o titular revogaria e
inviabilizaria o controle.

**O melhor controle do projeto:** a RN27 não é política, é schema. `pagador` tem FK para
`lojista` e a chave única é `(id_lojista, documento_hash)`. **Não é possível, por construção,
consultar reputação global.** O controle de privacidade mais forte é o que o modelo de dados
torna impossível.

### Plano de implementação — 17 tasks

Em TDD, cada uma com entregável testável. Ordem pensada para a apresentação: **o banco inteiro
sai nas Tasks 1 e 2**, antes de qualquer lógica — se o prazo apertar, o que mais pontua já está
pronto.

| # | Task |
|---|---|
| 1 | Esqueleto do monorepo e banco subindo |
| 2 | **Schema completo** — 15 tabelas, índices, partições, expurgo |
| 3 | Contratos Zod do domínio canônico |
| 4 | Pseudonimização HMAC |
| 5 | Cliente da API do Asaas |
| 6 | Webhook: token, reconsulta, idempotência |
| 7 | Normalização e persistência |
| 8 | Catálogo das nove regras |
| 9 | Motor de score e veredito |
| 10 | Orquestração da análise e notificação |
| 11 | Devolução assíncrona |
| 12 | Alerta, desfecho, auditoria, direitos do titular |
| 13 | Canal e-commerce |
| 14 | Conciliação do extrato |
| 15 | Gerador de massa sintética |
| 16 | **As oito consultas analíticas** |
| 17 | OpenAPI e roteiro de demonstração |

**Duas decisões que o plano fechou e o spec deixava em aberto:**

1. **A fórmula da renormalização da RN03:**
   `score = min(100, scoreBruto × pesoTotal / pesoApurado)`.
   Ela **infla** o score quando faltam sinais — por isso RN14 e RN21 são o que a torna segura.
2. **Pagador sem documento.** Aplicar HMAC sobre string vazia colapsaria todos os pagadores
   anônimos num hash só, e a RN09 passaria a pontuar o histórico de uma pessoa contra outra. O
   plano deriva hash único por transação a partir do `endToEndId`.

### Cinco classes de entrada que o plano cobre com teste

1. Webhook duplicado **em paralelo** — exige `ON CONFLICT DO NOTHING`, nunca *check-then-insert*
2. Pagamento com data **fora de qualquer partição** — exige partição `DEFAULT`
3. Pagador **sem documento** — não pode colapsar num hash só
4. **Fuso horário** na RN10 — comparar UTC com hora local erra a regra em 3 horas
5. **Escala do valor** — confundir reais com centavos passa silencioso por `NUMERIC(12,2)`

---

## 6. O que falta

### Bloqueia o início da implementação

1. **Escolher o método de execução do plano** — subagente por task (um agente implementa, outro
   revisa, antes da próxima começar) ou implementação direta em sessão com revisão só no fim.
2. **Criar a conta no sandbox do Asaas** e guardar as credenciais fora do repositório.
3. **Inicializar o git** em `Documents\A3_BigData` (seção 1).

### Primeira tarefa da execução, antes da Task 3

4. **Descobrir se o Asaas devolve o nome do pagador mascarado.** Um webhook de teste no sandbox e
   uma olhada no JSON bruto respondem. A documentação pública não especifica.
   **Por que importa:** se vier mascarado, a RN05 — o segundo sinal mais forte — fica indisponível
   na prática, e o peso dela precisa ser redistribuído **antes** da Task 8, não depois.

### Informação que falta do professor

5. **A data de entrega da A3.** O cronograma veio em branco no PDF do enunciado.
6. **O número de integrantes** do grupo (o enunciado permite até 5).

### Decisão de produto

7. **Confirmar o nome.** CONFIA é provisório e trocar não impacta o design.

---

## 7. O que o enunciado exige — conferência

| Exigência | Como está coberta |
|---|---|
| Escolha do banco justificada (3,0) | Seção 4 — quatro camadas de argumento |
| Organização e modelagem (3,0) | 15 tabelas, 3FN provada, dicionário, índices com consumidor |
| Qualidade e governança (1,5) | Cinco dimensões, tratamento de dado sujo, LGPD com base legal |
| Prova de conceito (1,0) | Asaas sandbox + Task 17 (roteiro em 10 passos) |
| Problema e inovação (1,0) | Seção 2 — a reformulação MED |
| Pitch (0,5) | Seções 2 e 4 — a dor e as frases de defesa |
| **≥5 consultas** respondendo perguntas de negócio | **8 consultas** (PN01–PN08), Task 16 |
| Dados fictícios, públicos ou anonimizados | Gerador determinístico (Task 15) + sandbox |

---

## 8. Stack

| Necessidade | Escolha |
|---|---|
| Banco | **PostgreSQL 16** + `pg_cron` + `pg_trgm` |
| Trilho Pix | **Asaas** (sandbox) |
| API | NestJS |
| Acesso a dados | SQL puro / Prisma |
| Contrato e validação | Zod |
| Testes | Vitest |
| Massa sintética | Faker com semente fixa |
| Infra local | Docker Compose — **dois contêineres** |
| Front | Next.js, **depois e à parte** |

Na versão poliglota eram seis contêineres. Caiu para dois, e essa redução é a demonstração
prática do argumento da seção 4.

---

## 9. Declaração de uso de IA

Assistente de IA generativa utilizado como apoio na estruturação dos documentos, na comparação de
alternativas de persistência e na redação. Todas as decisões técnicas, pesos de regra e modelagem
foram revisados e são de domínio da equipe, que responde integralmente por qualquer estrutura ou
linha de código apresentada.
