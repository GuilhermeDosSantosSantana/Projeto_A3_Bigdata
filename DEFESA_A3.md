# CONFIA — defesa da A3

## Resposta honesta sobre o estado atual

**O material exigido pelo enunciado existe e o protótipo de dados executa, mas a entrega ainda não está totalmente fechada para uma defesa sem ressalvas.** O relatório em PDF cobre os itens 4.1 a 4.7; há 15 tabelas, uma amostra fictícia, oito consultas executáveis com resultados, evidências e slides. Ainda é preciso confirmar a revisão pelo grupo, preencher os integrantes, ensaiar a participação de todos e decidir se a banca aceitará PGlite como demonstração do PostgreSQL ou se devemos executar o mesmo SQL em PostgreSQL 16 nativo. Não existe integração com Pix real nem medição de desempenho em escala.

O enunciado concentra **6 dos 10 pontos** na escolha do tipo de banco e na organização/modelagem dos dados. A interface serve para explicar o ciclo do dado; não é o centro da defesa.

## Conferência do enunciado

| Item | Estado | Evidência e ressalva |
|---|---|---|
| 4.1 Problema, público, proposta, perguntas e KPIs | Coberto | Seção 1 do relatório; não existem KPIs de produção medidos. |
| 4.2 Fontes, tipos, 5 Vs, crescimento e acesso | Coberto como hipótese | Seção 2; 2,2 milhões/ano é estimativa, não carga testada. |
| 4.3 Banco, alternativas, ACID/BASE, CAP, custo e latência | Coberto na argumentação | Seção 3; faltam benchmark e execução em servidor PostgreSQL 16 nativo. |
| 4.4 Modelos, dicionário, chaves, índices e crescimento | Coberto | Seção 4, apêndice do PDF e `sql/01_schema.sql`. Há tabela de cardinalidades, não um DER gráfico. |
| 4.5 Qualidade, fluxo, LGPD, acesso e backup | Coberto como desenho | Seção 5; backup, papéis de produção e expurgo agendado não foram implantados. |
| 4.6 Banco real, amostra, ≥5 consultas e resultados | Executado com ressalva | PGlite persiste PostgreSQL em WebAssembly; `npm run demo` executa 8 SQLs sobre 12 pagamentos fictícios e salva `evidencias/resultados.json`. |
| 4.7 Limitações, 100× e aprendizados | Coberto | Seção 7 do relatório. |
| Relatório PDF | Existe | `output/pdf/CONFIA_relatorio_A3.pdf`; falta preencher grupo e turma. |
| Protótipo e evidências | Existe | SQL, amostra, resultados JSON, testes automatizados e capturas. |
| Pitch e participação do grupo | Preparado, não realizado | `output/CONFIA_pitch_A3.pptx` e `PITCH.md`; duração e divisão entre integrantes ainda precisam ser acertadas. |
| Declaração de IA e revisão pelo grupo | Parcial | O relatório declara o uso de IA e a validação técnica local; a revisão humana do grupo precisa ser feita antes da entrega. |

## Explicação para falar na apresentação

**1. Problema.** “O comerciante pode receber um Pix verdadeiro, entregar o produto e depois enfrentar uma contestação. Um comprovante na tela do cliente não basta para decidir a entrega. O CONFIA propõe conferir o recebimento no provedor e avaliar o risco com o histórico daquela loja.”

**2. Decisão de produto.** “O CONFIA não aprova nem cancela o Pix no banco. O pagamento já ocorreu. Ele orienta a decisão que o lojista controla: liberar ou reter a mercadoria. Quando a entrega é retida, o painel mostra os sinais que levaram a isso; um sinal de risco não é prova de fraude.”

**3. Por que PostgreSQL.** “Precisamos de consistência entre pagamento, análise e decisão; por isso escolhemos um banco relacional com transações, chaves estrangeiras, restrições de domínio e unicidade do identificador da transação. O payload variável do evento cabe em JSONB, e as consultas de perfil, percentis e recorrência rodam no mesmo motor. Consideramos MongoDB, MySQL, Redis e grafos, mas o custo de separar os dados agora não se justifica para as relações e o volume previstos.”

**4. Modelagem.** “O núcleo liga lojista, conta recebedora, pagador, pagamento, análise e sinais. O pagador é identificado por loja, nunca em uma reputação global. A ingestão bruta é separada do pagamento normalizado para permitir expurgo após sete dias. A tabela `pagamento` tem `UNIQUE (psp, end_to_end_id)`, que impede duplicação quando um aviso é reenviado.”

**5. Prova.** “Executamos 15 tabelas e uma amostra de 12 pagamentos fictícios. Oito consultas respondem perguntas de negócio; cinco já bastariam para o enunciado. Demonstramos rejeição de pagamento duplicado, isolamento entre lojas e remoção do dado bruto sem perder o pagamento. No painel, um caso retido exibe os motivos recuperados das tabelas de regra e sinal.”

**6. Limite.** “Este é um protótipo de dados. O provedor no teste é simulado; ainda não há Pix real, push no celular nem avaliação estatística de fraude. A precisão de 100% em duas ocorrências rotuladas foi plantada na amostra e não estima resultado de produção.”

