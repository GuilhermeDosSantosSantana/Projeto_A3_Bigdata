# Validacao final do GIRO — 25/11/2026

## O que foi executado

| Camada | Verificacao | Resultado |
|---|---|---|
| MySQL | 7 tabelas, 38 campos, 7 consultas de negocio e 1 de qualidade | Passou; qualidade retornou 0 problemas |
| MySQL | Gatilho contra saldo negativo, motivo obrigatorio, FK de cliente | Rejeicoes confirmadas |
| Backup | Dump SQL, gzip e restauracao em outro esquema | Contagens iguais nas 7 tabelas; hash do gzip confere |
| API de escrita | Produto com ID automatico, 2 lotes, venda com cliente, perda, FEFO e recusa por saldo | Passou |
| Navegador | 4 telas, cadastro, edicao, entrada, venda, perda, filtro, busca, paginacao e celular | Passou no Edge automatizado; sem erro JavaScript |
| API de leitura | Paginas de produtos/clientes/movimentacoes, filtros, detalhes e requisicoes invalidas | Passou |
| Cache | Redis indisponivel nesta sessao; cache local temporario | Primeira pagina do catalogo 5.810 ms (`MISS`); segunda 17 ms (`HIT`) |

As amostras finais do banco contem **2.009 produtos, 500.000 clientes, 2.507 lotes, 750.006 vendas e 755.015 eventos de estoque**. Uma venda pode gerar mais de um evento ao consumir dois lotes; por isso, a quantidade de eventos nao e a de vendas. Os dados sao sinteticos. Os arquivos `evidencias/mysql_resultados_consultas.json` e `evidencias/api_fluxos.json` guardam as contagens e tempos observados; os prints estao em `evidencias/giro_*.png`.

O Redis instalado no WSL nao permaneceu disponivel de forma confiavel nesta sessao. O servidor agora usa cache em memoria quando isso acontece. O MySQL continua sendo a unica fonte permanente, e a invalidacao ocorre apos cadastro, edicao, entrada, venda e perda. O primeiro acesso apos invalidacao ainda executa a consulta pesada; este resultado **nao e benchmark de producao**.

Para repetir a validacao (os dois testes de escrita deixam produtos sinteticos novos no banco):

```powershell
python -m scripts.testar_fluxo_web
python -m scripts.testar_front
python -m scripts.validar_api_leitura
python scripts/validar_mysql.py
```

O relatorio e regenerado por `python scripts/relatorio.py`, e o pacote por `python scripts/empacotar_pitch.py`.
