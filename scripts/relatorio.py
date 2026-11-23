"""Gera o relatorio final a partir das evidencias verificadas pelo npm run demo."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'evidencias/resultados.json').read_text(encoding='utf-8'))
pdfmetrics.registerFont(TTFont('Arial',r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold',r'C:\Windows\Fonts\arialbd.ttf'))
S=getSampleStyleSheet()
S.add(ParagraphStyle(name='BodyA',fontName='Arial',fontSize=9.2,leading=13.5,spaceAfter=7))
S.add(ParagraphStyle(name='H1A',fontName='Arial-Bold',fontSize=13,leading=17,textColor=colors.HexColor('#17345b'),spaceBefore=16,spaceAfter=8))
S.add(ParagraphStyle(name='H2A',fontName='Arial-Bold',fontSize=10.5,leading=14,textColor=colors.HexColor('#17345b'),spaceBefore=10,spaceAfter=5))
S.add(ParagraphStyle(name='TitleA',fontName='Arial-Bold',fontSize=23,leading=29,textColor=colors.HexColor('#17345b'),alignment=TA_CENTER,spaceAfter=15))
S.add(ParagraphStyle(name='SmallA',fontName='Arial',fontSize=7,leading=9,spaceAfter=3))
S.add(ParagraphStyle(name='CellA',fontName='Arial',fontSize=6.7,leading=8.5))
S.add(ParagraphStyle(name='CellHeadA',fontName='Arial-Bold',fontSize=6.8,leading=8.5,textColor=colors.white))
story=[]
def P(t,style='BodyA'): story.append(Paragraph(t,S[style]))
def H(t): P(t,'H1A')
def H2(t): P(t,'H2A')
def tbl(headers,rows,widths=None):
    x=[[Paragraph(escape(str(c)),S['CellHeadA']) for c in headers]]
    x += [[Paragraph(escape('—' if c is None else str(c)),S['CellA']) for c in row] for row in rows]
    t=Table(x,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#17345b')),('GRID',(0,0),(-1,-1),0.25,colors.HexColor('#cad5df')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f7fa')]),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story.append(t);story.append(Spacer(1,8))

P('CONFIA','TitleA')
P('Antifraude para Pix recebido: decisão de dados, modelagem e prova de conceito','TitleA')
P('A3 · Análise de Dados e Big Data · 23 de novembro de 2026','BodyA')
P('Grupo: ____________________________________________  Turma: __________  Professora: ____________________')
P('Este relatório registra um protótipo de dados executado com amostra integralmente fictícia. O serviço de Pix e a aplicação de produção não foram integrados nesta prova de conceito. Todos os números de resultado abaixo vêm da execução reproduzível dos scripts anexos.')

H('1. Problema, público e proposta de valor')
P('Pequenos lojistas que entregam mercadorias após receber Pix enfrentam duas perdas: comprovantes falsos e pagamentos efetivos que depois são contestados. O CONFIA propõe registrar o pagamento confirmado pelo provedor, avaliar sinais explicáveis e informar ao lojista se deve liberar a entrega, retê-la para análise ou recusá-la. O foco é a decisão após o recebimento, antes da entrega.')
P('Perguntas de negócio: como se distribuem os vereditos por canal e faixa de valor? Quais regras acertam nos casos rotulados? Qual a latência da análise? Quanto valor ficou retido em transações com histórico de contestação? Em que horários surgem casos rotulados? Quantos dias até uma contestação? Como a recorrência altera o risco? Qual o tamanho e o tempo de atendimento da fila humana?')
P('KPIs propostos: taxa de perdas confirmadas por valor recebido; precisão por regra após maturação do rótulo; proporção de pagamentos em análise; latência p95; tempo médio de fechamento de alertas. A amostra deste relatório só demonstra cálculo, não estima desempenho real.')

H('2. Diagnóstico dos dados')
P('Fontes previstas: eventos e reconsulta à API do provedor de pagamentos, cadastro do lojista, decisões de analistas e contestações posteriores. O evento bruto é semiestruturado (JSONB); pagamentos, contas, análises, sinais e desfechos são estruturados. O protótipo usa fixtures sintéticas e não faz chamadas ao provedor.')
tbl(['V','Diagnóstico e implicação'],[
('Volume','Hipótese de projeto: 50 lojas, cerca de 2,2 milhões de pagamentos/ano (aproximadamente 183 mil/mês) e 9 sinais por pagamento; testar carga antes de dimensionar infraestrutura.'),
('Velocidade','Eventos chegam continuamente e a decisão de entrega precisa ser rápida; índices por pagador, conta e tempo atendem o caminho operacional.'),
('Variedade','JSONB preserva formatos variáveis do evento; o modelo canônico relacional estabiliza a análise.'),
('Veracidade','Webhook isolado não prova liquidação; a arquitetura exige reconsulta ao provedor antes de decidir. Unicidade evita duplicação.'),
('Valor','O dado conecta pagamento, risco, decisão e contestação, permitindo medir exposição e calibrar regras.')],[55,440])
P('O perfil operacional é predominantemente escrita na ingestão e leitura seletiva por identidade e janela temporal. As consultas analíticas fazem agregações históricas e devem migrar para réplica de leitura quando concorrerem com decisões em tempo real.')

H('3. Escolha do banco de dados')
P('Escolhemos PostgreSQL relacional como sistema de registro: transações ACID mantêm pagamento, análise e alerta coerentes; chaves estrangeiras e CHECKs impedem estados inválidos; UNIQUE assegura idempotência; JSONB com índice GIN acomoda o evento variável; índices parciais mantêm filas pequenas; funções de janela e percentis atendem às perguntas analíticas. Um único motor reduz custo de operação e reconciliação entre stores.')
tbl(['Alternativa','Força','Motivo da rejeição inicial'],[
('MongoDB/documentos','Flexibilidade do payload','O núcleo de pagamentos tem relações e regras fortes; transações e integridade entre documentos aumentariam a complexidade.'),
('MySQL relacional','Transações e modelo familiar','Atende boa parte do núcleo, mas PostgreSQL oferece índice parcial e GIN/JSONB diretamente usados no desenho.'),
('Neo4j/grafos','Relações profundas','A ligação pagador–loja aqui tem profundidade 1 e é resolvida por JOIN; não há rede entre lojistas.'),
('Redis/chave-valor','Baixa latência','Seria cache posterior, sem substituir o registro durável e os controles transacionais.')],[105,130,260])
P('CAP não diferencia motores em operação normal de um único nó. Em futura arquitetura distribuída, a decisão de liberar mercadoria priorizaria consistência em falha de rede; indisponibilidade deve manter a entrega retida. Escala horizontal e disponibilidade precisam ser medidas, não presumidas. A escolha será revista se o p95 operacional superar 300 ms ou se uma consulta analítica superar 30 s em réplica.')

H('4. Organização e modelagem dos dados')
P('Modelo conceitual: lojista possui contas e pagadores identificados apenas no próprio escopo; conta recebe pagamentos; pagamento pertence a pagador e recebe no máximo uma análise; análise registra nove sinais e pode abrir alerta; alerta pode receber desfecho; pagamento pode ter devolução e notificação. Ingestão bruta relaciona-se logicamente ao pagamento, sem FK, para permitir expurgo.')
tbl(['Origem','Cardinalidade','Destino'],[('Lojista','1:N','Conta recebedora, usuário, pagador'),('Conta recebedora','1:N','Pagamento'),('Pagador na mesma loja','1:N','Pagamento'),('Pagamento','1:0..1','Análise de risco'),('Análise de risco','1:N','Sinal apurado'),('Análise de risco','1:0..1','Alerta'),('Alerta','1:0..1','Desfecho'),('Pagamento','1:N','Devolução e notificação'),('Ingestão webhook','vínculo lógico','Pagamento; sem FK para permitir expurgo')],[135,85,275])
P('Modelo lógico: 15 entidades — lojista, usuario, conta_recebedora, pagador, ingestao_webhook, pagamento, cobranca_esperada, regra, analise_risco, sinal_apurado, alerta, desfecho, devolucao, notificacao e auditoria. O esquema físico completo, com tipos, PKs, FKs, CHECKs e índices, está em sql/01_schema.sql. A identidade do pagador é única por (id_lojista, documento_hash), e (id_pagador, id_lojista) é referenciado pelo pagamento para impedir vínculo entre lojas.')
P('Normalização: atributos são atômicos, as entidades possuem chaves simples e os fatos de regra ficam em regra, separados dos fatos de pagamento. Os contadores de pagador são desnormalização explícita para leitura rápida; uma implantação deve mantê-los transacionalmente e reconciliá-los periodicamente. A contribuição do sinal é snapshot da versão da regra na análise. O protótipo não particiona pagamento: a chave global (psp, end_to_end_id) sustenta idempotência e FKs simples. Particionamento mensal futuro exige redesenhar todas as referências com chave composta ou manter tabela global de identidade da transação.')
tbl(['Índice','Consulta/controle beneficiado'],[
('UNIQUE (psp, end_to_end_id)','Idempotência de pagamento'),('pagamento (id_pagador, ocorrido_em)','Recorrência e janela de risco'),('pagamento (id_conta, ocorrido_em)','Perfil temporal da conta'),('pagamento WHERE situacao_entrega=RETIDA','Fila operacional'),('alerta WHERE situacao=ABERTO','Fila do analista'),('GIN ingestao_webhook(payload)','Investigação de evento variável'),('sinal_apurado (id_regra, disparou)','Precisão por regra')],[220,275])

H('5. Qualidade, governança e segurança')
P('Completude: campos críticos são NOT NULL; ausências opcionais ficam explícitas. Consistência: FK, CHECK e decisão degradada sem RECUSADO. Unicidade: end_to_end_id por PSP e uma análise por pagamento. Validade: valor positivo, score 0–100 e vocabulários controlados. Atualidade: ocorrido_em e registrado_em permitem medir atraso; reconsulta e conciliação seriam necessárias no ambiente integrado.')
P('Fluxo local executado: criar pagamento fictício pendente, confirmar no provedor simulado, reconsultar seu estado, registrar evento bruto temporário, pseudonimizar o pagador, persistir pagamento, apurar sinais, registrar decisão e notificar na tela. O protótipo também exercita oito consultas sobre dados sintéticos e a exclusão da ingestão vencida. A reconsulta à API externa do Asaas e o agendamento automático do expurgo permanecem para uma implantação posterior.')
P('LGPD: o modelo operacional usa pseudônimos por HMAC-SHA256 com segredo fora do banco; pseudonimização não equivale a anonimização. No cenário real, documento e nome podem ser dados pessoais e o payload bruto exige acesso restrito e retenção mínima. A base legal deve ser confirmada pela equipe conforme finalidade e relação entre as partes; legítimo interesse (art. 7º, IX) é hipótese a avaliar para prevenção à fraude, com teste de balanceamento e transparência. Obrigações legais de retenção precisam ser identificadas especificamente antes de definir prazo. No protótipo não há dados pessoais reais.')
P('Segurança operacional prevista: credenciais fora do repositório, TLS, papéis de menor privilégio, backup restaurável, logs de acesso, segregação entre analista e lojista e trilha de auditoria. O dado bruto expira em sete dias. Um evento de webhook não deve, sozinho, alterar o estado da entrega.')

H('6. Prova de conceito e resultados')
P('Executar npm install e npm run demo na pasta do projeto recria o esquema em PostgreSQL WebAssembly (PGlite), insere a amostra e grava evidencias/resultados.json. Foram criadas 15 tabelas, 2 lojas, 4 identidades de pagador por loja, 12 pagamentos, 12 análises, 108 sinais, 4 alertas, 2 desfechos e 1 devolução. Todos os identificadores são fictícios.')
tbl(['Consulta','Pergunta','Resultado da amostra'],[
('PN01','Vereditos por canal/faixa','8 aprovados, 2 em análise e 2 recusados; um aprovado no e-commerce.'),
('PN02','Precisão por regra','RN05, RN08 e RN09: 100% entre apenas 2 rótulos de fraude; evidência insuficiente para inferência.'),
('PN03','Latência','p50 = 115 ms; p95 = 258 ms; p99 = 275,6 ms (valores sintéticos).'),
('PN04','Exposição retida','R$ 1.500,00 em 2 pagamentos de pagador com contestação prévia; proxy, não perda evitada comprovada.'),
('PN05','Perfil horário','Dois casos rotulados FRAUDE, às 9h e 13h locais.'),
('PN06','Atraso da contestação','Uma MED simulada 75,4 dias após o pagamento.'),
('PN07','Recorrência','Pagador 2: compras 1 e 2 aprovadas; compras 3 e 4 recusadas.'),
('PN08','Fila humana','2 alertas abertos; 2 fechados com média de 35,5 min.')],[46,110,339])
P('Verificações adicionais executadas: tentativa de duplicar (psp, end_to_end_id) e tentativa de vincular um pagamento à conta de outra loja foram rejeitadas; após expurgar a ingestão vencida, o bruto caiu de 1 para 0 linha e os 12 pagamentos normalizados permaneceram. Os SQLs de PN01–PN08 estão em sql/queries/. Os resultados integrais e reproduzíveis estão no JSON de evidência.')
P('Teste funcional adicional: o laboratório local cria um pagamento pendente; a API só o grava após confirmar e reconsultar o provedor simulado. A tela separada do lojista apresenta valor recebido, decisão de entrega e motivos provenientes das regras disparadas registradas no banco. O teste automatizado verificou os três vereditos (APROVADO/LIBERADA, EM_ANALISE/RETIDA e RECUSADO/RETIDA), reenvio idempotente e persistência após reinício. As capturas do fluxo e da decisão explicada estão em evidencias/tela-confirmacao.png e evidencias/tela-lojista-retida.png. Nenhum Pix real foi movimentado.')

H('7. Limitações, crescimento e aprendizados')
P('A amostra é pequena e os rótulos foram plantados; precisão, latência e exposição não estimam produção. O sistema local tem API, front e motor de decisão sobre um provedor simulado; não implementa PSP real, notificação externa, backup nem agendamento. Para crescer 100 vezes, primeiro medir p95 e consultas em réplica; depois avaliar particionamento com chave estável, cache apenas para leitura derivada e store colunar se a análise histórica passar do limite de 30 s.')
P('Aprendizado central: a pergunta sobre banco depende do ciclo completo do dado. Confirmar recebimento, manter integridade da decisão, expurgar o bruto e preservar histórico auditável são necessidades que favorecem um núcleo relacional. Regras explicáveis facilitam revisão, mas só rótulos reais e maturados permitem afirmar eficácia antifraude.')

H('8. Fontes e declaração de IA')
P('Fontes: enunciado A3 fornecido pela disciplina; documentação PostgreSQL 16 (www.postgresql.org/docs/16/); Lei nº 13.709/2018, texto compilado (planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm). O desenho anterior do CONFIA foi usado como base de hipóteses; os resultados desta prova foram recalculados pela execução local.')
P('IA generativa apoiou estruturação do texto, modelagem SQL e código dos scripts. A execução e as verificações automáticas foram feitas localmente. O grupo deve revisar o conteúdo, confirmar as hipóteses de negócio e inserir nomes dos integrantes antes da entrega.')

story.append(PageBreak())
H('Apêndice A. Dicionário de dados físico')
P('Cada linha informa nome, tipo, descrição e regra observável no protótipo. As restrições completas constam do DDL. Campos de data/hora são armazenados com fuso quando indicado por timestamptz.')
table_desc={'lojista':'Loja contratante','usuario':'Pessoa com acesso ao sistema','conta_recebedora':'Conta Pix da loja','pagador':'Identidade pseudonimizada, limitada à loja','ingestao_webhook':'Evento bruto temporário','pagamento':'Pix recebido e normalizado','cobranca_esperada':'Valor esperado de pedido e-commerce','regra':'Definição versionada de sinal','analise_risco':'Decisão por pagamento','sinal_apurado':'Resultado de regra na análise','alerta':'Fila de revisão','desfecho':'Rótulo humano do alerta','devolucao':'Contestação ou devolução','notificacao':'Mensagem ao lojista','auditoria':'Registro de ação'}
field_desc={'id_lojista':'Identificador da loja','id_usuario':'Identificador do usuário','id_conta':'Identificador da conta','id_pagador':'Identificador do pagador','id_ingestao':'Identificador do evento bruto','id_pagamento':'Identificador do pagamento','id_cobranca':'Identificador da cobrança','id_regra':'Identificador da regra','id_analise':'Identificador da análise','id_sinal':'Identificador do sinal','id_alerta':'Identificador do alerta','id_desfecho':'Identificador do desfecho','id_devolucao':'Identificador da devolução','id_notificacao':'Identificador da notificação','id_auditoria':'Identificador da auditoria','psp':'Provedor do pagamento','end_to_end_id':'Identificador único do Pix','documento_hash':'Pseudônimo do documento','nome_hash':'Pseudônimo do nome','cnpj_hash':'Pseudônimo do CNPJ','chave_pix_hash':'Pseudônimo da chave Pix','payload':'Evento JSON bruto','score':'Pontuação de risco','veredito':'Decisão de risco','contribuicao':'Peso aplicado na decisão','ocorrido_em':'Data e hora do fato','registrado_em':'Data e hora do registro','id_entidade':'Identificador do objeto auditado'}
from collections import defaultdict
cols=defaultdict(list)
for c in data['dictionary']: cols[c['table_name']].append(c)
pk_fields={'conta_recebedora':'id_conta','ingestao_webhook':'id_ingestao','cobranca_esperada':'id_cobranca','analise_risco':'id_analise','sinal_apurado':'id_sinal'}
unique_rules={
 ('lojista','cnpj_hash'):'UNIQUE',('usuario','email'):'UNIQUE',
 ('conta_recebedora','chave_pix_hash'):'UNIQUE',
 ('pagador','documento_hash'):'UNIQUE com id_lojista',
 ('pagamento','end_to_end_id'):'UNIQUE com psp',
 ('cobranca_esperada','txid'):'UNIQUE com id_conta',
 ('regra','codigo'):'UNIQUE com versao',
 ('analise_risco','id_pagamento'):'UNIQUE',
 ('sinal_apurado','id_regra'):'UNIQUE com id_analise',
 ('alerta','id_analise'):'UNIQUE',('desfecho','id_alerta'):'UNIQUE'
}
for name in table_desc:
    H2(name+' — '+table_desc[name])
    rows=[]
    for c in cols[name]:
        f=c['column_name'];typ=c['data_type'];desc=field_desc.get(f,f.replace('_',' ').capitalize())
        if typ=='character' and c.get('character_maximum_length'): typ=f"CHAR({c['character_maximum_length']})"
        elif typ=='numeric' and c.get('numeric_precision'): typ=f"NUMERIC({c['numeric_precision']},{c['numeric_scale']})"
        elif typ=='timestamp with time zone': typ='TIMESTAMPTZ'
        elif typ=='time without time zone': typ='TIME'
        else: typ=typ.upper()
        rules=[]
        if f==pk_fields.get(name,f'id_{name}'): rules.append('PK')
        elif f.startswith('id_') and f!='id_entidade': rules.append('FK; ver DDL')
        if (name,f) in unique_rules: rules.append(unique_rules[(name,f)])
        if c['is_nullable']=='NO': rules.append('obrigatório')
        if f.endswith('_hash'): rules.append('hash; ver DDL')
        if f in ('score','valor','valor_esperado','peso','contribuicao','latencia_ms','qtd_pagamentos','qtd_contestacoes'): rules.append('CHECK de faixa/positividade')
        if f in ('veredito','situacao','canal','origem','papel','situacao_entrega','situacao_processamento','rotulo'): rules.append('CHECK de domínio')
        rows.append((f,typ,desc,'; '.join(rules) or 'opcional'))
    tbl(['Campo','Tipo','Descrição','Regra'],rows,[110,96,142,147])

out=ROOT/'output'/'pdf'/'CONFIA_relatorio_A3.pdf';out.parent.mkdir(parents=True,exist_ok=True)
def footer(canvas,doc):
    canvas.setFont('Arial',7);canvas.setFillColor(colors.HexColor('#667788'))
    canvas.drawString(50,30,'CONFIA · A3 Análise de Dados e Big Data')
    canvas.drawRightString(A4[0]-50,30,f'Página {doc.page}')
SimpleDocTemplate(str(out),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=46,bottomMargin=50,title='CONFIA — Relatório A3').build(story,onFirstPage=footer,onLaterPages=footer)
print(out)
