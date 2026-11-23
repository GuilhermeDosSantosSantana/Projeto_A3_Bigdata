import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,rm} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const port=3107;
const base=`http://127.0.0.1:${port}`;
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function start(dir){
 const child=spawn(process.execPath,['app/server.mjs'],{cwd:root,env:{...process.env,PORT:String(port),CONFIA_DATA_DIR:dir},stdio:['ignore','pipe','pipe']});
 let output='';child.stdout.on('data',d=>output+=d);child.stderr.on('data',d=>output+=d);
 for(let i=0;i<100;i++){
  if(child.exitCode!==null)throw Error(`Servidor parou: ${output}`);
  try{if((await fetch(`${base}/api/state`)).ok)return child;}catch{}
  await wait(100);
 }
 child.kill();throw Error(`Servidor não iniciou: ${output}`);
}
async function req(url,method='GET',data){const r=await fetch(base+url,{method,headers:{'content-type':'application/json'},body:data?JSON.stringify(data):undefined});const v=await r.json();assert.ok(r.ok,JSON.stringify(v));return v;}
test('criação pendente, confirmação, vereditos, idempotência e persistência',async()=>{
 const testRoot=path.join(root,'data');
 const dir=await mkdtemp(path.join(testRoot,'test-'));
 assert.ok(path.resolve(dir).startsWith(path.resolve(testRoot)+path.sep));
 let child;
 try{
  child=await start(dir);
  assert.match(await (await fetch(base+'/')).text(),/Saiba quando pode entregar/);
  assert.match(await (await fetch(base+'/laboratorio')).text(),/Simule a chegada de um Pix/);
  for(const [scenario,verdict,delivery] of [['aprovado','APROVADO','LIBERADA'],['analise','EM_ANALISE','RETIDA'],['recusado','RECUSADO','RETIDA']]){
   const intent=await req('/api/intents','POST',{scenario});
   assert.equal(intent.status,'PENDENTE');
   assert.equal((await req('/api/state')).payments.length,scenario==='aprovado'?0:scenario==='analise'?1:2);
   const result=await req(`/api/intents/${intent.id}/confirm`,'POST');
   assert.equal(result.verdict,verdict);assert.equal(result.delivery,delivery);
   if(scenario==='recusado'){
    assert.ok(result.reasons.some(r=>r.text.includes('contestação')));
    assert.ok(!result.reasons.some(r=>r.text.includes('primeira compra')));
   }
   const repeat=await req(`/api/intents/${intent.id}/confirm`,'POST');
   assert.equal(repeat.duplicate,true);assert.equal(repeat.verdict,verdict);
  }
  const repeatedReview=await req('/api/intents','POST',{scenario:'analise'});
  assert.ok(repeatedReview.amount>2800);
  const repeatedResult=await req(`/api/intents/${repeatedReview.id}/confirm`,'POST');
  assert.equal(repeatedResult.verdict,'EM_ANALISE');
  assert.equal((await req('/api/state')).payments.length,4);
  const latest=(await req('/api/state')).payments[0];
  assert.ok(latest.reasons.length>=2);
  child.kill();await new Promise(r=>child.once('exit',r));child=null;
  child=await start(dir);
  assert.equal((await req('/api/state')).payments.length,4);
 }finally{
  if(child){child.kill();await new Promise(r=>child.once('exit',r));}
  await rm(dir,{recursive:true,force:true});
 }
});
