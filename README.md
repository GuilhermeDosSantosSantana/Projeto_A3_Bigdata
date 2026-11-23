# CONFIA — sistema local de confirmação de Pix (A3)

O relatório final está em `output/pdf/CONFIA_relatorio_A3.pdf`. O sistema local tem front, API e um banco PostgreSQL em WebAssembly (PGlite) persistido na pasta `data/postgres/`. O banco funciona sem Docker, login ou serviço externo. O arquivo `data/provedor-simulado.json` representa o provedor de pagamentos, separado do banco do CONFIA.

## Reprodução

Requisitos: Node.js e npm.

```sh
npm install
npm start
```

Abra **http://127.0.0.1:3000** para ver a tela do lojista: pagamentos recebidos, decisão de entrega e motivos. Para gerar eventos fictícios, entre em **http://127.0.0.1:3000/laboratorio**. Ali escolha um cenário, clique em **Criar pagamento fictício** e depois em **Confirmar no provedor simulado**. Volte à tela do lojista para ver a notificação. O pagamento só entra no banco após a API reconsultar o estado confirmado no provedor local. Os dados persistem após reiniciar o servidor.

No Windows, também é possível dar dois cliques em `INICIAR_DEMO.cmd`. Mantenha a janela aberta durante a apresentação. O cenário de valor acima do perfil calcula seu valor a partir do histórico atual, para continuar testável após vários ensaios.

Para executar o teste automatizado dos três cenários, idempotência e reinício:

```sh
npm test
```

Para reproduzir apenas a prova de conceito analítica original, sem iniciar a aplicação:

```sh
npm run demo
```

O comando `demo` cria um banco temporário em memória, executa `sql/01_schema.sql` e `sql/02_amostra.sql`, roda as oito consultas em `sql/queries/` e grava `evidencias/resultados.json`. Também testa duplicidade da transação, isolamento entre lojas e expurgo do evento bruto. Para regenerar o PDF, instale `reportlab` e execute `python scripts/relatorio.py` no Windows (a fonte Arial do sistema é usada).

Todos os dados são sintéticos. A amostra SQL histórica usa marcadores repetidos como hashes de teste. Os novos pagadores criados pela aplicação são pseudonimizados com HMAC-SHA256 e segredo gerado em `data/hmac.key`. O motor local calcula sinais e veredito na confirmação simulada. **Não há integração com o Asaas nem transferência real de dinheiro.** Para usar um provedor real, será preciso configurar conta sandbox e credenciais, fora deste teste local.

## Estrutura

- `sql/01_schema.sql`: 15 tabelas, FKs, restrições e índices.
- `app/`: tela do lojista, laboratório de simulação, API local e teste ponta a ponta.
- `INICIAR_DEMO.cmd`: inicialização rápida para o pitch no Windows.
- `data/`: banco persistente e provedor simulado, criado na primeira execução e ignorado pelo Git.
- `sql/02_amostra.sql`: amostra fictícia com padrões de fraude plantados.
- `sql/queries/pn01.sql` a `pn08.sql`: perguntas de negócio executáveis.
- `evidencias/resultados.json`: saída integral da última execução.
- `evidencias/tela-confirmacao.png`: captura do front após confirmação no navegador.
- `evidencias/tela-lojista-retida.png`: tela do lojista com decisão de entrega e motivos.
- `output/pdf/CONFIA_relatorio_A3.pdf`: relatório para entrega.
- `PITCH.md`: roteiro curto para apresentação.
- `DEFESA_A3.md`: conferência da rubrica, explicação oral, perguntas prováveis e prioridades finais.
- `output/CONFIA_pitch_A3.pptx`: apresentação editável de seis slides.

Antes de entregar, incluir nomes do grupo no PDF e conferir a duração definida pela professora, pois o enunciado deixa esses campos em branco.
