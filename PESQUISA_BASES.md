# Aplicações existentes para a nova A3

Pesquisa em 23/11/2026. O enunciado da A3 exige sobretudo escolha e modelagem do banco, qualidade dos dados, banco real com amostra e pelo menos cinco consultas com resultados. Uma tela visual ajuda a explicar essas decisões, mas não substitui a prova de conceito de dados.

| Aplicação | O que mostra | Reuso de código | Adequação à A3 |
|---|---|---|---|
| [Food To Save](https://www.foodtosave.com.br/) | Sacolas surpresa de excedentes vendidas com desconto | Produto fechado; inspiração de fluxo | Boa referência de problema e experiência do consumidor |
| [Too Good To Go](https://www.toogoodtogo.com/en-us/how-does-the-app-work) | Reserva, pagamento e retirada em janela definida | Produto fechado; inspiração de fluxo | Boa referência de operação e prazo de retirada |
| [Olio](https://olioapp.com/business/food-safety/) | Redistribuição comunitária, voluntários e segurança alimentar | Produto fechado; inspiração de governança | Boa referência para doação e rastreio |
| [RescuBite](https://github.com/chayma-saad/RescuBite) | Ofertas, mapa, perfis, reservas, gráficos e previsão simulada | [Licença MIT](https://github.com/chayma-saad/RescuBite/blob/main/LICENSE); pode ser adaptado com crédito | **Melhor base visual e local** encontrada para um protótipo em cinco dias |
| [foodbank](https://github.com/ava-wei666/foodbank) | Inventário por lote, aplicações e análises, com PostgreSQL | Licença MIT no repositório | Base de dados mais ampla, porém muito maior e dependente de serviços e conceitos britânicos |

## Verificação da base RescuBite

Commit examinado: `4820fac374747527fa09bd60ff3cda7d1604229d`.

- `npm ci`, criação do SQLite, carga da amostra e `npm run build` concluíram neste computador.
- A tela de ofertas exibiu quatro sacolas após a carga e o botão do mapa abriu a visualização. Os marcadores apareceram; os blocos do mapa ficaram cinza no navegador de teste, então tiles externos não são confiáveis para o pitch sem alternativa local.
- A página inicial exibiu indicadores públicos zerados apesar da amostra. O texto de marketing traz números fixos. Isso precisa ser ligado a consultas reais do banco ou retirado.
- O código de reserva primeiro lê a quantidade, depois insere a reserva e por fim decrementa o saldo em operações independentes. Não há transação ou atualização condicional que impeça duas reservas simultâneas de ultrapassar o estoque. A rota de doação tem o mesmo tipo de risco.
- O gráfico de impacto lê a tabela `ImpactLog`, que é semeada separadamente do ciclo de reservas. Reservar uma sacola não prova que o alimento foi recolhido e não deve aumentar automaticamente a métrica “resgatado”.
- O pacote declara `AI`, mas a [documentação da autora](https://github.com/chayma-saad/RescuBite) explica que a previsão é uma fórmula determinística. Na defesa, chamar de estimativa baseada em regras.
- O `npm ci` apontou 21 alertas de dependência, incluindo 2 críticos. Antes de entregar uma adaptação, revisar dependências e a superfície usada no pitch.

## Recomendação

Usar RescuBite como **ponto de partida**, preservando a licença e o crédito à autora, e reduzir o escopo para um fluxo que o grupo consiga demonstrar e explicar:

1. Restaurante registra excedente com quantidade, validade e local.
2. Instituição visualiza ofertas compatíveis no mapa e reserva.
3. Banco confirma a reserva em transação, impedindo saldo negativo ou duplicidade.
4. Retirada é confirmada; só então o painel soma quilos resgatados.
5. Painel e cinco consultas SQL respondem: excedente por categoria, tempo médio até reserva, taxa de resgate, instituições atendidas e lotes próximos do vencimento.

Para o pitch, usar dados fictícios de São Paulo, interface em português e mapa que funcione mesmo sem internet. Documentar as alterações feitas pelo grupo e declarar o uso de IA, como pede o enunciado. Não apresentar a base de terceiros sem essas adaptações como projeto concluído.
