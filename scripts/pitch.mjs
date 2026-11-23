import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation, PresentationFile} from '@oai/artifact-tool';

const workspaceDir=process.cwd();
const skillDir='C:\\Users\\gsantana5\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.1119.11507\\skills\\presentations';
const build=path.join(workspaceDir,'.pitch-build');
const out=path.join(workspaceDir,'output','CONFIA_pitch_A3.pptx');
await fs.mkdir(build,{recursive:true});await fs.mkdir(path.dirname(out),{recursive:true});
const pres=Presentation.create({slideSize:{width:1280,height:720}});
const navy='#17345b', blue='#3d78af', ink='#263747', muted='#66788a', white='#ffffff';
function box(slide,text,x,y,w,h,size=24,color=ink,bold=false){
 const sh=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{style:'solid',fill:'none',width:0}});
 sh.text=text;sh.text.style={fontFamily:'Arial',fontSize:`${size}pt`,color,bold,verticalAlignment:'middle'};return sh;
}
function slide(title,n){const s=pres.slides.add();s.background.fill=white;box(s,title,72,48,1136,76,31,navy,true);box(s,`CONFIA · A3  |  ${n}/6`,72,665,1136,25,11,muted);return s;}
let s=pres.slides.add();s.background.fill=navy;
box(s,'CONFIA',72,180,1136,110,54,white,true);
box(s,'Antifraude para Pix recebido',72,300,1136,65,28,white);
box(s,'Decisão de banco, modelagem e prova de conceito',72,392,1136,45,19,'#dbe9f6');
box(s,'A3 · Análise de Dados e Big Data',72,620,1136,35,15,'#dbe9f6');
s=slide('A perda acontece depois do Pix',2);
box(s,'O pagamento entra. A mercadoria sai. Uma contestação posterior pode retirar o valor.',72,160,1130,110,27,ink,true);
box(s,'O CONFIA avaliaria sinais explicáveis antes de liberar a entrega.',72,315,1100,75,23,blue);
box(s,'Público: pequenos lojistas com venda presencial e online.',72,450,1100,60,20,ink);
s=slide('Um registro, 15 entidades',3);
box(s,'LOJISTA  →  CONTA  →  PAGAMENTO  →  ANÁLISE  →  ALERTA',72,160,1130,80,25,blue,true);
box(s,'PAGADOR é identificado dentro da loja. Nove sinais ficam associados à análise.',72,285,1100,95,22,ink);
box(s,'O webhook bruto expira em 7 dias; o pagamento normalizado permanece.',72,440,1100,85,22,ink);
s=slide('Por que PostgreSQL',4);
box(s,'ACID + chaves estrangeiras + UNIQUE: decisão e pagamento coerentes',72,150,1136,65,21,ink);
box(s,'JSONB/GIN: evento variável consultável',72,235,1136,65,21,ink);
box(s,'Índices parciais: filas pequenas e rápidas',72,320,1136,65,21,ink);
box(s,'Percentis e janelas: oito perguntas analíticas no mesmo motor',72,405,1136,65,21,ink);
box(s,'MongoDB, MySQL, Redis e grafos foram comparados para este caso.',72,530,1136,65,17,muted);
s=slide('A prova de conceito funciona',5);
box(s,'12 pagamentos  ·  9 regras  ·  108 sinais  ·  8 consultas',72,155,1136,80,26,blue,true);
box(s,'p95 de latência sintética: 258 ms',72,270,1136,60,22,ink);
box(s,'R$ 1.500 em exposição retida na amostra fictícia',72,350,1136,60,22,ink);
box(s,'Duplicidade e vínculo entre lojas bloqueados. Bruto expurgado; 12 pagamentos preservados.',72,450,1136,100,20,ink);
s=slide('O que a amostra prova',6);
box(s,'O esquema mantém integridade e as oito consultas retornam resultados.',72,165,1136,100,26,ink,true);
box(s,'Dois rótulos de fraude são insuficientes para medir eficácia real.',72,310,1136,70,22,ink);
box(s,'Próximo passo: integrar um PSP em sandbox e medir carga e precisão com dados maturados.',72,425,1136,115,22,blue);
for(let i=0;i<pres.slides.items.length;i++){
 const blob=await pres.export({slide:pres.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(build,`slide-${i+1}.png`),new Uint8Array(await blob.arrayBuffer()));
}
const draft=path.join(build,'candidate.pptx');await(await PresentationFile.exportPptx(pres)).save(draft);
const {finalizePresentation}=await import(pathToFileURL(path.join(skillDir,'container_tools','artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({workspaceDir,candidatePath:draft,finalPath:out,pythonExecutable:'C:\\Users\\gsantana5\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe',integrityValidatorPath:path.join(skillDir,'container_tools','inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skillDir,'container_tools','inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],explicitTotalSlideCount:6,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(build,'validation.json')});
console.log(JSON.stringify({out,result},null,2));
