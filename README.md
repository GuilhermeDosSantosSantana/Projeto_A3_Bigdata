# GIRO - entrega do banco da A3

O foco da entrega e o **MySQL 8.4**. O esquema `giro_a3` foi instalado nesta maquina e esta carregado com dados inteiramente ficticios, sem acentos nos nomes da amostra para exibir corretamente no Workbench.

| Tabela | Registros |
|---|---:|
| `category` | 12 |
| `supplier` | 40 |
| `customer` | 500.000 |
| `product` | 2.000 |
| `batch` | 2.498 |
| `sale` | 750.000 |
| `stock_event` | 755.002 |

## Abrir e mostrar

1. De dois cliques em `INICIAR_MYSQL_GIRO.cmd`. Ele inicia o servidor local, se necessario, e abre o MySQL Workbench.
2. Abra a conexao salva **GIRO A3 - MySQL local**. O esquema `giro_a3` aparece a esquerda.
3. Expanda `Tables` e `Views`. Execute, por exemplo, `SELECT * FROM giro_a3.product_balance LIMIT 20;`.
4. Para perguntas de negocio, abra os arquivos em `mysql/consultas/`. A consulta `07_qualidade.sql` deve retornar zero linhas.

O usuario `giro_demo` da conexao visual tem apenas `SELECT` e `SHOW VIEW`. As credenciais desta instalacao estao em `mysql/CONEXAO_LOCAL.txt`, ignorado pelo Git. O servidor escuta somente em `127.0.0.1:3306`. Apos reiniciar o Windows, use o atalho novamente.

## Arquivos para a entrega

- `entrega/GIRO_A3_pacote_pitch.zip`: pacote compacto com relatorio, esquema, consultas, evidencias e backup compactado; sem senhas.
- `output/pdf/GIRO_relatorio_A3.pdf`: relatorio da A3, justificativa e resultados.
- `entrega/GIRO_mysql_A3.sql`: backup restauravel do esquema, dados, visoes e gatilho.
- `entrega/GIRO_mysql_A3.sql.gz`: o mesmo backup compactado para copiar ou versionar.
- `mysql/01_schema.sql`: sete tabelas, FKs, CHECK, indices e duas visoes.
- `mysql/02_seed.sql`: registros pequenos de referencia.
- `mysql/03_volume_seed.sql`: carga sintetica grande, gerada de modo deterministico.
- `mysql/04_trigger.sql`: protecao de saldo e coerencia venda-lote.
- `mysql/consultas/`: sete consultas de negocio e uma de qualidade.
- `docs/dicionario_de_dados_mysql.csv`: 38 campos, tipos reais conferidos contra `information_schema`.
- `evidencias/mysql_resultados_consultas.json`: resultados das consultas, contagens e teste de restauracao.
- `scripts/gerar_amostra_mysql.py`: regenerador da carga.
- `scripts/validar_mysql.py`: validador, gerador do dump e teste de restauracao.
- `docs/ROTEIRO_DEFESA.md`: explicacao curta para o pitch.

## Reconstruir a base nesta maquina

O dump e a maneira mais simples de restaurar a base. O arquivo de carga e o codigo gerador tambem permitem recria-la do zero. A ordem de construcao e `01_schema.sql`, `02_seed.sql`, `03_volume_seed.sql`, `04_trigger.sql`; a consulta de qualidade confere a carga antes do uso. O gatilho e criado apos a importacao em lote para que a carga sintetica seja eficiente. Em operacao normal, ele fica ativo.

Para repetir a validacao com o MySQL em funcionamento:

```powershell
python scripts\validar_mysql.py
```

O antigo prototipo de interface usa SQLite e permanece apenas como historico de desenvolvimento. A prova de conceito entregue e defendida neste material e a base MySQL; nao ha integracao confirmada entre aquela interface e o MySQL.