## Perguntas prováveis da professora

**“Se o tema é Big Data, por que só há 12 pagamentos?”** A amostra pequena comprova que o esquema e as consultas funcionam. O volume de 2,2 milhões/ano é hipótese de dimensionamento discutida pelos 5 Vs, não resultado de teste de carga. Não afirmamos que o protótipo validou escala.

**“Por que não MongoDB?”** O evento bruto é variável e usa JSONB, mas o núcleo exige relações estáveis, transações e integridade. Separar payload e decisões em motores diferentes criaria reconciliação de dados financeiros.

**“Por que não MySQL?”** MySQL é alternativa séria. PostgreSQL foi escolhido por recursos que o desenho usa diretamente: JSONB com GIN, índices parciais e agregações analíticas. A conclusão é para este problema, não uma afirmação de que MySQL seja incapaz.

**“Por que não grafo para antifraude?”** No escopo atual, a relação usada é pagador–loja, com profundidade 1 e sem reputação compartilhada entre lojas. Um `JOIN` resolve a pergunta; o banco de grafos adicionaria operação sem consulta correspondente.

**“Onde entra CAP?”** No protótipo há um só nó, então CAP não escolhe o motor. Se houver uma rede distribuída e a confirmação ficar indisponível, a entrega deve continuar retida. A prioridade é evitar uma liberação baseada em dado possivelmente desatualizado.

**“O Pix foi recusado?”** Não. O Pix foi recebido no cenário. O veredito interno `RECUSADO` significa **entrega retida por risco elevado**; o sistema não cancela uma transferência já concluída.

**“O webhook prova que entrou?”** Não. Em produção, o aviso deve provocar uma reconsulta à API do provedor. Nesta demonstração, a API reconsulta o estado de um provedor local simulado. Isso prova o fluxo de software, não a integração com Asaas.

**“Como sabem que as regras detectam fraude?”** Ainda não sabem. Os rótulos são sintéticos e poucos; a consulta PN02 demonstra como calcular precisão quando houver desfechos confiáveis, sem provar eficácia do modelo.

**“Vocês implementaram as nove regras?”** O catálogo e a amostra têm nove sinais. O fluxo interativo calcula seis; RN06, RN11 e RN12 ainda não são avaliadas ao vivo. A A3 exige modelagem e consultas, não um antifraude de produção. Não afirmar que o motor completo foi entregue.

**“Isso é PostgreSQL de verdade?”** O protótipo roda PGlite, PostgreSQL compilado para WebAssembly, com persistência local e SQL executado. Não há servidor PostgreSQL 16 nativo instalado. Para eliminar essa ressalva na banca, executar os mesmos scripts e consultas em uma instância PostgreSQL 16 e guardar o resultado.

**“E a LGPD?”** Os dados da apresentação são fictícios. O desenho separa bruto temporário de registro normalizado e limita a identidade do pagador ao lojista. No fluxo interativo, novos identificadores são pseudonimizados por HMAC. Pseudonimização não é anonimização; base legal, retenção e acesso precisam de revisão antes de operar com pessoas reais.

## Roteiro de demonstração sem depender de Pix real

1. Abrir `http://127.0.0.1:3000/` e explicar a decisão de entrega que o lojista recebe.
2. Abrir `/laboratorio` em outra aba. Criar pagamento fictício e mostrar o estado **PENDENTE**; ele ainda não entra como pagamento confirmado.
3. Confirmar no provedor simulado e voltar à tela do lojista. Mostrar valor, decisão e motivos. Usar o cenário de contestação anterior para mostrar a retenção explicada.
4. Mostrar `sql/01_schema.sql`: FK entre pagamento, conta e pagador da mesma loja; UNIQUE do Pix; índices parciais e GIN.
5. Rodar `npm run demo` e abrir `evidencias/resultados.json`. Mostrar PN01, PN02, PN03, PN04 e PN07, explicando que existem oito consultas.
6. Mostrar as verificações `duplicate_blocked`, `cross_store_blocked`, `raw_after_purge=0` e `normalized_after_purge=12`.

## Prioridades para os cinco dias restantes

1. **Banco:** executar o DDL, a amostra e as oito consultas em PostgreSQL 16 nativo; guardar captura e saída. Esse é o maior risco de questionamento da prova de conceito.
2. **Revisão do grupo:** conferir os campos do dicionário, a base legal proposta e o que cada integrante consegue explicar. Inserir nomes e turma no PDF.
3. **Ensaio:** medir o tempo real do pitch, definir quem fala cada bloco e preparar a demonstração sem internet; guardar `evidencias/resultados.json` e capturas como contingência.
4. **Checagem final:** executar `npm test` e `npm run demo` na máquina da apresentação, abrir PDF e slides e verificar se os resultados correspondem ao discurso.

Referências técnicas para a defesa: [PGlite — documentação oficial](https://pglite.dev/docs/about), [PostgreSQL 16 — JSONB e GIN](https://www.postgresql.org/docs/16/datatype-json.html), [PostgreSQL 16 — índices parciais](https://www.postgresql.org/docs/16/indexes-partial.html) e [LGPD — texto compilado](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm).
