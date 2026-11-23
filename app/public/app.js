const money=n=>Number(n).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
const date=v=>new Date(v).toLocaleString('pt-BR',{dateStyle:'medium',timeStyle:'short',timeZone:'America/Sao_Paulo'});
const $=id=>document.getElementById(id);
let selectedId=null,latestId=null;
const states={
 APROVADO:{label:'Entrega liberada',eyebrow:'PAGAMENTO CONFIRMADO',action:'Pode entregar a mercadoria.',detail:'O Pix foi confirmado pelo provedor simulado e nenhum sinal de risco foi detectado nesta análise.',className:'approved'},
 EM_ANALISE:{label:'Em análise',eyebrow:'PAGAMENTO CONFIRMADO · ENTREGA RETIDA',action:'Aguarde a revisão. Não entregue ainda.',detail:'O Pix entrou, mas alguns sinais precisam de conferência antes da entrega.',className:'review'},
 RECUSADO:{label:'Entrega retida',eyebrow:'PAGAMENTO CONFIRMADO · RISCO ELEVADO',action:'Não entregue a mercadoria.',detail:'O Pix entrou, mas a combinação dos sinais abaixo indica risco elevado. A decisão não comprova fraude.',className:'blocked'}
};
function el(tag,cls,text){const x=document.createElement(tag);if(cls)x.className=cls;if(text!==undefined)x.textContent=text;return x;}
function renderDetail(p){
 const root=$('payment-detail');root.replaceChildren();
 if(!p){const empty=el('div','empty-state');empty.append(el('div','empty-icon','◌'),el('h2','', 'Nenhum Pix recebido ainda'),el('p','', 'Quando um pagamento for confirmado, a decisão de entrega aparecerá aqui.'),el('a','primary-link','Abrir laboratório de teste →'));empty.lastChild.href='/laboratorio';root.append(empty);return;}
 const state=states[p.veredito]||states.EM_ANALISE;root.className=`detail-card ${state.className}`;
 const top=el('div','detail-top');const topLeft=el('div');topLeft.append(el('p','eyebrow',state.eyebrow),el('h2','amount',money(p.valor)),el('p','payment-date',`Recebido em ${date(p.ocorrido_em)}`));top.append(topLeft,el('span','status-pill',state.label));root.append(top);
 const decision=el('div','decision');decision.append(el('span','decision-mark',p.veredito==='APROVADO'?'✓':'!'));
 const decisionText=el('div');decisionText.append(el('p','decision-label','DECISÃO PARA A ENTREGA'),el('h3','',state.action),el('p','',state.detail));decision.append(decisionText);root.append(decision);
 const reasons=el('div','reasons');reasons.append(el('h3','',p.reasons.length?'Por que a entrega foi retida':'Por que foi liberada'));
 if(p.reasons.length){const list=el('ul','reason-list');for(const reason of p.reasons)list.append(el('li','',reason.text));reasons.append(list);}
 else reasons.append(el('p','', 'O provedor confirmou o pagamento e as regras disponíveis não apontaram risco nesta transação.'));
 root.append(reasons);
 const meta=el('div','detail-meta');meta.append(el('span','',`Transação ${p.end_to_end_id}`),el('span','', 'Provedor local confirmado'),el('span','',`Análise em ${p.latencia_ms} ms`));root.append(meta);
}
function renderList(payments){const host=$('payment-list');host.replaceChildren();if(!payments.length){host.append(el('p','list-empty','Os recebimentos confirmados aparecerão aqui.'));return;}
 for(const p of payments){const state=states[p.veredito]||states.EM_ANALISE;const row=el('button',`payment-row ${selectedId===p.id_pagamento?'selected':''}`);row.type='button';row.append(el('span','row-amount',money(p.valor)),el('span','row-date',date(p.ocorrido_em)),el('span',`row-status ${state.className}`,state.label),el('span','row-arrow','→'));row.onclick=()=>{selectedId=p.id_pagamento;renderDetail(p);renderList(payments);window.scrollTo({top:0,behavior:'smooth'});};host.append(row);}}
async function refresh(){try{const response=await fetch('/api/state',{cache:'no-store'});if(!response.ok)throw Error('Falha na API');const {payments}=await response.json();
  if(payments.length && latestId!==null && payments[0].id_pagamento!==latestId){$('new-alert').classList.remove('hidden');selectedId=payments[0].id_pagamento;}
  latestId=payments[0]?.id_pagamento??null;
  if(selectedId===null)selectedId=latestId;
  const selected=payments.find(p=>p.id_pagamento===selectedId)||payments[0];
  renderDetail(selected);renderList(payments);
 }catch{$('payment-detail').textContent='Não foi possível carregar os recebimentos. Confira se o servidor local está ativo.';}}
$('refresh').onclick=()=>refresh();refresh();setInterval(refresh,3000);
