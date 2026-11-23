# Pitch — CONFIA

**Abertura (30 s).** O Pix pode ter entrado de verdade e ainda assim gerar perda posterior ao lojista por contestação. O CONFIA ajuda a decidir se a mercadoria deve ser entregue, analisada ou retida.

**Produto e dados (45 s).** O serviço observaria o evento do provedor, reconsultaria o pagamento, pseudonimizaria o pagador e registraria sinais de risco. O protótipo desta A3 demonstra o núcleo de dados com 12 pagamentos totalmente fictícios.

**Decisão do banco (60 s).** Escolhemos PostgreSQL porque dinheiro exige integridade transacional e idempotência. JSONB recebe formatos variáveis de evento; FKs e CHECKs evitam estados inválidos; índices parciais atendem filas pequenas; consultas analíticas usam percentis e funções de janela. Consideramos MongoDB, MySQL, Redis e grafos. Um motor é suficiente para a profundidade real das relações e evita reconciliação entre bancos.

**Modelagem e qualidade (60 s).** Mostrar `sql/01_schema.sql`: 15 tabelas, identidade de pagador única por loja, UNIQUE em `(psp, end_to_end_id)`, uma análise por pagamento. Mostrar que a ingestão bruta não possui FK para pagamento: ela pode ser expurgada após sete dias, enquanto o pagamento normalizado continua.

**Demonstração (90 s).** Rodar `npm run demo`. Abrir `evidencias/resultados.json`. Mostrar PN01 (vereditos), PN02 (precisão com só dois rótulos, sem conclusão estatística), PN03 (latência sintética), PN04 (R$ 1.500 de exposição retida) e PN07 (recorrência). Destacar que as oito consultas retornam dados. Mostrar `duplicate_blocked=true`, `raw_after_purge=0` e `normalized_after_purge=12`.

**Fecho (30 s).** A escolha do banco nasce do ciclo de vida do dado: receber, validar, decidir, auditar e reduzir retenção de dados pessoais. O próximo passo é integrar um PSP em sandbox e medir carga real. O protótipo comprova modelagem e consultas; ainda não comprova a eficácia do antifraude em produção.

Distribuir os blocos entre os integrantes presentes. O enunciado não informa duração do pitch; ajustar os tempos quando a professora confirmar.
