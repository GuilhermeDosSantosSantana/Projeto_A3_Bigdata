# CONFIA — Antifraude de Pix Recebido · Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o backend completo do CONFIA — ingestão de eventos de Pix recebido, motor de regras de negócio e banco de dados PostgreSQL único — pronto para demonstração ao vivo com Asaas em sandbox, sem front-end.

**Architecture:** Monorepo TypeScript. `packages/contracts` define os schemas Zod do domínio canônico e é a fonte única do contrato. `packages/rules` é o catálogo de 9 regras e o motor de score, puro e sem I/O — é o núcleo autoral e é testável isoladamente. `packages/db` tem as migrations SQL. `apps/api` (NestJS) orquestra: recebe o webhook, reconsulta o Asaas, normaliza, pseudonimiza, apura os sinais, grava a decisão e dispara devolução ou notificação. Um único PostgreSQL 16 é o sistema de registro.

**Tech Stack:** TypeScript, NestJS, PostgreSQL 16 (`pg_cron`, `pg_trgm`), Zod, node-postgres, Vitest, Faker, Docker Compose.

**Spec:** [`docs/superpowers/specs/2026-11-23-confia-antifraude-pix-recebido-design.md`](../specs/2026-11-23-confia-antifraude-pix-recebido-design.md)

## Global Constraints

- **Um único motor de banco: PostgreSQL 16.** Nenhum outro banco, nenhum cache, em nenhuma task (RNF12, seção 3.5 do spec). Se uma task parecer precisar de Redis, ela está errada.
- **Migrations em SQL puro**, numeradas e versionadas em `packages/db/migrations/`. Sem ORM gerando schema — o schema é o entregável avaliado e precisa ser legível na apresentação.
- **Pseudonimização HMAC-SHA256 antes de qualquer escrita em tabela permanente** (RN24). O documento e o nome originais só existem em `ingestao_webhook`.
- **Escopo por `id_lojista` em toda consulta de pagador** (RNF09, RN27). A chave única é `(id_lojista, documento_hash)`. Não existe consulta de reputação global.
- **Score 0–100 com teto em 100.** Faixas: ≤39 APROVADO, 40–74 EM_ANALISE, ≥75 RECUSADO (RN02).
- **Recusa exige ≥2 sinais disparados** (RN14). **Veredito degradado tem teto em EM_ANALISE** (RN21).
- **Retenção:** `ingestao_webhook` 7 dias, `sinal_apurado` 18 meses, `pagamento` e `devolucao` 5 anos (RN26).
- **`auditoria` é append-only.** O usuário de aplicação do banco não recebe `UPDATE` nem `DELETE` nessa tabela.
- **Nenhuma credencial no repositório.** `.env.example` com valores falsos; `.env` no `.gitignore`.
- **O corpo do webhook nunca é fonte da verdade** (seção 6.4). Toda decisão parte da reconsulta na API do Asaas.
- **Orçamento de latência:** p95 do webhook até a notificação ≤ 2 s (RNF01).

## Review Focus

Cinco classes de entrada que o spec implica e que nenhuma task exercitaria por conta própria. Cada linha tem o teste correspondente adicionado à task que possui o código.

1. **Webhook duplicado chegando em paralelo, não em série.** A idempotência por `UNIQUE` protege contra reentrega sequencial; duas requisições concorrentes passam ambas por um `SELECT` de verificação e colidem no `INSERT`. Exige `ON CONFLICT DO NOTHING` seguido de releitura, nunca *check-then-insert*. → Task 6.
2. **Pagamento com `ocorrido_em` fora de qualquer partição existente.** Particionamento declarativo rejeita o `INSERT` com erro, não cria a partição sozinho. Um pagamento com data futura ou antiga derruba a ingestão. Exige partição `DEFAULT`. → Task 2.
3. **Pagador sem documento no payload.** Se o documento vier nulo ou vazio, aplicar HMAC sobre string vazia colapsaria **todos** os pagadores anônimos num único `documento_hash` — e aí RN09 e RN18 passariam a pontuar o histórico de uma pessoa contra outra. Exige pagador anônimo por pagamento, nunca compartilhado. → Task 4.
4. **Fuso horário na RN10.** O Asaas devolve o horário em America/Sao_Paulo; a faixa de operação do lojista é hora local. Comparar `ocorrido_em` em UTC com `hora_abertura` local erra a regra em 3 horas e faz todo pagamento de fim de tarde parecer fora do horário. → Task 8.
5. **Valor com escala errada na borda.** Confundir reais com centavos na leitura do payload é o bug financeiro clássico e passa silencioso por `NUMERIC(12,2)`. Exige teste de borda com valor fracionário. → Task 3.

---

## File Structure

```
confia/
├── docker-compose.yml                   Postgres 16 + extensões; a API roda fora
├── package.json                         workspaces
├── .env.example                         valores falsos
├── packages/
│   ├── contracts/src/
│   │   ├── pagamento.ts                 PagamentoCanonico, Canal, SituacaoEntrega
│   │   ├── veredito.ts                  Veredito, ResultadoSinal, AnaliseRisco
│   │   └── asaas.ts                     schema do payload cru do Asaas
│   ├── db/
│   │   ├── migrations/001..007_*.sql    schema, por responsabilidade
│   │   ├── queries/pn01..pn08.sql       as consultas analíticas
│   │   └── src/pool.ts                  pool do pg, migrate(), reset() para teste
│   └── rules/src/
│       ├── tipos.ts                     Contexto, Regra, ResultadoSinal
│       ├── sinais/rn04..rn12.ts         uma regra por arquivo
│       ├── catalogo.ts                  agrega as 9 regras + versão do catálogo
│       └── motor.ts                     renormalização, teto, veredito
└── apps/api/src/
    ├── asaas/cliente.ts                 reconsulta e estorno
    ├── webhook/controller.ts            token, gravação bruta, idempotência
    ├── ingestao/normalizador.ts         payload → PagamentoCanonico
    ├── ingestao/pseudonimizador.ts      HMAC, normalização de nome, máscara
    ├── ingestao/repositorio.ts          resolve pagador, grava pagamento
    ├── analise/contexto.ts              monta o Contexto a partir do banco
    ├── analise/servico.ts               orquestra a decisão e persiste
    ├── devolucao/servico.ts             solicita, retenta, concilia PIX_REFUND
    ├── ecommerce/servico.ts             cobrança esperada e divergência (canal 2)
    ├── conciliacao/servico.ts           extrato × banco, detecta webhook perdido
    ├── alerta/servico.ts                fila humana, rotulagem, direitos do titular
    ├── auditoria/servico.ts             trilha encadeada
    └── seed/gerador.ts                  massa sintética com fraude plantada
```

---

### Task 1: Esqueleto do monorepo e banco subindo

**Files:**
- Create: `package.json`, `tsconfig.base.json`, `docker-compose.yml`, `.env.example`, `.gitignore`
- Create: `packages/db/src/pool.ts`, `packages/db/migrations/001_cadastro.sql`
- Test: `packages/db/test/migrate.test.ts`

**Interfaces:**
- Consumes: nada.
- Produces: `pool: Pool`, `migrate(): Promise<void>`, `reset(): Promise<void>` em `packages/db/src/pool.ts`. Toda task posterior usa esses três.

A migration 001 cria `lojista`, `usuario` e `conta_recebedora` conforme o modelo lógico de 5.2 do spec. `lojista` carrega `hora_abertura` e `hora_fechamento` como `SMALLINT` (0–23), porque a RN10 compara hora cheia e um `TIME` traria precisão que a regra não usa.

- [ ] **Step 1: Escrever o teste que falha**

