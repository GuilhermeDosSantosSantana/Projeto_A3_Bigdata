# CONFIA — protótipo de dados da A3

O relatório final está em `output/pdf/CONFIA_relatorio_A3.pdf`. O protótipo usa PostgreSQL em WebAssembly (PGlite), para funcionar sem Docker ou servidor instalado. Os arquivos SQL usam recursos centrais do PostgreSQL e podem ser migrados para uma instância PostgreSQL convencional; a execução aqui foi verificada no PGlite.

## Reprodução

Requisitos: Node.js e npm.

```sh
npm install
npm run demo
```

O comando cria o banco em memória, executa `sql/01_schema.sql` e `sql/02_amostra.sql`, roda as oito consultas em `sql/queries/` e grava `evidencias/resultados.json`. Também testa duplicidade da transação, isolamento entre lojas e expurgo do evento bruto. Para regenerar o PDF, instale `reportlab` e execute `python scripts/relatorio.py` no Windows (a fonte Arial do sistema é usada).

Todos os dados são sintéticos. Os hashes com caracteres repetidos são marcadores de demonstração e **não** uma implementação de HMAC. Não existe integração com Asaas nem análise em tempo real neste protótipo.

## Estrutura

- `sql/01_schema.sql`: 15 tabelas, FKs, restrições e índices.
- `sql/02_amostra.sql`: amostra fictícia com padrões de fraude plantados.
- `sql/queries/pn01.sql` a `pn08.sql`: perguntas de negócio executáveis.
- `evidencias/resultados.json`: saída integral da última execução.
- `output/pdf/CONFIA_relatorio_A3.pdf`: relatório para entrega.
- `PITCH.md`: roteiro curto para apresentação.

Antes de entregar, incluir nomes do grupo no PDF e conferir a duração definida pela professora, pois o enunciado deixa esses campos em branco.
