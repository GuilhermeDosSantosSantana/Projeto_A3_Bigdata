import {createServer} from 'node:http';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {randomBytes,randomUUID,createHmac,timingSafeEqual} from 'node:crypto';
import {PGlite} from '@electric-sql/pglite';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const dataDir=path.resolve(process.env.CONFIA_DATA_DIR || path.join(root,'data'));
const port=Number(process.env.PORT || 3000);
await mkdir(dataDir,{recursive:true});
const secretFile=path.join(dataDir,'hmac.key');
let secret;
try {secret=await readFile(secretFile);} catch {secret=randomBytes(32);await writeFile(secretFile,secret,{flag:'wx'});}
const hmac=value=>createHmac('sha256',secret).update(value).digest('hex');
const db=new PGlite(path.join(dataDir,'postgres'));
await db.waitReady;
const existing=await db.query("SELECT count(*)::int AS n FROM pg_tables WHERE schemaname='public' AND tablename='pagamento'");
if(Number(existing.rows[0].n)===0){
 await db.exec(await readFile(path.join(root,'sql','01_schema.sql'),'utf8'));
 await db.exec(await readFile(path.join(root,'sql','02_amostra.sql'),'utf8'));
}
// A fixture usa IDs explícitos; sincronize as sequências antes de receber eventos reais do teste.
for(const [table,key] of [['lojista','id_lojista'],['usuario','id_usuario'],['conta_recebedora','id_conta'],['pagador','id_pagador'],['ingestao_webhook','id_ingestao'],['pagamento','id_pagamento'],['cobranca_esperada','id_cobranca'],['regra','id_regra'],['analise_risco','id_analise'],['sinal_apurado','id_sinal'],['alerta','id_alerta'],['desfecho','id_desfecho'],['devolucao','id_devolucao'],['notificacao','id_notificacao'],['auditoria','id_auditoria']]){
 const n=Number((await db.query(`SELECT coalesce(max(${key}),0)::int AS n FROM ${table}`)).rows[0].n);
 await db.query('SELECT setval(pg_get_serial_sequence($1,$2),$3,$4)',[table,key,Math.max(1,n),n>0]);
}
// Corrige apenas decisões locais antigas que combinaram, por engano, "primeira compra" e contestação prévia.
await db.exec(`UPDATE sinal_apurado s SET disparou=false, contribuicao=0
 FROM analise_risco a JOIN pagamento p ON p.id_pagamento=a.id_pagamento
 JOIN regra r ON r.codigo='RN04' AND r.versao=1
 WHERE s.id_analise=a.id_analise AND s.id_regra=r.id_regra AND s.disparou
 AND p.psp='SIMULADOR_LOCAL' AND EXISTS (
   SELECT 1 FROM sinal_apurado sx JOIN regra rx ON rx.id_regra=sx.id_regra
   WHERE sx.id_analise=a.id_analise AND sx.disparou AND rx.codigo='RN09'
 );
 UPDATE analise_risco a SET score=LEAST(100,(
   SELECT COALESCE(SUM(s.contribuicao),0) FROM sinal_apurado s WHERE s.id_analise=a.id_analise
 )) WHERE EXISTS (SELECT 1 FROM pagamento p WHERE p.id_pagamento=a.id_pagamento AND p.psp='SIMULADOR_LOCAL');`);
