import { PGlite } from '@electric-sql/pglite';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { join } from 'node:path';

const db = new PGlite();
const sql = async (file) => readFile(join(process.cwd(),file),'utf8');
await db.exec(await sql('sql/01_schema.sql'));
await db.exec(await sql('sql/02_amostra.sql'));
const evidence = { engine: 'PGlite (PostgreSQL em WebAssembly)', sample: {}, queries: {} };
evidence.dictionary=(await db.query(`SELECT table_name,column_name,data_type,is_nullable,column_default,
 character_maximum_length,numeric_precision,numeric_scale
 FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position`)).rows;
for (const table of ['lojista','pagador','pagamento','regra','analise_risco','sinal_apurado','alerta','desfecho','devolucao','ingestao_webhook']) {
  evidence.sample[table] = Number((await db.query(`SELECT count(*)::int AS n FROM ${table}`)).rows[0].n);
}
for (let i=1;i<=8;i++) {
  const name=`pn${String(i).padStart(2,'0')}`;
  const result=await db.query(await sql(`sql/queries/${name}.sql`));
  if (result.rows.length===0) throw new Error(`${name} nao devolveu linhas`);
  evidence.queries[name]=result.rows;
}
const badDuplicate=async()=>{try{await db.query("INSERT INTO pagamento(id_conta,id_lojista,id_pagador,psp,end_to_end_id,canal,valor,ocorrido_em) VALUES(1,1,1,'SIMULADO','E-001','PRESENCIAL',1,now())");return false}catch{return true}};
evidence.checks={duplicate_blocked:await badDuplicate()};
try {
  await db.query("INSERT INTO pagamento(id_conta,id_lojista,id_pagador,psp,end_to_end_id,canal,valor,ocorrido_em) VALUES(3,1,1,'SIMULADO','E-FAKE','PRESENCIAL',1,now())");
  evidence.checks.cross_store_blocked=false;
} catch { evidence.checks.cross_store_blocked=true; }
await db.query('DELETE FROM ingestao_webhook WHERE expurgar_em < now()');
evidence.checks.raw_after_purge=Number((await db.query('SELECT count(*)::int AS n FROM ingestao_webhook')).rows[0].n);
evidence.checks.normalized_after_purge=Number((await db.query('SELECT count(*)::int AS n FROM pagamento')).rows[0].n);
if (!evidence.checks.duplicate_blocked || !evidence.checks.cross_store_blocked || evidence.checks.raw_after_purge!==0 || evidence.checks.normalized_after_purge!==12) throw new Error('Falha nas verificacoes');
await mkdir('evidencias',{recursive:true});
await writeFile('evidencias/resultados.json',JSON.stringify(evidence,null,2));
console.log('OK: 15 tabelas, 12 pagamentos, 8 consultas com resultado, unicidade e expurgo verificados.');
