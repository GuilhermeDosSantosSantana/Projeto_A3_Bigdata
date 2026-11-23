# GIRO — gestão inteligente de estoque

Protótipo local criado do zero para a A3 de Análise de Dados e Big Data. A demonstração foi pensada para um pequeno mercado: cadastrar produto, registrar entrada por lote, vender, registrar perda e acompanhar o impacto no painel. O código usa somente a biblioteca padrão do Python, HTML, CSS, JavaScript e SQLite.

**Estado em 23/11/2026:** os arquivos foram escritos, mas a aplicação **não foi executada nem testada** nesta etapa, conforme pedido do usuário. Portanto, o funcionamento ponta a ponta e os resultados das consultas ainda precisam de verificação antes do pitch. Não apresentar este protótipo como validado até essa verificação.

## Como iniciar quando for autorizado testar

Requisito: Python 3.11 ou mais recente.

```powershell
cd C:\Users\gsantana5\Documents\A3_BigData
python -m giro.server
```

Abrir `http://127.0.0.1:3000`. O banco `storage/giro.sqlite3` será criado com dados **fictícios** na primeira inicialização. O servidor escuta apenas em `127.0.0.1`, sem serviço externo ou credenciais.

No Windows, `INICIAR_GIRO.cmd` oferece o mesmo comando por duplo clique. Ele também não foi executado nesta etapa.

## Estrutura

- `giro/db.py`: conexão, indicadores e operações transacionais.
- `giro/server.py`: API e servidor local.
- `web/`: painel visual e formulários.
- `sql/01_schema.sql`: tabelas, chaves, restrições, índices, gatilhos e visões.
- `sql/02_seed.sql`: amostra fictícia com produtos, entradas, vendas e perdas.
- `sql/consultas/`: seis perguntas de negócio e uma consulta de qualidade.
- `scripts/consultas.py`: gera `evidencias/resultados.json` quando autorizado.
- `tests/test_stock.py`: verifica baixa por validade, saldo insuficiente, duplicidade e gatilho.
- `docs/PROJETO_A3.md`: decisões de dados e roteiro de defesa.

## Decisão de dados

SQLite é um banco relacional real, gravado em arquivo, com transações ACID. Para o protótipo de um único comércio, permite demonstrar a lógica sem instalar serviço, criar conta ou depender de internet. As vendas são gravadas em uma transação `BEGIN IMMEDIATE`; um gatilho impede que um lote fique com saldo negativo. O estoque vem de lotes recebidos menos vendas e perdas registradas. A lógica de reposição é uma regra transparente baseada em vendas de sete dias, prazo do fornecedor e estoque mínimo, sem alegação de inteligência artificial.

O sistema é um protótipo acadêmico local: não tem autenticação, integração com caixa/ERP, pedidos reais a fornecedores ou previsão estatística treinada. O relatório e as evidências executadas ainda precisam ser concluídos.

Quando o grupo decidir validar, os comandos previstos são `python -m unittest discover -s tests` e `python -m scripts.consultas`. Eles não foram executados nesta etapa.

## Origem do código

Os arquivos ativos do GIRO foram escritos neste projeto. A cópia de terceiro usada temporariamente para estudo foi removida. O trabalho anterior, CONFIA, foi retirado da branch ativa e pode ser recuperado pela tag Git `confia-archive-2026-11-23`.