const providerFile=path.join(dataDir,'provedor-simulado.json');
let intents=[];
try{intents=JSON.parse(await readFile(providerFile,'utf8'));}catch{await writeFile(providerFile,'[]');}
const saveProvider=()=>writeFile(providerFile,JSON.stringify(intents,null,2));
let queue=Promise.resolve();
function exclusive(fn){const next=queue.then(fn,fn);queue=next.catch(()=>{});return next;}
const amounts={aprovado:42.50,analise:null,recusado:2800};
const reasonText={
 RN09:'Este pagador já teve uma contestação registrada nesta loja.',
 RN05:'O nome associado ao pagador diverge do histórico desta loja.',
 RN08:'Houve um pagamento pequeno seguido de outro muito maior em pouco tempo.',
 RN04:'É a primeira compra deste pagador e o valor está acima do padrão da loja.',
 RN06:'O mesmo pagador fez vários pagamentos em poucos minutos.',
 RN07:'O valor está acima do padrão recente da loja.',
 RN12:'O pagador apareceu em várias contas desta loja no mesmo dia.',
 RN11:'A loja recebeu uma rajada incomum de pagamentos.',
 RN10:'O pagamento ocorreu fora do horário informado pela loja.'
};
function json(res,status,obj){res.writeHead(status,{'content-type':'application/json; charset=utf-8','cache-control':'no-store'});res.end(JSON.stringify(obj));}
async function body(req){let s='';for await(const c of req){s+=c;if(s.length>8192)throw Error('Corpo grande demais');}return s?JSON.parse(s):{};}
async function state(){
 const payments=(await db.query(`SELECT p.id_pagamento,p.end_to_end_id,p.valor,p.ocorrido_em,p.situacao_entrega,
 a.id_analise,a.veredito,a.score,a.latencia_ms,n.conteudo AS notificacao
 FROM pagamento p LEFT JOIN analise_risco a USING(id_pagamento)
 LEFT JOIN notificacao n USING(id_pagamento)
 WHERE p.psp='SIMULADOR_LOCAL' ORDER BY p.id_pagamento DESC LIMIT 30`)).rows;
 for(const payment of payments){
  const signals=(await db.query(`SELECT r.codigo FROM sinal_apurado s JOIN regra r USING(id_regra)
   WHERE s.id_analise=$1 AND s.disparou ORDER BY s.contribuicao DESC,r.codigo`,[payment.id_analise])).rows;
  payment.reasons=signals.map(x=>({code:x.codigo,text:reasonText[x.codigo] || x.codigo}));
 }
 return {mode:'SIMULADOR_LOCAL',intents:intents.slice(-10).reverse().map(({id,scenario,amount,status,createdAt})=>({id,scenario,amount,status,createdAt})),payments};
}
async function processConfirmed(intent){
 // O aviso apenas aciona a leitura do provedor simulado; nunca decide pelo corpo do aviso.
 const pspRecord=intents.find(x=>x.id===intent.id);
 if(!pspRecord || pspRecord.status!=='CONFIRMADO') throw Error('Pagamento não confirmado pelo provedor');
 const e2e=`SIM-${pspRecord.id}`;
 const duplicate=await db.query('SELECT id_pagamento FROM pagamento WHERE psp=$1 AND end_to_end_id=$2',['SIMULADOR_LOCAL',e2e]);
 if(duplicate.rows.length){
  const idPagamento=Number(duplicate.rows[0].id_pagamento);
  const saved=(await db.query(`SELECT p.situacao_entrega,a.veredito,a.score,a.id_analise
   FROM pagamento p JOIN analise_risco a USING(id_pagamento) WHERE p.id_pagamento=$1`,[idPagamento])).rows[0];
  const signals=(await db.query(`SELECT r.codigo FROM sinal_apurado s JOIN regra r USING(id_regra)
   WHERE s.id_analise=$1 AND s.disparou ORDER BY s.contribuicao DESC,r.codigo`,[saved.id_analise])).rows.map(x=>x.codigo);
  return {duplicate:true,idPagamento,verdict:saved.veredito,score:Number(saved.score),delivery:saved.situacao_entrega,
   signals,reasons:signals.map(code=>({code,text:reasonText[code]}))};
 }
 const began=Date.now();
 await db.exec('BEGIN');
 try{
  await db.query(`INSERT INTO ingestao_webhook(psp,origem_autenticada,confirmado_na_api,payload,situacao_processamento)
   VALUES($1,true,true,$2::jsonb,'PROCESSADO')`,['SIMULADOR_LOCAL',JSON.stringify({event:'PAYMENT_RECEIVED',paymentId:pspRecord.id})]);
  const docHash=hmac(pspRecord.document);
  const nameHash=hmac(pspRecord.name.trim().toUpperCase());
  if(pspRecord.scenario==='recusado'){
   await db.query(`INSERT INTO pagador(id_lojista,documento_hash,nome_hash,qtd_contestacoes)
    VALUES(1,$1,$2,1) ON CONFLICT(id_lojista,documento_hash) DO NOTHING`,[docHash,hmac('NOME ANTERIOR')]);
  }
  const found=await db.query('SELECT id_pagador,nome_hash,qtd_pagamentos,qtd_contestacoes FROM pagador WHERE id_lojista=1 AND documento_hash=$1',[docHash]);
  const prior=found.rows[0];
  let idPagador;
  if(prior) idPagador=Number(prior.id_pagador);
  else {idPagador=Number((await db.query(`INSERT INTO pagador(id_lojista,documento_hash,nome_hash)
   VALUES(1,$1,$2) RETURNING id_pagador`,[docHash,nameHash])).rows[0].id_pagador);}
  const stats=(await db.query(`SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY valor) AS p95,
   percentile_cont(0.99) WITHIN GROUP (ORDER BY valor) AS p99 FROM pagamento WHERE id_lojista=1`)).rows[0];
  const localHour=Number(new Intl.DateTimeFormat('en-US',{timeZone:'America/Sao_Paulo',hour:'2-digit',hourCycle:'h23'}).format(new Date()));
  const fired=new Set();
  if(Number(prior?.qtd_contestacoes || 0)>0) fired.add('RN09');
  if(prior?.nome_hash && prior.nome_hash.trim()!==nameHash) fired.add('RN05');
  if(!prior && pspRecord.amount>Number(stats.p95)) fired.add('RN04');
  if(pspRecord.amount>Number(stats.p99)) fired.add('RN07');
  if(localHour<8 || localHour>=20) fired.add('RN10');
  const recent=(await db.query(`SELECT valor FROM pagamento WHERE id_pagador=$1 AND ocorrido_em>=now()-interval '30 minutes'`,[idPagador])).rows;
  if(recent.some(x=>Number(x.valor)<=5 && pspRecord.amount>=Number(x.valor)*20))fired.add('RN08');
  const rules=(await db.query('SELECT id_regra,codigo,peso FROM regra WHERE ativa=true AND versao=1 ORDER BY id_regra')).rows;
  const score=Math.min(100,rules.reduce((n,r)=>n+(fired.has(r.codigo)?Number(r.peso):0),0));
  let verdict=score>=75 && fired.size>=2?'RECUSADO':score>=40?'EM_ANALISE':'APROVADO';
  const delivery=verdict==='APROVADO'?'LIBERADA':'RETIDA';
  const pay=(await db.query(`INSERT INTO pagamento(id_conta,id_lojista,id_pagador,psp,end_to_end_id,canal,valor,ocorrido_em,situacao_entrega)
   VALUES(1,1,$1,'SIMULADOR_LOCAL',$2,'PRESENCIAL',$3,now(),$4) RETURNING id_pagamento`,[idPagador,e2e,pspRecord.amount,delivery])).rows[0];
  const idPagamento=Number(pay.id_pagamento);
  const analysis=(await db.query(`INSERT INTO analise_risco(id_pagamento,veredito,score,degradada,latencia_ms,versao_catalogo)
   VALUES($1,$2,$3,false,$4,1) RETURNING id_analise`,[idPagamento,verdict,score,Date.now()-began])).rows[0];
  const idAnalise=Number(analysis.id_analise);
  for(const r of rules)await db.query(`INSERT INTO sinal_apurado(id_analise,id_regra,disparou,contribuicao)
   VALUES($1,$2,$3,$4)`,[idAnalise,Number(r.id_regra),fired.has(r.codigo),fired.has(r.codigo)?Number(r.peso):0]);
  if(verdict!=='APROVADO')await db.query(`INSERT INTO alerta(id_analise,situacao,aberto_em) VALUES($1,'ABERTO',now())`,[idAnalise]);
  await db.query(`INSERT INTO notificacao(id_pagamento,id_usuario,canal_envio,conteudo,enviada_em)
   VALUES($1,1,'TELA',$2,now())`,[idPagamento,`Recebido R$ ${pspRecord.amount.toFixed(2)}. ${verdict}.`]);
  await db.query(`UPDATE pagador SET qtd_pagamentos=qtd_pagamentos+1,
   primeiro_pagamento_em=coalesce(primeiro_pagamento_em,now()),ultimo_pagamento_em=now() WHERE id_pagador=$1`,[idPagador]);
  await db.exec('COMMIT');
  return {duplicate:false,idPagamento,verdict,score,delivery,signals:[...fired],reasons:[...fired].map(code=>({code,text:reasonText[code]}))};
 }catch(e){await db.exec('ROLLBACK');throw e;}
}
const server=createServer(async(req,res)=>{
 try{
  const url=new URL(req.url,'http://localhost');
  if(req.method==='GET' && url.pathname==='/api/state')return json(res,200,await state());
  if(req.method==='POST' && url.pathname==='/api/intents'){
   const input=await body(req);if(!Object.hasOwn(amounts,input.scenario))return json(res,400,{error:'Cenário inválido'});
   return json(res,201,await exclusive(async()=>{
    const id=randomUUID();const scenario=input.scenario;
    let amount=amounts[scenario];
    if(scenario==='analise'){
      const stats=(await db.query(`SELECT percentile_cont(0.99) WITHIN GROUP (ORDER BY valor) AS p99
       FROM pagamento WHERE id_lojista=1`)).rows[0];
      amount=Math.max(2800,Math.ceil(Number(stats.p99 || 0)/100)*100+100);
    }
    const intent={id,scenario,amount,status:'PENDENTE',document:`FICTICIO-${id}`,name:scenario==='recusado'?'NOME DIVERGENTE':'CLIENTE FICTICIO',createdAt:new Date().toISOString()};
    intents.push(intent);await saveProvider();return {id,scenario,amount:intent.amount,status:intent.status};
   }));
  }
  const m=url.pathname.match(/^\/api\/intents\/([a-f0-9-]+)\/confirm$/);
  if(req.method==='POST' && m){
   return json(res,200,await exclusive(async()=>{
    const intent=intents.find(x=>x.id===m[1]);if(!intent)throw Error('Cobrança não encontrada');
    intent.status='CONFIRMADO';await saveProvider();
    const result=await processConfirmed(intent);return {...result,providerStatus:intent.status};
   }));
  }
  if(req.method==='GET' && (url.pathname==='/' || url.pathname==='/laboratorio' || url.pathname==='/app.js' || url.pathname==='/lab.js' || url.pathname==='/style.css')){
   const file=url.pathname==='/'?'index.html':url.pathname==='/laboratorio'?'laboratorio.html':url.pathname.slice(1);
   const content=await readFile(path.join(root,'app','public',file));
   res.writeHead(200,{'content-type':file.endsWith('.js')?'text/javascript; charset=utf-8':file.endsWith('.css')?'text/css; charset=utf-8':'text/html; charset=utf-8'});res.end(content);return;
  }
  json(res,404,{error:'Rota não encontrada'});
 }catch(e){json(res,500,{error:e.message});}
});
server.listen(port,'127.0.0.1',()=>console.log(`CONFIA aberto em http://127.0.0.1:${port}`));
export {server,db};
