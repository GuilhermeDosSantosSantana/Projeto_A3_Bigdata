const $=id=>document.getElementById(id);
let current=null;
const money=n=>Number(n).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
const request=async(url,options={})=>{const r=await fetch(url,{headers:{'content-type':'application/json'},...options});const j=await r.json();if(!r.ok)throw Error(j.error||`Erro ${r.status}`);return j;};
async function refresh(){
 const s=await request('/api/state');const host=$('history');host.replaceChildren();
 if(!s.payments.length){host.className='empty';host.textContent='Ainda não há pagamentos confirmados nesta demonstração.';return;}
 host.className='';const t=document.createElement('table');const h=document.createElement('tr');
 for(const x of ['ID','Valor','Situação','Veredito','Score','Registrado']){const th=document.createElement('th');th.textContent=x;h.append(th);}t.append(h);
 for(const p of s.payments){const tr=document.createElement('tr');for(const x of [p.end_to_end_id.slice(0,12)+'…',money(p.valor),p.situacao_entrega,p.veredito,p.score,new Date(p.ocorrido_em).toLocaleString('pt-BR')]){const td=document.createElement('td');if(x===p.veredito){const b=document.createElement('span');b.className=`badge ${p.veredito}`;b.textContent=x;td.append(b);}else td.textContent=x;tr.append(td);}t.append(tr);}host.append(t);
}
function show(id,text){const e=$(id);e.textContent=text;e.classList.remove('hidden');}
$('create').onclick=async()=>{const b=$('create');b.disabled=true;try{const v=await request('/api/intents',{method:'POST',body:JSON.stringify({scenario:$('scenario').value})});current=v.id;show('created',`Pagamento ${v.id.slice(0,8)} criado por ${money(v.amount)}. Estado: PENDENTE.`);show('pending','Aguardando confirmação do provedor. Nenhum pagamento foi registrado ainda.');$('confirm').classList.remove('hidden');$('verdict').classList.add('hidden');}catch(e){show('created',`Erro: ${e.message}`)}finally{b.disabled=false}};
$('confirm').onclick=async()=>{if(!current)return;const b=$('confirm');b.disabled=true;try{const r=await request(`/api/intents/${current}/confirm`,{method:'POST'});show('created',`Pagamento ${current.slice(0,8)} confirmado pelo provedor simulado.`);show('pending','Provedor local confirmou o pagamento. A API reconsultou o estado e registrou a decisão.');show('verdict',`${r.verdict} · score ${r.score}/100 · entrega ${r.delivery}. Motivos: ${r.reasons.length?r.reasons.map(x=>x.text).join(' '):'nenhum sinal de risco'}. ${r.duplicate?'Reenvio idempotente.':''} Abra a visão do lojista para ver a mensagem final.`);await refresh();}catch(e){show('verdict',`Erro: ${e.message}`)}finally{b.disabled=false}};
$('refresh').onclick=()=>refresh().catch(e=>show('history',`Erro: ${e.message}`));
refresh().catch(e=>show('history',`Erro: ${e.message}`));
