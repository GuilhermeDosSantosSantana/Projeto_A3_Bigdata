# Nova A3 — resgate de alimentos

O tema escolhido é redistribuir excedentes de restaurantes e mercados antes do vencimento. A implementação anterior, CONFIA, foi retirada da versão ativa e pode ser recuperada pela tag Git `confia-archive-2026-11-23`.

Estamos avaliando aplicações existentes antes de adaptar uma delas. O comparativo e a decisão técnica estão em [PESQUISA_BASES.md](PESQUISA_BASES.md).

## Base local para avaliação

Uma cópia de estudo do projeto aberto RescuBite está em `referencias/RescuBite/` (ignorada pelo Git principal). Ela é uma referência de terceiros, ainda não é a entrega da A3. Para executar no Windows:

```powershell
cd referencias/RescuBite
npm ci
npm run db:push
npm run db:seed
npm run dev
```

Abra `http://localhost:3000/browse`. Use `localhost`, pois o servidor de desenvolvimento da versão testada bloqueou recursos quando aberto como `127.0.0.1`. O banco de demonstração fica em `referencias/RescuBite/prisma/dev.db`.

O novo relatório, as consultas exigidas no enunciado e o pitch ainda serão feitos após a escolha da base. Nenhum dado desta cópia deve ser apresentado como resultado do grupo sem adaptação, teste e atribuição à autora.
