# GIRO - entrega do banco da A3

O foco da entrega e o **MySQL 8.4**. O esquema `giro_a3` foi instalado nesta maquina e esta carregado com dados inteiramente ficticios, sem acentos nos nomes da amostra para exibir corretamente no Workbench.

| Tabela | Registros |
|---|---:|
| `category` | 12 |
| `supplier` | 40 |
| `customer` | 500.000 |
| `product` | 2.001+ |
| `batch` | 2.500+ |
| `sale` | 750.001+ |
| `stock_event` | 755.005+ |

Os numeros acima incluem os registros de demonstracao e podem crescer ao usar a interface.

## Abrir o sistema completo

Para instalar em outro Windows, baixe apenas [INSTALAR_GIRO.bat](INSTALAR_GIRO.bat) e execute-o. Ele baixa o projeto do GitHub, instala Python 3.13, Visual C++ Runtime, MySQL 8.4 e Workbench via `winget`, instala as bibliotecas Python em `.venv` e restaura o backup compactado. A senha `root` do MySQL e solicitada localmente, sem aparecer na tela. Veja [o guia da equipe](docs/INSTALACAO_EQUIPE.md). Se o MySQL Configurator ainda nao estiver concluido, finalize-o e execute o mesmo `.bat` de novo.

1. De dois cliques em `INICIAR_GIRO.cmd`. O atalho inicia o MySQL e o servidor web local, se necessario, e abre o painel em `http://127.0.0.1:3000`.
2. O painel mostra clientes, vendas, produtos, estoque, alertas e receita diretamente da base `giro_a3`.
3. Use **Novo produto**, **Registrar entrada**, **Registrar venda** (com busca opcional de cliente) e **Registrar perda**. Depois confira o mesmo registro no MySQL Workbench.
4. Para iniciar somente o banco e abrir o Workbench, use `INICIAR_MYSQL_GIRO.cmd`.

O servidor web usa `mysql-connector-python` e uma conta local `giro_app` com permissoes restritas a leitura e gravacao no esquema da A3. As credenciais ficam em `mysql/runtime/app.cnf`, ignorado pelo Git. O servidor web e o MySQL escutam apenas em `127.0.0.1`.

O Redis e usado como cache descartavel do painel e do catalogo quando esta disponivel. Se o Redis local falhar, um cache temporario em memoria mantem as leituras rapidas; o MySQL continua sendo a fonte dos dados. Produtos e clientes sao mostrados em paginas de 12 registros; movimentacoes, em paginas de 20. As respostas da API incluem `items`, `page`, `pages` e `total`.

Para a apresentacao, siga [o guia de cada fluxo](docs/GUIA_DE_USO_PITCH.md). Para redigir e defender a A3 segundo o enunciado, use [o guia de redacao](docs/GUIA_DE_REDACAO_A3.md). Os prints estao em `evidencias/` e no apendice do PDF.

Teste de ponta a ponta: `python -m scripts.testar_fluxo_web` cria um produto sintetico, duas entradas, uma venda associada a cliente e uma perda; tambem confirma que uma venda sem saldo e recusada. O teste deixa esses dados de demonstracao no banco.

Teste visual: `python -m scripts.testar_front` abre o Edge em modo automatico, percorre navegacao, cadastro, edicao, entrada, venda, perda, busca e paginacao, e atualiza os prints. Tambem deixa dados sinteticos identificados por SKU `UI-*`.

## Abrir e mostrar

1. De dois cliques em `INICIAR_MYSQL_GIRO.cmd`. Ele inicia o servidor local, se necessario, e abre o MySQL Workbench.
2. Abra a conexao salva **GIRO A3 - MySQL local** nesta maquina. Em outro Windows, crie a conexao com host, usuario e senha indicados em `mysql/CONEXAO_LOCAL.txt`. O esquema `giro_a3` aparece a esquerda.
3. Expanda `Tables` e `Views`. Execute, por exemplo, `SELECT * FROM giro_a3.product_balance LIMIT 20;`.
4. Para perguntas de negocio, abra os arquivos em `mysql/consultas/`. A consulta `07_qualidade.sql` deve retornar zero linhas.

O usuario `giro_demo` da conexao visual tem apenas `SELECT` e `SHOW VIEW`. As credenciais desta instalacao estao em `mysql/CONEXAO_LOCAL.txt`, ignorado pelo Git. O servidor escuta somente em `127.0.0.1:3306`. Apos reiniciar o Windows, use o atalho novamente.

## Arquivos para a entrega

- `entrega/GIRO_A3_pacote_pitch.zip`: pacote compacto com relatorio, esquema, consultas, evidencias e backup compactado; sem senhas.
- `output/pdf/GIRO_relatorio_A3.pdf`: relatorio da A3, justificativa e resultados.
- `entrega/GIRO_mysql_A3.sql`: backup restauravel do esquema, dados, visoes e gatilho.
- `entrega/GIRO_mysql_A3.sql.gz`: o mesmo backup compactado para copiar ou versionar.
- `mysql/01_schema.sql`: sete tabelas, FKs, CHECK, indices, IDs gerados automaticamente para transacoes novas e duas visoes.
- `mysql/02_seed.sql`: registros pequenos de referencia.
- `mysql/03_volume_seed.sql`: carga sintetica grande, gerada de modo deterministico.
- `mysql/04_trigger.sql`: protecao de saldo e coerencia venda-lote.
- `mysql/05_enable_app_writes.sql`: migracao da base ja instalada para IDs gerados automaticamente.
- `giro/mysql_db.py`, `giro/server.py` e `web/`: backend e painel conectados ao MySQL.
- `mysql/consultas/`: sete consultas de negocio e uma de qualidade.
- `docs/dicionario_de_dados_mysql.csv`: 38 campos, tipos reais conferidos contra `information_schema`.
- `evidencias/mysql_resultados_consultas.json`: resultados das consultas, contagens e teste de restauracao.
- `scripts/gerar_amostra_mysql.py`: regenerador da carga.
- `scripts/validar_mysql.py`: validador, gerador do dump e teste de restauracao.
- `docs/ROTEIRO_DEFESA.md`: explicacao curta para o pitch.
- `docs/GUIA_DE_USO_PITCH.md`: passo a passo de cada fluxo com prints.
- `docs/GUIA_DE_REDACAO_A3.md`: estrutura de redacao e divisao da fala conforme o enunciado.
- `docs/RESULTADOS_VALIDACAO.md`: o que passou nos testes e limites observados.

## Reconstruir a base nesta maquina

O dump e a maneira mais simples de restaurar a base. O arquivo de carga e o codigo gerador tambem permitem recria-la do zero. A ordem de construcao e `01_schema.sql`, `02_seed.sql`, `03_volume_seed.sql`, `04_trigger.sql`; a consulta de qualidade confere a carga antes do uso. O gatilho e criado apos a importacao em lote para que a carga sintetica seja eficiente. Em operacao normal, ele fica ativo.

Para repetir a validacao com o MySQL em funcionamento:

```powershell
python scripts\validar_mysql.py
```

O prototipo antigo com SQLite permanece em `historico/sqlite/` apenas como historico. O painel atual utiliza a base MySQL da A3.
