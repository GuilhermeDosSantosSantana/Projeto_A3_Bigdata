# Pitch — CONFIA

Para defesa completa, ressalvas e respostas às perguntas da professora, consultar `DEFESA_A3.md`.

**Abertura (30 s).** O Pix pode ter entrado de verdade e ainda assim gerar perda posterior ao lojista por contestação. O CONFIA ajuda a decidir se a mercadoria deve ser entregue, analisada ou retida.

**Produto e dados (45 s).** O serviço observaria o evento do provedor, reconsultaria o pagamento, pseudonimizaria o pagador e registraria sinais de risco. O protótipo desta A3 demonstra o núcleo de dados com 12 pagamentos totalmente fictícios.

**Decisão do banco (60 s).** Escolhemos PostgreSQL porque dinheiro exige integridade transacional e idempotência. JSONB recebe formatos variáveis de evento; FKs e CHECKs evitam estados inválidos; índices parciais atendem filas pequenas; consultas analíticas usam percentis e funções de janela. Consideramos MongoDB, MySQL, Redis e grafos. Um motor é suficiente para a profundidade real das relações e evita reconciliação entre bancos.

**Modelagem e qualidade (60 s).** Mostrar `sql/01_schema.sql`: 15 tabelas, identidade de pagador única por loja, UNIQUE em `(psp, end_to_end_id)`, uma análise por pagamento. Mostrar que a ingestão bruta não possui FK para pagamento: ela pode ser expurgada após sete dias, enquanto o pagamento normalizado continua. O expurgo foi demonstrado por script; o agendamento automático ainda não existe.

**Demonstração (90 s).** Rodar `npm start`. Abrir a visão do lojista em `http://127.0.0.1:3000` e explicar que é onde ele recebe a decisão. Em outra aba, abrir `/laboratorio`, criar um Pix fictício e mostrar que ele ainda não aparece como recebido. Confirmar no provedor simulado; voltar à visão do lojista e mostrar valor, ação de entrega e motivos em linguagem comum. Repetir com EM_ANALISE e RECUSADO, destacando os sinais. Depois abrir `evidencias/resultados.json`: PN01, PN02 (só dois rótulos, sem conclusão estatística), PN03, PN04 e PN07. Mostrar `duplicate_blocked=true`, `raw_after_purge=0` e `normalized_after_purge=12`.

**Fecho (30 s).** A escolha do banco nasce do ciclo de vida do dado: receber, validar, decidir, auditar e reduzir retenção de dados pessoais. O próximo passo é integrar um PSP em sandbox e medir carga real. O protótipo comprova modelagem e consultas; ainda não comprova a eficácia do antifraude em produção.

Distribuir os blocos entre os integrantes presentes. O enunciado não informa duração do pitch; ajustar os tempos quando a professora confirmar.