```ts
// packages/db/test/migrate.test.ts
it('cria as tabelas de cadastro e exige pg_cron e pg_trgm', async () => {
  await reset(); await migrate();
  const { rows } = await pool.query(
    `SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename`);
  expect(rows.map(r => r.tablename)).toEqual(['conta_recebedora', 'lojista', 'usuario']);

  const ext = await pool.query(`SELECT extname FROM pg_extension ORDER BY extname`);
  expect(ext.rows.map(r => r.extname)).toEqual(expect.arrayContaining(['pg_cron', 'pg_trgm']));
});

it('rejeita hora de operação fora de 0..23', async () => {
  await expect(inserirLojista({ horaAbertura: 24 })).rejects.toThrow();
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `docker compose up -d && npm test -w packages/db`
Expected: FAIL — `relation "pg_tables" ... returns []` ou módulo `pool` inexistente.

- [ ] **Step 3: Escrever `docker-compose.yml`**

Imagem `postgres:16` com `shared_preload_libraries=pg_cron` e `cron.database_name` apontando para o banco da aplicação — `pg_cron` **só carrega via `shared_preload_libraries`**, e sem isso a migration 002 falha mais adiante. Monta `packages/db/migrations` como volume somente leitura.

- [ ] **Step 4: Implementar `pool.ts` com `migrate()` e `reset()`**

`migrate()` lê os arquivos de `migrations/` em ordem lexicográfica e aplica os ainda não registrados numa tabela `schema_migrations (versao, aplicada_em)`. `reset()` dropa o schema `public` e recria — usado só em teste.

- [ ] **Step 5: Escrever `001_cadastro.sql`**

Inclui `CREATE EXTENSION IF NOT EXISTS pg_cron` e `pg_trgm`, as três tabelas, e `CHECK (hora_abertura BETWEEN 0 AND 23)` em ambas as colunas de hora.

- [ ] **Step 6: Rodar e verificar que passa**

Run: `npm test -w packages/db`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add package.json tsconfig.base.json docker-compose.yml .env.example .gitignore packages/db
git commit -m "feat(db): esqueleto do monorepo e migration de cadastro"
```

---

### Task 2: Schema completo — as 15 tabelas, índices, partições e expurgo

**Files:**
- Create: `packages/db/migrations/002_pagamento.sql`, `003_analise.sql`, `004_tratativa.sql`, `005_indices.sql`, `006_retencao.sql`
- Test: `packages/db/test/schema.test.ts`

**Interfaces:**
- Consumes: `migrate()` da Task 1.
- Produces: o schema inteiro. Nenhuma task posterior altera estrutura — só lê e escreve.

Este é o entregável avaliado pelos Eixos 1 e 2. Segue literalmente o modelo lógico de 5.2 e o DDL de 5.3 do spec, incluindo a chave primária composta de `pagamento` e a ausência deliberada de FK entre `ingestao_webhook` e `pagamento`.

- [ ] **Step 1: Escrever o teste que falha**

```ts
// packages/db/test/schema.test.ts
it('tem as 15 tabelas do modelo lógico', async () => {
  const esperadas = ['alerta','analise_risco','auditoria','cobranca_esperada','conta_recebedora',
    'desfecho','devolucao','ingestao_webhook','lojista','notificacao','pagador','pagamento',
    'regra','sinal_apurado','usuario'];
  expect(await nomesDeTabela()).toEqual(expect.arrayContaining(esperadas));
});

it('cria os dois índices parciais das filas', async () => {
  const defs = await definicoesDeIndice();
  expect(defs).toContainEqual(expect.stringMatching(/pagamento.*WHERE.*situacao_entrega = 'RETIDA'/s));
  expect(defs).toContainEqual(expect.stringMatching(/alerta.*WHERE.*situacao = 'ABERTO'/s));
});

it('impede dois pagamentos com o mesmo end_to_end_id no mesmo psp', async () => {
  await inserirPagamento({ endToEndId: 'E1', psp: 'ASAAS' });
  await expect(inserirPagamento({ endToEndId: 'E1', psp: 'ASAAS' }))
    .rejects.toMatchObject({ code: '23505' });
});

it('impede o mesmo documento para o mesmo lojista, mas permite entre lojistas diferentes', async () => {
  await inserirPagador({ idLojista: 1, documentoHash: 'H' });
  await expect(inserirPagador({ idLojista: 1, documentoHash: 'H' }))
    .rejects.toMatchObject({ code: '23505' });
  await expect(inserirPagador({ idLojista: 2, documentoHash: 'H' })).resolves.toBeDefined();
});

// Review Focus 2 — partição ausente
it('aceita pagamento com data fora das partições nomeadas', async () => {
  await expect(inserirPagamento({ ocorridoEm: '2031-07-04T10:00:00Z' })).resolves.toBeDefined();
});

it('expurga ingestao_webhook com mais de 7 dias e preserva o pagamento', async () => {
  await inserirIngestao({ recebidoEm: diasAtras(8) });
  await inserirPagamento({ endToEndId: 'E2' });
  await pool.query(`DELETE FROM ingestao_webhook WHERE expurgar_em < now()`);
  expect(await contar('ingestao_webhook')).toBe(0);
  expect(await contar('pagamento')).toBe(1);
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w packages/db -- schema`
Expected: FAIL — tabelas inexistentes.

- [ ] **Step 3: Escrever `002_pagamento.sql`**

`ingestao_webhook` (com `origem_autenticada`, `confirmado_na_api`, `payload JSONB`, `expurgar_em` como coluna gerada), `pagador`, `pagamento` particionada por range em `ocorrido_em`, `cobranca_esperada`. Cria as partições dos 12 meses do período de demonstração **e uma partição `DEFAULT`** — sem ela, Review Focus 2 derruba a ingestão em produção.

- [ ] **Step 4: Escrever `003_analise.sql`**

`regra`, `analise_risco`, `sinal_apurado`. `sinal_apurado.contribuicao` é `SMALLINT` e `detalhe` é `JSONB`. `analise_risco.id_pagamento` com `UNIQUE` (RN19).

- [ ] **Step 5: Escrever `004_tratativa.sql`**

`alerta`, `desfecho`, `devolucao`, `notificacao`, `auditoria`. `devolucao.situacao` com `CHECK` em `('PENDENTE','CANCELADA','CONCLUIDA')` — o ciclo do Asaas (`PENDING`/`CANCELLED`/`DONE`) traduzido; `tentativas INTEGER NOT NULL DEFAULT 0` e `ultimo_erro TEXT`.

- [ ] **Step 6: Escrever `005_indices.sql`**

Os dez índices da tabela 5.6 do spec, com os dois parciais e o GIN sobre `payload`. Cada `CREATE INDEX` leva um comentário `-- consumidor: RNxx / PNxx` — é o que sustenta a arguição de que nenhum índice é gratuito.

- [ ] **Step 7: Escrever `006_retencao.sql`**

A materialized view `perfil_loja_diario` com índice único em `(id_conta, dia)` — exigido por `REFRESH ... CONCURRENTLY` — e os três agendamentos de `pg_cron`: expurgo diário da ingestão, refresh de 15 em 15 minutos, expurgo mensal de `sinal_apurado`.

- [ ] **Step 8: Rodar e verificar que passa**

Run: `npm test -w packages/db`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add packages/db/migrations packages/db/test
git commit -m "feat(db): schema completo com particionamento, indices parciais e retencao"
```

---

### Task 3: Contratos do domínio canônico

**Files:**
- Create: `packages/contracts/src/pagamento.ts`, `veredito.ts`, `asaas.ts`, `index.ts`
- Test: `packages/contracts/test/asaas.test.ts`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `PagamentoCanonico = { psp, endToEndId, txid: string | null, canal: Canal, valor: number, infoPagador: string | null, ocorridoEm: Date, pagador: { documento: string | null, nome: string | null } }`
  - `Canal = 'PRESENCIAL' | 'ECOMMERCE'`, `Veredito = 'APROVADO' | 'EM_ANALISE' | 'RECUSADO'`
  - `asaasPaymentReceivedSchema: ZodSchema`, `parsearAsaas(bruto: unknown): PagamentoCanonico`

O schema do Asaas é **permissivo por design**: a documentação avisa que novos atributos aparecem com o tempo, então campos desconhecidos passam sem erro e só os que consumimos são validados.

- [ ] **Step 1: Escrever o teste que falha**

```ts
// Review Focus 5 — escala do valor
it('preserva centavos sem arredondar', () => {
  const p = parsearAsaas(fixture({ value: 10.5 }));
  expect(p.valor).toBe(10.5);
  expect(parsearAsaas(fixture({ value: 1050 })).valor).toBe(1050);
});

it('aceita payload com campos desconhecidos', () => {
  expect(() => parsearAsaas(fixture({ campoNovoDoAsaas: 'x' }))).not.toThrow();
});

it('devolve txid nulo quando o QR era estático', () => {
  expect(parsearAsaas(fixture({ externalReference: null })).txid).toBeNull();
});

it('rejeita payload sem end_to_end_id', () => {
  expect(() => parsearAsaas(fixture({ pixTransaction: null }))).toThrow();
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w packages/contracts`
Expected: FAIL — `parsearAsaas` não existe.

- [ ] **Step 3: Implementar os schemas e `parsearAsaas`**

Zod com `.passthrough()` no objeto raiz. O valor é lido como `z.number()` e repassado sem conversão — nenhuma multiplicação por 100 em lugar nenhum do sistema.

- [ ] **Step 4: Rodar e verificar que passa**

Run: `npm test -w packages/contracts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/contracts
git commit -m "feat(contracts): dominio canonico e parser do payload do Asaas"
```

---

### Task 4: Pseudonimização

**Files:**
- Create: `apps/api/src/ingestao/pseudonimizador.ts`
- Test: `apps/api/test/pseudonimizador.test.ts`

**Interfaces:**
- Consumes: `PagamentoCanonico` da Task 3.
- Produces:
  - `hashDocumento(documento: string): string` — HMAC-SHA256 hex, 64 chars
  - `hashNome(nome: string): string`
  - `normalizarNome(nome: string): string`
  - `estaMascarado(nome: string): boolean`
  - `documentoAnonimo(endToEndId: string): string` — hash único por transação

Implementa RN24 e a nota técnica da RN05. A chave HMAC vem de `process.env.CONFIA_HMAC_KEY` e a ausência dela deve **lançar na inicialização**, não gerar hash com chave vazia.

- [ ] **Step 1: Escrever o teste que falha**

```ts
it('produz hash estável de 64 caracteres', () => {
  expect(hashDocumento('12345678901')).toHaveLength(64);
  expect(hashDocumento('12345678901')).toBe(hashDocumento('12345678901'));
});

it('normaliza grafia antes do hash', () => {
  expect(hashNome('José  da Silva')).toBe(hashNome('JOSE DA SILVA'));
});

it('reconhece nome mascarado', () => {
  expect(estaMascarado('J*** S*** SILVA')).toBe(true);
  expect(estaMascarado('JOSE DA SILVA')).toBe(false);
});

// Review Focus 3 — pagador sem documento
it('não colapsa pagadores anônimos num único hash', () => {
  const a = documentoAnonimo('E2E-AAA');
  const b = documentoAnonimo('E2E-BBB');
  expect(a).not.toBe(b);
  expect(a).not.toBe(hashDocumento(''));
});

it('lança se a chave HMAC não estiver configurada', () => {
  delete process.env.CONFIA_HMAC_KEY;
  expect(() => carregarChave()).toThrow(/CONFIA_HMAC_KEY/);
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w apps/api -- pseudonimizador`
Expected: FAIL

- [ ] **Step 3: Implementar o módulo**

`normalizarNome` aplica maiúsculas, remove acentos por `normalize('NFD')` e colapsa espaços. `estaMascarado` detecta a presença de `*`. `documentoAnonimo` deriva do `endToEndId`, que é único por transação — garantindo que cada pagamento sem documento vire um pagador distinto.

- [ ] **Step 4: Rodar e verificar que passa**

Run: `npm test -w apps/api -- pseudonimizador`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ingestao/pseudonimizador.ts apps/api/test/pseudonimizador.test.ts
git commit -m "feat(ingestao): pseudonimizacao HMAC com tratamento de pagador anonimo"
```

---

### Task 5: Cliente da API do Asaas

**Files:**
- Create: `apps/api/src/asaas/cliente.ts`
- Test: `apps/api/test/asaas-cliente.test.ts`

**Interfaces:**
- Consumes: `PagamentoCanonico` da Task 3.
- Produces:
  - `consultarPagamento(id: string): Promise<AsaasPagamento | null>` — `null` quando o Asaas devolve 404
  - `solicitarEstorno(id: string, valor: number): Promise<{ situacao: SituacaoEstorno, idExterno: string }>`
  - `type SituacaoEstorno = 'PENDENTE' | 'CANCELADA' | 'CONCLUIDA'`
  - `class SaldoIndisponivelError extends Error`

É o que viabiliza o controle da seção 6.4 do spec. O erro 400 por saldo indisponível no estorno é **esperado e recuperável** — vira `SaldoIndisponivelError`, que a Task 10 trata como retentativa, nunca como falha.

- [ ] **Step 1: Escrever o teste que falha**

```ts
it('devolve null quando o pagamento não existe', async () => {
  servidorFalso.get('/v3/payments/pay_x').responde(404, {});
  expect(await consultarPagamento('pay_x')).toBeNull();
});

it('traduz o ciclo de status do estorno', async () => {
  servidorFalso.post('/v3/payments/pay_1/refund').responde(200, { status: 'PENDING' });
  expect((await solicitarEstorno('pay_1', 10)).situacao).toBe('PENDENTE');
});

it('converte 400 de saldo indisponível em SaldoIndisponivelError', async () => {
  servidorFalso.post('/v3/payments/pay_1/refund')
    .responde(400, { errors: [{ code: 'invalid_value', description: 'Saldo indisponível' }] });
  await expect(solicitarEstorno('pay_1', 10)).rejects.toBeInstanceOf(SaldoIndisponivelError);
});

it('envia a credencial no cabeçalho access_token e nunca na URL', async () => {
  await consultarPagamento('pay_1');
  expect(servidorFalso.ultimaRequisicao.headers['access_token']).toBeDefined();
  expect(servidorFalso.ultimaRequisicao.url).not.toContain('token');
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w apps/api -- asaas-cliente`
Expected: FAIL

- [ ] **Step 3: Implementar o cliente**

`fetch` nativo com base URL de `process.env.ASAAS_BASE_URL`. Distingue o 400 de saldo pela descrição do erro; qualquer outro 400 propaga como erro comum.

- [ ] **Step 4: Rodar e verificar que passa**

Run: `npm test -w apps/api -- asaas-cliente`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/asaas apps/api/test/asaas-cliente.test.ts
git commit -m "feat(asaas): cliente de consulta e estorno com tratamento de saldo indisponivel"
```

---

### Task 6: Recepção do webhook, autenticação e idempotência

**Files:**
- Create: `apps/api/src/webhook/controller.ts`, `apps/api/src/webhook/guard.ts`
- Test: `apps/api/test/webhook.test.ts`

**Interfaces:**
- Consumes: `pool` (Task 1), `parsearAsaas` (Task 3), `consultarPagamento` (Task 5).
- Produces: `POST /api/v1/webhook/asaas`; `registrarIngestao(payload: unknown, autenticada: boolean): Promise<number>` devolvendo `id_ingestao`.

Implementa a seção 6.4 do spec. Três camadas: confere o token em tempo constante, grava o bruto **sempre** (inclusive o não autenticado, para investigação), e reconsulta o Asaas antes de deixar o evento seguir.

- [ ] **Step 1: Escrever o teste que falha**

```ts
it('rejeita token inválido mas registra a tentativa', async () => {
  const r = await post('/api/v1/webhook/asaas', fixture(), { 'asaas-access-token': 'errado' });
  expect(r.status).toBe(401);
  const { rows } = await pool.query(`SELECT origem_autenticada, situacao_processamento FROM ingestao_webhook`);
  expect(rows[0]).toMatchObject({ origem_autenticada: false, situacao_processamento: 'REJEITADO' });
});

it('compara o token em tempo constante', () => {
  expect(fonteDe(compararToken)).toContain('timingSafeEqual');
});

it('rejeita o evento quando a reconsulta não encontra o pagamento', async () => {
  servidorFalso.get('/v3/payments/pay_1').responde(404, {});
  const r = await post('/api/v1/webhook/asaas', fixture({ id: 'pay_1' }), cabecalhoValido);
  expect(r.status).toBe(202);
  expect(await situacaoDaIngestao()).toBe('REJEITADO');
  expect(await contar('pagamento')).toBe(0);
});

it('rejeita o evento quando o valor da API diverge do corpo', async () => {
  servidorFalso.get('/v3/payments/pay_1').responde(200, { id: 'pay_1', value: 999 });
  await post('/api/v1/webhook/asaas', fixture({ id: 'pay_1', value: 10 }), cabecalhoValido);
  expect(await situacaoDaIngestao()).toBe('REJEITADO');
});

// Review Focus 1 — reentrega concorrente
it('grava um único pagamento sob duas entregas simultâneas', async () => {
  const corpo = fixture({ endToEndId: 'E2E-1' });
  await Promise.all([
    post('/api/v1/webhook/asaas', corpo, cabecalhoValido),
    post('/api/v1/webhook/asaas', corpo, cabecalhoValido),
  ]);
  expect(await contar('pagamento')).toBe(1);
  expect(await contar('analise_risco')).toBe(1);
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w apps/api -- webhook`
Expected: FAIL

- [ ] **Step 3: Implementar o guard com `crypto.timingSafeEqual`**

Compara o cabeçalho `asaas-access-token` com `process.env.ASAAS_WEBHOOK_TOKEN`. Comprimentos diferentes são igualados antes da comparação para não vazar tamanho.

- [ ] **Step 4: Implementar o controller**

Grava em `ingestao_webhook`, reconsulta o Asaas, compara `id` e `value`, e só então encaminha. A gravação do pagamento usa `INSERT ... ON CONFLICT (psp, end_to_end_id, ocorrido_em) DO NOTHING RETURNING id_pagamento`; quando nada retorna, relê o pagamento existente e devolve o resultado original — **nunca** um `SELECT` antes do `INSERT`.

- [ ] **Step 5: Rodar e verificar que passa**

Run: `npm test -w apps/api -- webhook`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/webhook apps/api/test/webhook.test.ts
git commit -m "feat(webhook): autenticacao por token, reconsulta na API e idempotencia concorrente"
```

---

### Task 7: Normalização e persistência da ingestão

**Files:**
- Create: `apps/api/src/ingestao/normalizador.ts`, `apps/api/src/ingestao/repositorio.ts`
- Test: `apps/api/test/ingestao.test.ts`

**Interfaces:**
- Consumes: `PagamentoCanonico` (Task 3), pseudonimizador (Task 4).
- Produces:
  - `resolverPagador(idLojista: number, p: PagamentoCanonico): Promise<number>` — cria ou recupera, devolve `id_pagador`
  - `gravarPagamento(idConta: number, idPagador: number, p: PagamentoCanonico): Promise<number>`

`resolverPagador` é onde os contadores desnormalizados de 5.7 do spec são mantidos: `qtd_pagamentos` é incrementado **na mesma transação** do pagamento, ou diverge.

- [ ] **Step 1: Escrever o teste que falha**

```ts
it('reaproveita o pagador do mesmo documento no mesmo lojista', async () => {
  const a = await resolverPagador(1, canonico({ documento: '111' }));
  const b = await resolverPagador(1, canonico({ documento: '111' }));
  expect(a).toBe(b);
});

it('cria pagadores distintos para o mesmo documento em lojistas distintos', async () => {
  expect(await resolverPagador(1, canonico({ documento: '111' })))
    .not.toBe(await resolverPagador(2, canonico({ documento: '111' })));
});

it('incrementa qtd_pagamentos na mesma transação do pagamento', async () => {
  const id = await resolverPagador(1, canonico({ documento: '111' }));
  await gravarPagamento(1, id, canonico({ documento: '111', endToEndId: 'E1' }));
  await gravarPagamento(1, id, canonico({ documento: '111', endToEndId: 'E2' }));
  expect(await campo('pagador', id, 'qtd_pagamentos')).toBe(2);
});

it('não persiste documento nem nome em claro em pagador', async () => {
  await resolverPagador(1, canonico({ documento: '12345678901', nome: 'JOSE' }));
  const { rows } = await pool.query(`SELECT documento_hash, nome_hash FROM pagador`);
  expect(rows[0].documento_hash).not.toContain('12345678901');
  expect(rows[0].nome_hash).not.toContain('JOSE');
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w apps/api -- ingestao`
Expected: FAIL

- [ ] **Step 3: Implementar `resolverPagador` e `gravarPagamento`**

`resolverPagador` usa `INSERT ... ON CONFLICT (id_lojista, documento_hash) DO UPDATE SET ultimo_pagamento_em = excluded.ultimo_pagamento_em RETURNING id_pagador` — um só round-trip e sem corrida. Pagamento sem documento usa `documentoAnonimo(endToEndId)`.

- [ ] **Step 4: Rodar e verificar que passa**

Run: `npm test -w apps/api -- ingestao`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ingestao apps/api/test/ingestao.test.ts
git commit -m "feat(ingestao): resolucao de pagador escopada por lojista e persistencia do pagamento"
```

---

### Task 8: Catálogo das 9 regras

**Files:**
- Create: `packages/rules/src/tipos.ts`, `packages/rules/src/sinais/rn04.ts` … `rn12.ts`, `packages/rules/src/catalogo.ts`
- Test: `packages/rules/test/sinais.test.ts`

**Interfaces:**
- Consumes: `PagamentoCanonico` (Task 3).
- Produces:
  - ```ts
    type Contexto = {
      pagamento: PagamentoCanonico;
      identidade: { nomeHash: string | null; mascarado: boolean;
                    nomesAnterioresHash: string[]; algumAnteriorMascarado: boolean };
      pagador: { qtdPagamentos: number; qtdContestacoes: number; primeiroPagamentoEm: Date | null };
      perfilLoja: { p95: number; p99: number; medianaQtd: number } | null;
      janela: { pagamentosUltimos10min: number; menorValorUltimos30min: number | null;
                contasDistintasUltimas24h: number; qtdNaFaixaUltimos15min: number };
      lojista: { horaAbertura: number; horaFechamento: number; fuso: string };
    };
    ```
  - `type ResultadoSinal = { disparou: true, contribuicao: number, detalhe: object } | { disparou: false } | { indisponivel: true, motivo: string }`
  - `type Regra = { codigo: string, peso: number, descricao: string, avaliar(ctx: Contexto): ResultadoSinal }`
  - `CATALOGO: Regra[]`, `VERSAO_CATALOGO: string`
  - `carregarCatalogo(idLojista: number, em: Date): Promise<Regra[]>` — filtra por `ativa` e vigência (RF13)
  - `simular(ctx: Contexto, catalogo: Regra[]): Map<string, ResultadoSinal>` — apura sem persistir (RF13)

Núcleo autoral. Pesos exatos da tabela 4.3 do spec: RN04 25, RN05 35, RN06 25, RN07 15, RN08 30, RN09 40, RN10 10, RN11 12, RN12 15. `perfilLoja` nulo significa agregado indisponível — as regras que dependem dele devolvem `indisponivel`, nunca `disparou: false`.

O campo `identidade` existe porque a RN05 precisa comparar o nome atual com os anteriores **e** saber se algum dos dois estava mascarado — sem isso ela não tem como devolver `indisponivel` conforme a nota técnica de 4.3 do spec.

- [ ] **Step 1: Escrever o teste que falha**

```ts
it('RN09 dispara com 40 para pagador com contestação prévia', () => {
  expect(rn09.avaliar(ctx({ pagador: { qtdContestacoes: 1 } })))
    .toMatchObject({ disparou: true, contribuicao: 40 });
});

it('RN05 fica indisponível quando qualquer nome está mascarado', () => {
  expect(rn05.avaliar(ctx({ nomeAtual: 'J*** S***', nomeAnterior: 'JOSE SILVA' })))
    .toMatchObject({ indisponivel: true });
});

it('RN04 exige pagador novo E valor acima do p95', () => {
  expect(rn04.avaliar(ctx({ pagador: { qtdPagamentos: 0 }, perfilLoja: { p95: 100 }, valor: 150 })))
    .toMatchObject({ disparou: true, contribuicao: 25 });
  expect(rn04.avaliar(ctx({ pagador: { qtdPagamentos: 9 }, perfilLoja: { p95: 100 }, valor: 150 })))
    .toMatchObject({ disparou: false });
});

it('RN07 fica indisponível sem perfil da loja', () => {
  expect(rn07.avaliar(ctx({ perfilLoja: null }))).toMatchObject({ indisponivel: true });
});

it('RN08 dispara na sonda: R$ 2 seguido de R$ 400', () => {
  expect(rn08.avaliar(ctx({ janela: { menorValorUltimos30min: 2 }, valor: 400 })))
    .toMatchObject({ disparou: true, contribuicao: 30 });
});

// Review Focus 4 — fuso horário
it('RN10 avalia a hora no fuso do lojista, não em UTC', () => {
  // 2026-11-23T23:30:00Z = 20h30 em São Paulo → dentro de 08h–21h
  const r = rn10.avaliar(ctx({
    ocorridoEm: new Date('2026-11-23T23:30:00Z'),
    lojista: { horaAbertura: 8, horaFechamento: 21, fuso: 'America/Sao_Paulo' },
  }));
  expect(r).toMatchObject({ disparou: false });
});

it('o catálogo tem 9 regras e soma 207 de peso', () => {
  expect(CATALOGO).toHaveLength(9);
  expect(CATALOGO.reduce((s, r) => s + r.peso, 0)).toBe(207);
});

// RF13 — ativação e simulação
it('carregarCatalogo omite regra inativa e regra fora de vigência', async () => {
  await desativarRegra('RN12');
  await definirVigencia('RN11', { fim: ontem() });
  const c = await carregarCatalogo(1, new Date());
  expect(c.map(r => r.codigo)).not.toContain('RN12');
  expect(c.map(r => r.codigo)).not.toContain('RN11');
});

it('simular apura sem gravar nada', async () => {
  const antes = await contar('analise_risco');
  const r = simular(ctx({ pagador: { qtdContestacoes: 1 } }), CATALOGO);
  expect(r.get('RN09')).toMatchObject({ disparou: true });
  expect(await contar('analise_risco')).toBe(antes);
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w packages/rules -- sinais`
Expected: FAIL

- [ ] **Step 3: Implementar as nove regras, uma por arquivo**

Funções puras, sem I/O. A RN10 converte `ocorridoEm` para o fuso do lojista com `Intl.DateTimeFormat` antes de extrair a hora — comparar `getUTCHours()` com hora local é exatamente o defeito do Review Focus 4.

- [ ] **Step 4: Implementar `catalogo.ts` com `carregarCatalogo` e `simular`**

Exporta o array e `VERSAO_CATALOGO` como string semântica (`'1.0.0'`), gravada em `analise_risco.versao_catalogo` para reprodutibilidade (RNF06). `carregarCatalogo` cruza `CATALOGO` com a tabela `regra` filtrando `ativa = true` e `em BETWEEN vigencia_inicio AND coalesce(vigencia_fim, 'infinity')` — o código da regra vive no TypeScript, a ativação vive no banco. `simular` é `apurar` sem a transação de persistência, e serve para calibrar peso sem decidir nada.

- [ ] **Step 5: Rodar e verificar que passa**

Run: `npm test -w packages/rules`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/rules/src/tipos.ts packages/rules/src/sinais packages/rules/src/catalogo.ts packages/rules/test
git commit -m "feat(rules): catalogo das nove regras de risco com tratamento de sinal indisponivel"
```

---

### Task 9: Motor de score e veredito

**Files:**
- Create: `packages/rules/src/motor.ts`
- Test: `packages/rules/test/motor.test.ts`

**Interfaces:**
- Consumes: `CATALOGO`, `ResultadoSinal` (Task 8).
- Produces:
  - `apurar(ctx: Contexto): Map<string, ResultadoSinal>`
  - `calcularScore(resultados): { score: number, degradada: boolean, qtdDisparados: number }`
  - `decidir(s: { score, degradada, qtdDisparados }, tetoConfianca: boolean): Veredito`

Implementa RN02, RN03, RN14, RN18 e RN21. **A renormalização da RN03 é a decisão que o spec não fecha e este plano fecha:**

```
pesoApurado  = Σ peso das regras que devolveram disparou (true ou false)
pesoTotal    = Σ peso de todas as regras do catálogo (207)
scoreBruto   = Σ contribuicao das que dispararam
score        = min(100, round(scoreBruto × pesoTotal / pesoApurado))
degradada    = pesoApurado < pesoTotal
```

A renormalização infla o score quando faltam sinais — por isso RN14 e RN21 são o que a torna segura, e os testes abaixo fixam exatamente esse acoplamento.

- [ ] **Step 1: Escrever o teste que falha**

```ts
it('aplica as faixas da RN02', () => {
  expect(decidir({ score: 39, degradada: false, qtdDisparados: 2 }, false)).toBe('APROVADO');
  expect(decidir({ score: 40, degradada: false, qtdDisparados: 2 }, false)).toBe('EM_ANALISE');
  expect(decidir({ score: 75, degradada: false, qtdDisparados: 2 }, false)).toBe('RECUSADO');
});

it('RN14: não recusa com um único sinal, por mais alto que seja o score', () => {
  expect(decidir({ score: 100, degradada: false, qtdDisparados: 1 }, false)).toBe('EM_ANALISE');
});

it('RN21: degradada nunca recusa', () => {
  expect(decidir({ score: 100, degradada: true, qtdDisparados: 3 }, false)).toBe('EM_ANALISE');
});

it('RN18: teto de confiança impede recusa automática', () => {
  expect(decidir({ score: 90, degradada: false, qtdDisparados: 3 }, true)).toBe('EM_ANALISE');
});

it('RN03: renormaliza pelos pesos apurados e marca degradada', () => {
  const r = new Map([
    ['RN09', { disparou: true, contribuicao: 40, detalhe: {} }],
    ['RN07', { indisponivel: true, motivo: 'perfil ausente' }],
  ]);
  const s = calcularScore(r);
  expect(s.degradada).toBe(true);
  expect(s.score).toBe(100); // 40 × 207/40, limitado a 100
  expect(s.qtdDisparados).toBe(1);
});

it('RN09 + RN05 somam exatamente o piso de recusa', () => {
  const s = calcularScore(new Map([
    ['RN09', { disparou: true, contribuicao: 40, detalhe: {} }],
    ['RN05', { disparou: true, contribuicao: 35, detalhe: {} }],
    ...demaisRegrasNaoDispararam(),
  ]));
  expect(s.score).toBe(75);
  expect(decidir(s, false)).toBe('RECUSADO');
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w packages/rules -- motor`
Expected: FAIL

- [ ] **Step 3: Implementar `calcularScore` e `decidir`**

A fórmula está fixada acima. `decidir` aplica, em ordem: faixa da RN02; depois rebaixa para `EM_ANALISE` se `qtdDisparados < 2`, `degradada`, ou `tetoConfianca`.

- [ ] **Step 4: Rodar e verificar que passa**

Run: `npm test -w packages/rules`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/rules/src/motor.ts packages/rules/test/motor.test.ts
git commit -m "feat(rules): motor de score com renormalizacao e guardas de recusa"
```

---

### Task 10: Orquestração da análise e notificação

**Files:**
- Create: `apps/api/src/analise/contexto.ts`, `apps/api/src/analise/servico.ts`, `apps/api/src/notificacao/servico.ts`
- Test: `apps/api/test/analise.test.ts`

**Interfaces:**
- Consumes: `apurar`, `calcularScore`, `decidir` (Tasks 8–9); repositório (Task 7).
- Produces: `analisar(idPagamento: number): Promise<{ veredito: Veredito, idAnalise: number }>`; `notificar(idPagamento, veredito): Promise<void>`

`montarContexto` lê `perfil_loja_diario` (a materialized view), o histórico do pagador e a janela de 10/30 minutos. Se a view estiver vazia ou obsoleta, devolve `perfilLoja: null` — e é assim que a degradação da RN03 acontece de verdade, não por exceção.

- [ ] **Step 1: Escrever o teste que falha**

```ts
it('persiste uma linha de sinal_apurado por regra do catálogo, inclusive as que não dispararam', async () => {
  const { idAnalise } = await analisar(idPagamento);
  expect(await contar('sinal_apurado', { id_analise: idAnalise })).toBe(9);
});

it('grava a versão do catálogo e a latência', async () => {
  const { idAnalise } = await analisar(idPagamento);
  const a = await buscar('analise_risco', idAnalise);
  expect(a.versao_catalogo).toBe(VERSAO_CATALOGO);
  expect(a.latencia_ms).toBeGreaterThanOrEqual(0);
});

it('marca degradada quando o perfil da loja não existe', async () => {
  await pool.query(`REFRESH MATERIALIZED VIEW perfil_loja_diario`); // vazia
  const { idAnalise } = await analisar(idPagamento);
  expect((await buscar('analise_risco', idAnalise)).degradada).toBe(true);
});

it('mantém a entrega RETIDA enquanto o veredito não for APROVADO', async () => {
  await analisar(idPagamentoSuspeito);
  expect(await campo('pagamento', idPagamentoSuspeito, 'situacao_entrega')).toBe('RETIDA');
});

it('libera a entrega no veredito APROVADO', async () => {
  await analisar(idPagamentoLimpo);
  expect(await campo('pagamento', idPagamentoLimpo, 'situacao_entrega')).toBe('LIBERADA');
});

it('registra notificação com os motivos em texto', async () => {
  await analisar(idPagamentoSuspeito);
  const n = await ultimaLinha('notificacao');
  expect(n.conteudo).toContain('Em análise');
  expect(n.conteudo).toMatch(/contestação|valor acima/i);
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w apps/api -- analise`
Expected: FAIL

- [ ] **Step 3: Implementar `montarContexto`**

Uma consulta por fonte: perfil da loja na view, histórico em `pagador`, janela em `pagamento` com `count` e `min(valor)` filtrados por intervalo. `tetoConfianca` da RN18 sai de `qtd_pagamentos >= 3 AND qtd_contestacoes = 0 AND primeiro_pagamento_em <= now() - interval '180 days'`.

- [ ] **Step 4: Implementar `analisar`**

Tudo numa transação: grava `analise_risco`, as 9 linhas de `sinal_apurado`, atualiza `situacao_entrega`, e enfileira notificação. Mede a latência com `performance.now()`.

- [ ] **Step 5: Implementar `notificar`**

Monta o texto a partir das regras disparadas, usando `regra.descricao`. Grava em `notificacao`; o envio real fica para quando houver app.

- [ ] **Step 6: Rodar e verificar que passa**

Run: `npm test -w apps/api -- analise`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add apps/api/src/analise apps/api/src/notificacao apps/api/test/analise.test.ts
git commit -m "feat(analise): orquestracao da decisao com degradacao e notificacao explicavel"
```

---

### Task 11: Devolução assíncrona

**Files:**
- Create: `apps/api/src/devolucao/servico.ts`
- Test: `apps/api/test/devolucao.test.ts`

**Interfaces:**
- Consumes: `solicitarEstorno`, `SaldoIndisponivelError` (Task 5).
- Produces: `solicitarDevolucao(idPagamento: number, motivo: string): Promise<number>`; `reprocessarPendentes(): Promise<number>`; `conciliarRefund(payload: unknown): Promise<void>`

Implementa a RN16 reescrita. Saldo indisponível é retentativa, não falha, e a entrega continua `RETIDA` até a devolução concluir.

- [ ] **Step 1: Escrever o teste que falha**

```ts
it('deixa a devolução PENDENTE quando o saldo está indisponível', async () => {
  asaasFalso.estornoFalhaPorSaldo();
  const id = await solicitarDevolucao(idPagamento, 'RECUSADO por risco');
  const d = await buscar('devolucao', id);
  expect(d).toMatchObject({ situacao: 'PENDENTE', tentativas: 1 });
  expect(d.ultimo_erro).toMatch(/saldo/i);
});

it('retenta a pendente e conclui quando o saldo aparece', async () => {
  asaasFalso.estornoFalhaPorSaldo();
  const id = await solicitarDevolucao(idPagamento, 'x');
  asaasFalso.estornoConclui();
  expect(await reprocessarPendentes()).toBe(1);
  expect((await buscar('devolucao', id)).tentativas).toBe(2);
});

it('mantém a entrega RETIDA até a devolução concluir', async () => {
  asaasFalso.estornoFalhaPorSaldo();
  await solicitarDevolucao(idPagamento, 'x');
  expect(await campo('pagamento', idPagamento, 'situacao_entrega')).toBe('RETIDA');
});

it('PIX_REFUND com status DONE marca DEVOLVIDA e concluida_em', async () => {
  const id = await solicitarDevolucao(idPagamento, 'x');
  await conciliarRefund({ event: 'PIX_REFUND', refund: { id: 'ref_1', status: 'DONE' } });
  expect((await buscar('devolucao', id)).concluida_em).not.toBeNull();
  expect(await campo('pagamento', idPagamento, 'situacao_entrega')).toBe('DEVOLVIDA');
});

it('não duplica devolução para o mesmo pagamento', async () => {
  await solicitarDevolucao(idPagamento, 'x');
  await solicitarDevolucao(idPagamento, 'x');
  expect(await contar('devolucao', { id_pagamento: idPagamento })).toBe(1);
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w apps/api -- devolucao`
Expected: FAIL

- [ ] **Step 3: Implementar o serviço**

`reprocessarPendentes` busca `situacao='PENDENTE'` com recuo exponencial por `tentativas`, agendado por `pg_cron` chamando um endpoint interno — mantém o agendamento no mesmo motor, sem fila externa.

- [ ] **Step 4: Rodar e verificar que passa**

Run: `npm test -w apps/api -- devolucao`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/devolucao apps/api/test/devolucao.test.ts
git commit -m "feat(devolucao): estorno assincrono com retentativa por saldo e conciliacao de PIX_REFUND"
```

---

### Task 12: Alerta, desfecho e auditoria encadeada

**Files:**
- Create: `apps/api/src/alerta/servico.ts`, `apps/api/src/auditoria/servico.ts`
- Test: `apps/api/test/alerta.test.ts`, `apps/api/test/auditoria.test.ts`

**Interfaces:**
- Consumes: `pool` (Task 1).
- Produces: `abrirAlerta(idAnalise): Promise<number>`; `rotular(idAlerta, rotulo, justificativa, ator): Promise<void>`; `registrar(evento): Promise<void>`; `verificarCadeia(idLojista): Promise<boolean>`; `atenderTitular(documentoHash, acao: 'ACESSO' | 'ELIMINACAO'): Promise<RespostaTitular>`

Implementa RN19, RN20, RN23, RN28 e RF18. A cadeia de hash de `auditoria` é o que torna adulteração detectável.

`atenderTitular` com `ELIMINACAO` **bloqueia em vez de apagar** enquanto a retenção fiscal de 5 anos da RN26 estiver corrente, e devolve a base legal na resposta — é a resposta correta pela LGPD, não uma evasiva, e está em 7.4 do spec.

- [ ] **Step 1: Escrever o teste que falha**

```ts
it('exige justificativa ao rotular', async () => {
  await expect(rotular(idAlerta, 'LEGITIMO', '', 'ana')).rejects.toThrow(/justificativa/i);
});

it('rotular FRAUDE incrementa qtd_contestacoes do pagador (RN23)', async () => {
  await rotular(idAlerta, 'FRAUDE', 'conta de laranja', 'ana');
  expect(await campo('pagador', idPagador, 'qtd_contestacoes')).toBe(1);
});

it('não altera a análise original ao rotular (RN19)', async () => {
  const antes = await buscar('analise_risco', idAnalise);
  await rotular(idAlerta, 'LEGITIMO', 'cliente conhecido', 'ana');
  expect(await buscar('analise_risco', idAnalise)).toEqual(antes);
});

it('encadeia o hash de auditoria e detecta adulteração', async () => {
  await registrar({ idLojista: 1, entidade: 'analise_risco', acao: 'DECIDIU', ator: 'sistema' });
  await registrar({ idLojista: 1, entidade: 'alerta', acao: 'ABRIU', ator: 'sistema' });
  expect(await verificarCadeia(1)).toBe(true);
  await pool.query(`UPDATE auditoria SET acao='X' WHERE id_auditoria=1`); // via superusuário
  expect(await verificarCadeia(1)).toBe(false);
});

it('a aplicação não consegue apagar auditoria', async () => {
  await expect(poolDaAplicacao.query(`DELETE FROM auditoria`))
    .rejects.toMatchObject({ code: '42501' });
});

// RF18 — direitos do titular
it('ACESSO devolve o que existe sobre o titular e gera evento de auditoria', async () => {
  const r = await atenderTitular(hashDocumento('111'), 'ACESSO');
  expect(r.pagamentos.length).toBeGreaterThan(0);
  expect(await ultimaLinha('auditoria')).toMatchObject({ acao: 'ACESSO_TITULAR' });
});

it('ELIMINACAO bloqueia em vez de apagar dentro da retenção fiscal', async () => {
  const r = await atenderTitular(hashDocumento('111'), 'ELIMINACAO');
  expect(r.situacao).toBe('BLOQUEADO');
  expect(r.baseLegal).toMatch(/art\. 7º, II/);
  expect(await contar('pagamento')).toBeGreaterThan(0);
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w apps/api -- 'alerta|auditoria'`
Expected: FAIL

- [ ] **Step 3: Criar o papel de aplicação na migration**

`REVOKE UPDATE, DELETE ON auditoria FROM confia_app`. O teste acima só passa com um pool conectado como `confia_app`, separado do pool de migração.

- [ ] **Step 4: Implementar os dois serviços**

`registrar` calcula `payload_hash` sobre o evento e `hash_anterior` lendo o último registro do mesmo lojista. `verificarCadeia` recomputa a sequência e compara.

- [ ] **Step 5: Rodar e verificar que passa**

Run: `npm test -w apps/api -- 'alerta|auditoria'`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/alerta apps/api/src/auditoria apps/api/test packages/db/migrations
git commit -m "feat(alerta): rotulagem auditada e trilha encadeada append-only"
```

---

### Task 13: Canal e-commerce — cobrança esperada e divergência de valor

**Files:**
- Create: `apps/api/src/ecommerce/controller.ts`, `apps/api/src/ecommerce/servico.ts`
- Test: `apps/api/test/ecommerce.test.ts`

**Interfaces:**
- Consumes: repositório (Task 7), `analisar` (Task 10).
- Produces:
  - `POST /api/v1/cobrancas` → `registrarCobranca(idConta, txid, valorEsperado, referenciaPedido, expiraEm): Promise<number>`
  - `conferirValor(idPagamento): Promise<{ divergente: boolean, diferenca: number } | null>` — `null` no canal PRESENCIAL

Implementa RF15 e RN22, e é o que faz valer a promessa de 5.4 do spec: **os dois canais nas mesmas tabelas**, com o canal como atributo. É também a resposta pronta para "isso serve só para loja física?".

A divergência de valor é **operacional, não de risco**: o valor foi definido pelo sistema do lojista, então a diferença é erro de integração dele. Não entra no score, não vira sinal, não muda o veredito.

- [ ] **Step 1: Escrever o teste que falha**

```ts
it('amarra o pagamento à cobrança pelo txid', async () => {
  await registrarCobranca(1, 'TXID-1', 100, 'pedido-9', amanha());
  const id = await gravarPagamento(1, idPagador, canonico({ txid: 'TXID-1', canal: 'ECOMMERCE', valor: 100 }));
  expect(await conferirValor(id)).toMatchObject({ divergente: false, diferenca: 0 });
});

it('aponta divergência quando o valor pago difere do esperado', async () => {
  await registrarCobranca(1, 'TXID-2', 100, 'pedido-10', amanha());
  const id = await gravarPagamento(1, idPagador, canonico({ txid: 'TXID-2', canal: 'ECOMMERCE', valor: 50 }));
  expect(await conferirValor(id)).toMatchObject({ divergente: true, diferenca: -50 });
});

// RN22 — não se aplica ao presencial
it('devolve null no canal PRESENCIAL, mesmo sem txid', async () => {
  const id = await gravarPagamento(1, idPagador, canonico({ txid: null, canal: 'PRESENCIAL', valor: 50 }));
  expect(await conferirValor(id)).toBeNull();
});

it('divergência não altera o score nem o veredito', async () => {
  await registrarCobranca(1, 'TXID-3', 100, 'pedido-11', amanha());
  const id = await gravarPagamento(1, idPagador, canonico({ txid: 'TXID-3', canal: 'ECOMMERCE', valor: 10 }));
  const { idAnalise } = await analisar(id);
  expect(await contar('sinal_apurado', { id_analise: idAnalise })).toBe(9);
  expect(await buscarSinal(idAnalise, 'RN22')).toBeUndefined();
});

it('recusa cobrança com txid repetido na mesma conta', async () => {
  await registrarCobranca(1, 'TXID-4', 100, 'p1', amanha());
  await expect(registrarCobranca(1, 'TXID-4', 100, 'p2', amanha()))
    .rejects.toMatchObject({ code: '23505' });
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w apps/api -- ecommerce`
Expected: FAIL

- [ ] **Step 3: Acrescentar o `UNIQUE (id_conta, txid)` em `cobranca_esperada`**

Nova migration `007_cobranca_unique.sql`. O schema da Task 2 criou a tabela sem essa restrição; o teste acima a exige.

- [ ] **Step 4: Implementar `registrarCobranca` e `conferirValor`**

`conferirValor` retorna cedo com `null` quando `canal <> 'ECOMMERCE'` ou quando não existe cobrança para o `txid` — ausência de cobrança não é divergência.

- [ ] **Step 5: Rodar e verificar que passa**

Run: `npm test -w apps/api -- ecommerce`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ecommerce apps/api/test/ecommerce.test.ts packages/db/migrations/007_cobranca_unique.sql
git commit -m "feat(ecommerce): cobranca esperada e divergencia operacional de valor"
```

---

### Task 14: Conciliação do extrato contra os pagamentos registrados

**Files:**
- Create: `apps/api/src/conciliacao/servico.ts`
- Test: `apps/api/test/conciliacao.test.ts`

**Interfaces:**
- Consumes: `consultarPagamento` e a listagem do Asaas (Task 5), repositório (Task 7).
- Produces: `conciliar(idConta: number, de: Date, ate: Date): Promise<Divergencias>`, onde `Divergencias = { ausentesNoBanco: string[], ausentesNoPsp: string[], valorDivergente: Array<{ endToEndId, valorPsp, valorBanco }> }`

Implementa RF14 e é a rede de segurança de todo o resto: **um webhook perdido é invisível por definição** — não chega aviso nenhum dizendo que não chegou aviso. A conciliação é o único mecanismo que detecta isso.

Também é o que sustenta a mitigação de 7.5 do spec para indisponibilidade do PSP.

- [ ] **Step 1: Escrever o teste que falha**

```ts
it('aponta pagamento que existe no PSP e não no banco', async () => {
  asaasFalso.extrato([{ endToEndId: 'E-1', value: 100 }]);
  const d = await conciliar(1, ontem(), hoje());
  expect(d.ausentesNoBanco).toEqual(['E-1']);
});

it('aponta pagamento que existe no banco e não no PSP', async () => {
  await gravarPagamento(1, idPagador, canonico({ endToEndId: 'E-2' }));
  asaasFalso.extrato([]);
  expect((await conciliar(1, ontem(), hoje())).ausentesNoPsp).toEqual(['E-2']);
});

it('aponta divergência de valor', async () => {
  await gravarPagamento(1, idPagador, canonico({ endToEndId: 'E-3', valor: 100 }));
  asaasFalso.extrato([{ endToEndId: 'E-3', value: 150 }]);
  expect((await conciliar(1, ontem(), hoje())).valorDivergente)
    .toEqual([{ endToEndId: 'E-3', valorPsp: 150, valorBanco: 100 }]);
});

it('não acusa divergência quando tudo bate', async () => {
  await gravarPagamento(1, idPagador, canonico({ endToEndId: 'E-4', valor: 100 }));
  asaasFalso.extrato([{ endToEndId: 'E-4', value: 100 }]);
  const d = await conciliar(1, ontem(), hoje());
  expect(d).toEqual({ ausentesNoBanco: [], ausentesNoPsp: [], valorDivergente: [] });
});

it('registra a execução da conciliação em auditoria', async () => {
  await conciliar(1, ontem(), hoje());
  expect(await ultimaLinha('auditoria')).toMatchObject({ acao: 'CONCILIOU' });
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w apps/api -- conciliacao`
Expected: FAIL

- [ ] **Step 3: Acrescentar `listarPagamentos(idConta, de, ate)` ao cliente Asaas**

Paginado; a API do Asaas devolve em páginas e ignorar isso faz a conciliação mentir em qualquer volume real.

- [ ] **Step 4: Implementar `conciliar`**

Compara dois conjuntos por `endToEndId`. Pagamento ausente no banco **não é reingerido automaticamente** — vira divergência para decisão humana, porque reingerir às cegas contorna a reconsulta de 6.4.

- [ ] **Step 5: Rodar e verificar que passa**

Run: `npm test -w apps/api -- conciliacao`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/conciliacao apps/api/test/conciliacao.test.ts apps/api/src/asaas
git commit -m "feat(conciliacao): deteccao de webhook perdido e divergencia contra o extrato"
```

---

### Task 15: Gerador de massa sintética

**Files:**
- Create: `apps/api/src/seed/gerador.ts`, `apps/api/src/seed/cli.ts`
- Test: `apps/api/test/seed.test.ts`

**Interfaces:**
- Consumes: todo o schema e o repositório.
- Produces: `gerar(opcoes: { lojistas: number, meses: number, taxaFraude: number, semente: number }): Promise<Resumo>`, onde `Resumo = { pagamentos, pagadores, fraudesPlantadas, defeitosInjetados }`

Implementa RF19 e é o que torna a demonstração possível. **Determinístico por semente** — sem isso a apresentação não é reprodutível e um número que apareceu no ensaio pode não aparecer na hora.

- [ ] **Step 1: Escrever o teste que falha**

```ts
it('é determinístico para a mesma semente', async () => {
  const a = await gerar({ lojistas: 2, meses: 1, taxaFraude: 0.05, semente: 42 });
  await reset(); await migrate();
  const b = await gerar({ lojistas: 2, meses: 1, taxaFraude: 0.05, semente: 42 });
  expect(a).toEqual(b);
});

it('planta os três padrões de fraude em quantidade conhecida', async () => {
  const r = await gerar({ lojistas: 5, meses: 3, taxaFraude: 0.05, semente: 7 });
  expect(r.fraudesPlantadas.sonda).toBeGreaterThan(0);
  expect(r.fraudesPlantadas.nomeDivergente).toBeGreaterThan(0);
  expect(r.fraudesPlantadas.contestacaoPrevia).toBeGreaterThan(0);
});

it('distribui contestações com atraso de até 90 dias', async () => {
  await gerar({ lojistas: 5, meses: 6, taxaFraude: 0.1, semente: 7 });
  const { rows } = await pool.query(
    `SELECT max(d.solicitada_em - p.ocorrido_em) AS maior
     FROM devolucao d JOIN pagamento p USING (id_pagamento) WHERE d.origem='MED'`);
  expect(diasDe(rows[0].maior)).toBeGreaterThan(30);
  expect(diasDe(rows[0].maior)).toBeLessThanOrEqual(90);
});

it('injeta defeitos em quantidade conhecida e contabilizada', async () => {
  const r = await gerar({ lojistas: 3, meses: 1, taxaFraude: 0.05, semente: 7 });
  expect(r.defeitosInjetados.nomeMascarado).toBeGreaterThan(0);
  expect(r.defeitosInjetados.semDocumento).toBeGreaterThan(0);
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w apps/api -- seed`
Expected: FAIL

- [ ] **Step 3: Implementar `gerar`**

Faker com semente fixa. Insere em lote com `COPY` ou `INSERT` multi-valor — 2,2 milhões de linhas uma a uma não termina em tempo útil. O volume cheio do spec roda pela CLI; os testes usam recortes pequenos.

- [ ] **Step 4: Implementar a CLI**

`npm run seed -- --lojistas 50 --meses 12 --semente 42`, imprimindo o resumo. É o comando que prepara a apresentação.

- [ ] **Step 5: Rodar e verificar que passa**

Run: `npm test -w apps/api -- seed`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/seed apps/api/test/seed.test.ts
git commit -m "feat(seed): gerador deterministico com fraude plantada e defeitos contabilizados"
```

---

### Task 16: As oito consultas analíticas

**Files:**
- Create: `packages/db/queries/pn01.sql` … `pn08.sql`, `packages/db/queries/README.md`
- Test: `packages/db/test/queries.test.ts`

**Interfaces:**
- Consumes: o schema completo e o gerador (Task 15).
- Produces: oito arquivos `.sql` executáveis isoladamente — é o que o enunciado exige como "consultas que respondem a perguntas de negócio, com resultados".

Cada arquivo abre com um comentário de três linhas: a pergunta de negócio, a técnica usada, e por que ela só é possível no motor relacional. Esse comentário é o roteiro falado da apresentação.

- [ ] **Step 1: Escrever o teste que falha**

```ts
it('as oito consultas rodam contra a massa e devolvem linhas', async () => {
  await gerar({ lojistas: 5, meses: 3, taxaFraude: 0.1, semente: 42 });
  for (const pn of ['pn01','pn02','pn03','pn04','pn05','pn06','pn07','pn08']) {
    const { rows } = await pool.query(lerSql(pn));
    expect(rows.length, `${pn} não devolveu linhas`).toBeGreaterThan(0);
  }
});

it('PN02 calcula precisão por regra sem divisão por zero', async () => {
  const { rows } = await pool.query(lerSql('pn02'));
  for (const r of rows) expect(Number.isFinite(Number(r.precisao))).toBe(true);
});

it('PN07 usa window function', () => {
  expect(lerSql('pn07')).toMatch(/OVER\s*\(/i);
});

it('PN01 usa width_bucket para a faixa de valor', () => {
  expect(lerSql('pn01')).toMatch(/width_bucket/i);
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w packages/db -- queries`
Expected: FAIL — arquivos inexistentes.

- [ ] **Step 3: Escrever as oito consultas**

Conforme a tabela 9.4 do spec. PN02 usa `count(*) FILTER (WHERE ...)` e protege a divisão com `NULLIF`. PN07 usa `count() OVER (PARTITION BY id_pagador ORDER BY ocorrido_em)`.

- [ ] **Step 4: Escrever o `README.md` das consultas**

Tabela de PN → arquivo → pergunta, para a professora conseguir navegar sozinha.

- [ ] **Step 5: Rodar e verificar que passa**

Run: `npm test -w packages/db -- queries`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/db/queries packages/db/test/queries.test.ts
git commit -m "feat(db): oito consultas analiticas respondendo as perguntas de negocio"
```

---

### Task 17: Contrato OpenAPI e roteiro de demonstração reproduzível

**Files:**
- Create: `DEMO.md`, `scripts/demo-aprovado.sh`, `scripts/demo-recusado.sh`
- Modify: `apps/api/src/main.ts` — habilitar `@nestjs/swagger`
- Test: `apps/api/test/demo.e2e.test.ts`

**Interfaces:**
- Consumes: tudo.
- Produces: dois scripts que disparam os cenários do roteiro 9.5 do spec contra a API local.

O entregável é a apresentação funcionando. O teste ponta a ponta existe porque "funcionou no ensaio" não é garantia nenhuma se ninguém reexecutou o caminho inteiro.

- [ ] **Step 1: Escrever o teste ponta a ponta que falha**

```ts
it('cenário aprovado: webhook → pagamento → análise → liberado → notificação', async () => {
  await gerar({ lojistas: 1, meses: 6, taxaFraude: 0, semente: 42 });
  await post('/api/v1/webhook/asaas', fixtureLimpo(), cabecalhoValido);
  await aguardarAnalise();
  expect(await campo('pagamento', 1, 'situacao_entrega')).toBe('LIBERADA');
  expect((await ultimaLinha('notificacao')).conteudo).toContain('Aprovado');
});

it('cenário recusado: dois sinais fortes → RECUSADO → devolução solicitada', async () => {
  await semearPagadorComContestacaoENomeDivergente();
  await post('/api/v1/webhook/asaas', fixtureSuspeito(), cabecalhoValido);
  await aguardarAnalise();
  const a = await ultimaLinha('analise_risco');
  expect(a.veredito).toBe('RECUSADO');
  expect(a.score).toBeGreaterThanOrEqual(75);
  expect(await contar('devolucao')).toBe(1);
  expect(await campo('pagamento', idUltimo, 'situacao_entrega')).toBe('RETIDA');
});

it('reentrega do mesmo webhook não duplica nada', async () => {
  const corpo = fixtureLimpo();
  await post('/api/v1/webhook/asaas', corpo, cabecalhoValido);
  await post('/api/v1/webhook/asaas', corpo, cabecalhoValido);
  expect(await contar('pagamento')).toBe(1);
  expect(await contar('analise_risco')).toBe(1);
});

it('o expurgo remove o bruto e preserva o normalizado', async () => {
  await post('/api/v1/webhook/asaas', fixtureLimpo(), cabecalhoValido);
  await pool.query(`UPDATE ingestao_webhook SET recebido_em = now() - interval '8 days'`);
  await pool.query(`DELETE FROM ingestao_webhook WHERE expurgar_em < now()`);
  expect(await contar('ingestao_webhook')).toBe(0);
  expect(await contar('pagamento')).toBe(1);
});

// RF20 — contrato publicado
it('expõe OpenAPI 3 com as rotas versionadas', async () => {
  const doc = await get('/api/v1/docs-json');
  expect(doc.body.openapi).toMatch(/^3\./);
  expect(Object.keys(doc.body.paths)).toEqual(
    expect.arrayContaining(['/api/v1/webhook/asaas', '/api/v1/cobrancas']));
});
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `npm test -w apps/api -- demo.e2e`
Expected: FAIL

- [ ] **Step 3: Habilitar o `@nestjs/swagger` em `main.ts`**

`DocumentBuilder` com título, versão e a tag de cada módulo. Servido em `/api/v1/docs`, JSON em `/api/v1/docs-json`.

- [ ] **Step 4: Implementar os dois scripts**

`curl` contra a API local com os payloads dos dois cenários. Sem segredo embutido — leem do `.env`.

- [ ] **Step 5: Escrever o `DEMO.md`**

Os dez passos do roteiro 9.5 do spec, cada um com o comando exato e o que mostrar na tela. Inclui as consultas de verificação em `psql` para os passos 1, 9 e 10, que são os que endereçam a rubrica diretamente.

- [ ] **Step 6: Rodar e verificar que passa**

Run: `npm test -w apps/api -- demo.e2e`
Expected: PASS

- [ ] **Step 7: Rodar a suíte inteira**

Run: `npm test`
Expected: PASS em todos os pacotes

- [ ] **Step 8: Commit**

```bash
git add DEMO.md scripts apps/api/src/main.ts apps/api/test/demo.e2e.test.ts
git commit -m "feat(demo): contrato OpenAPI, roteiro reproduzivel e teste ponta a ponta"
```

---

## Primeira coisa a fazer na execução

A pendência nº 2 do spec, antes da Task 3: **disparar um webhook de teste no sandbox do Asaas e inspecionar o JSON bruto** para descobrir se o nome e o documento do pagador vêm, e se vêm mascarados. A resposta decide se a RN05 dispara na prática e, se vier mascarado, o peso dela precisa ser redistribuído antes da Task 8 — não depois.
