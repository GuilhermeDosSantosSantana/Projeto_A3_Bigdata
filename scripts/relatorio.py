"""Gera o relatório PDF da A3 a partir do banco e das evidências executadas."""

from __future__ import annotations

import csv
import json
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = json.loads((ROOT / "evidencias" / "mysql_resultados_consultas.json").read_text(encoding="utf-8"))
OUTPUT = ROOT / "output" / "pdf" / "GIRO_relatorio_A3.pdf"

FONT_DIR = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Arial", str(FONT_DIR / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Bold", str(FONT_DIR / "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Georgia", str(FONT_DIR / "georgia.ttf")))

INK = colors.HexColor("#193B30")
GREEN = colors.HexColor("#2A644B")
PALE = colors.HexColor("#EAF2E7")
MUTED = colors.HexColor("#617469")
LINE = colors.HexColor("#DCE7DB")
CREAM = colors.HexColor("#F7F8F4")
ORANGE = colors.HexColor("#D88953")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleCustom", fontName="Georgia", fontSize=29, leading=34, textColor=INK, spaceAfter=12))
styles.add(ParagraphStyle(name="SubtitleCustom", fontName="Arial", fontSize=11, leading=16, textColor=MUTED, spaceAfter=13))
styles.add(ParagraphStyle(name="SectionCustom", fontName="Georgia", fontSize=18, leading=22, textColor=INK, spaceBefore=4, spaceAfter=10, keepWithNext=True))
styles.add(ParagraphStyle(name="SubCustom", fontName="Arial-Bold", fontSize=10, leading=14, textColor=GREEN, spaceBefore=9, spaceAfter=5, keepWithNext=True))
styles.add(ParagraphStyle(name="BodyCustom", fontName="Arial", fontSize=9, leading=13.5, textColor=INK, spaceAfter=8))
styles.add(ParagraphStyle(name="SmallCustom", fontName="Arial", fontSize=7.7, leading=10.8, textColor=INK, spaceAfter=4))
styles.add(ParagraphStyle(name="TinyCustom", fontName="Arial", fontSize=6.7, leading=8.8, textColor=INK))
styles.add(ParagraphStyle(name="LabelCustom", fontName="Arial-Bold", fontSize=7, leading=10, textColor=GREEN, spaceAfter=4))
styles.add(ParagraphStyle(name="CenterCustom", parent=styles["BodyCustom"], alignment=TA_CENTER))


def P(text, style="BodyCustom"):
    return Paragraph(text, styles[style])


def heading(title):
    return P(title, "SectionCustom")


def sub(title):
    return P(title, "SubCustom")


def table(headers, rows, widths, font_size=7.2, first_color=PALE):
    data = [[P(str(h), "LabelCustom") for h in headers]]
    for row in rows:
        data.append([P(str(value).replace("&", "&amp;"), "TinyCustom") for value in row])
    item = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    item.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), first_color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, LINE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CREAM]),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return item


class ModelDiagram(Flowable):
    width = 510
    height = 265

    def __init__(self):
        super().__init__()
        self.width = 510
        self.height = 265

    def draw(self):
        c = self.canv
        boxes = {
            "Categoria": (5, 205), "Produto": (195, 205), "Lote": (385, 205),
            "Fornecedor": (5, 115), "Cliente": (5, 25),
            "Venda": (195, 25), "Evento": (385, 25),
        }
        edges = [
            ((125, 226), (195, 226), "1:N"),
            ((125, 136), (195, 206), "1:N"),
            ((315, 226), (385, 226), "1:N"),
            ((255, 205), (255, 67), "1:N"),
            ((445, 205), (445, 67), "1:N"),
            ((125, 46), (195, 46), "1:N"),
            ((315, 46), (385, 46), "1:N"),
        ]
        c.setStrokeColor(colors.HexColor("#93B69A"))
        c.setLineWidth(1.2)
        for a, b, label in edges:
            c.line(*a, *b)
            c.setFillColor(GREEN)
            c.setFont("Arial-Bold", 6)
            c.drawCentredString((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 4, label)
        for title, (x, y) in boxes.items():
            c.setFillColor(PALE)
            c.setStrokeColor(LINE)
            c.roundRect(x, y, 120, 42, 8, stroke=1, fill=1)
            c.setFillColor(INK)
            c.setFont("Arial-Bold", 10)
            c.drawCentredString(x + 60, y + 17, title)


def brl(cents):
    return "R$ " + f"{int(cents) / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def number(value):
    return f"{int(value):,}".replace(",", ".")


def page_frame(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(GREEN)
    canvas.rect(0, h - 11 * mm, w, 11 * mm, fill=1, stroke=0)
    canvas.setFont("Arial-Bold", 7)
    canvas.setFillColor(colors.white)
    canvas.drawString(18 * mm, h - 7.2 * mm, "GIRO  /  A3 - ANÁLISE DE DADOS E BIG DATA")
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 16 * mm, w - 18 * mm, 16 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Arial", 7)
    canvas.drawString(18 * mm, 11 * mm, "Amostra fictícia em MySQL 8.4  •  25/11/2026")
    canvas.drawRightString(w - 18 * mm, 11 * mm, f"Página {doc.page}")
    canvas.restoreState()


story = []

# Capa e visão da startup
story += [Spacer(1, 18 * mm), P("GIRO", "LabelCustom"), P("Estoque confiável.<br/>Decisões no tempo certo.", "TitleCustom"),
          P("Projeto Startup de Dados  |  Avaliação A3  |  Análise de Dados e Big Data", "SubtitleCustom"),
          Spacer(1, 7 * mm),
          table(["Integrantes", "Turma", "Data da evidência"], [["Preencher pelo grupo", "Preencher", "25/11/2026"]], [220, 90, 200]),
          Spacer(1, 12 * mm), heading("4.1  Problema e visão"),
          P("Varejistas com grande volume de transações perdem vendas por ruptura de estoque e descartam produtos vencidos. O GIRO registra produtos, clientes, entradas por lote, vendas e perdas. O histórico permite alertas de reposição e validade e análises de vendas por cliente."),
          P("<b>Público-alvo:</b> gestor de estoque de uma operação varejista centralizada. <b>Proposta de valor:</b> saber o que repor, o que vender antes do vencimento e quanto capital está imobilizado. A amostra é sintética e todos os clientes são fictícios."),
          sub("Perguntas e indicadores"),
          table(["Pergunta de negócio", "Indicador"], [
              ["O que deve ser reposto?", "Saldo vs. ponto de reposição"],
              ["O que vence nos próximos 7 dias?", "Lotes e unidades disponíveis"],
              ["Quanto vendemos por dia?", "Receita diária em centavos"],
              ["Onde está o capital em estoque?", "Valor a custo por categoria"],
              ["Qual produto tem menor cobertura?", "Dias de cobertura pela média de vendas"],
              ["Onde há perdas?", "Quantidade e custo por motivo"],
              ["Quais clientes mais compraram?", "Compras e receita por cliente fictício"],
          ], [250, 260])]
story.append(PageBreak())

# Diagnóstico e decisão
story += [heading("4.2  Diagnóstico dos dados"),
          P("<b>Fontes:</b> cadastro de produtos, categorias, fornecedores e clientes fictícios; recebimentos por lote, vendas e perdas. Os dados são estruturados e gerados localmente por script com semente fixa. Não há nome real, telefone, e-mail, endereço pessoal, imagem ou API externa."),
          table(["V", "Aplicação ao GIRO"], [
              ["Volume", f"Amostra executada: {number(EVIDENCE['table_counts']['product'])} produtos, {number(EVIDENCE['table_counts']['customer'])} clientes, {number(EVIDENCE['table_counts']['batch'])} lotes, {number(EVIDENCE['table_counts']['sale'])} vendas e {number(EVIDENCE['table_counts']['stock_event'])} eventos."],
              ["Velocidade", "Escritas curtas a cada entrada, venda ou perda; leitura frequente do saldo."],
              ["Variedade", "Cadastros, clientes fictícios, lotes, vendas e eventos de baixa."],
              ["Veracidade", "SKU e referência únicos, FKs, CHECK, gatilhos, transações e conciliação."],
              ["Valor", "Alertas de ruptura, vencimento, cobertura e capital em estoque."],
          ], [85, 425]),
          P("A carga foi criada para a prova de conceito e cobre vendas distribuídas em 90 dias; não representa demanda real. O acesso esperado combina escritas curtas de operação e consultas agregadas. A escala 100x seria cerca de 75 milhões de vendas e exige avaliação de capacidade específica."),
          heading("4.3  Escolha do banco - Eixo 1"),
          P("<b>Escolha para a entrega de dados:</b> MySQL 8.4 com InnoDB, relacional e transacional. Produto, lote, cliente, venda e baixa exigem chaves, junções e regras de integridade. A aplicação atual lê e grava no MySQL; a venda e as baixas dos lotes são gravadas juntas em transação. MySQL oferece múltiplas conexões, usuários com permissões distintas e ferramentas de inspeção para uma operação centralizada."),
          table(["Critério", "MySQL 8.4", "SQLite", "PostgreSQL", "Documentos"], [
              ["Integridade", "ACID, FK, CHECK, gatilho", "ACID, FK, CHECK", "ACID, FK, CHECK", "Relações exigem desenho extra"],
              ["Concorrência", "Vários clientes", "Um escritor por arquivo", "Vários clientes / MVCC", "Depende do produto"],
              ["Operação", "Servidor e backup", "Arquivo simples", "Servidor e backup", "Servidor e gestão"],
              ["Decisão", "Escolhido para a A3", "Etapa local anterior", "Alternativa forte", "Não escolhido"],
          ], [80, 115, 100, 110, 105]),
          P("SQLite foi a opção mais simples para a primeira tela local, mas limitava a defesa de acesso multiusuário e perfis. PostgreSQL também atenderia bem e é uma alternativa técnica séria; não há benchmark aqui que prove superioridade de MySQL. Banco de documentos não simplifica as relações e invariantes desta base. <b>Redis</b> acelera leituras do painel e catálogo como cache descartável; quando indisponível, um cache temporário em memória evita repetir a consulta pesada a cada leitura. O MySQL continua a fonte definitiva. <b>CAP:</b> o MySQL instalado é uma instância única, sem distribuição; CAP só entra no projeto se houver replicação ou sincronização entre lojas."),
          P("Referências: dev.mysql.com/doc/refman/8.4/en/innodb-introduction.html; sqlite.org/whentouse.html; postgresql.org/docs/17/mvcc-intro.html.", "SmallCustom")]
story.append(PageBreak())

# Modelagem
story += [heading("4.4  Organização e modelagem - Eixo 2"),
          P("<b>Modelo conceitual:</b> categoria e fornecedor classificam produtos; produto recebe lotes e aparece em vendas; cliente fictício pode estar associado a várias vendas; uma venda consome um ou mais lotes por eventos; eventos também registram perdas. O escopo é um centro de estoque; filiais ainda não são modeladas."),
          ModelDiagram(), Spacer(1, 6 * mm),
          sub("Modelo lógico"),
          P("category(id PK, name UQ, color); supplier(id PK, name UQ); customer(id PK, code UQ, name); product(id PK, sku UQ, category_id FK, supplier_id FK, name, unit, min_stock, lead_days, sale_price_cents, active); batch(id PK, product_id FK, quantity_received, unit_cost_cents, expires_on, source_ref UQ, received_at); sale(id PK, product_id FK, customer_id FK opcional, quantity, unit_price_cents, sold_at); stock_event(id PK, batch_id FK, sale_id FK opcional, kind, quantity, reason, occurred_at)."),
          sub("Modelo físico e normalização"),
          P("IDs são BIGINT, quantidades e centavos são INT, validade é DATE e instantes são DATETIME em UTC. Valores monetários inteiros evitam arredondamento de ponto flutuante. FKs impedem órfãos; SKU, código de cliente e referência de entrada são únicos. A separação de cadastros, lotes, vendas e eventos evita duplicar saldos. <b>batch_balance</b> e <b>product_balance</b> calculam saldo derivado. Preço e custo históricos são snapshots intencionais, pois podem mudar."),
          P("Índices: batch(product_id, expires_on) apoia validade; stock_event(batch_id) apoia saldo; sale(product_id, sold_at) apoia giro; sale(customer_id, sold_at) apoia compras por cliente; stock_event(occurred_at) apoia auditoria. Índices únicos cobrem as chaves naturais. No crescimento 100x, mediremos consultas antes de criar agregados ou particionar."),
          sub("Dicionário de dados"),
          P(f"O dicionário completo nas páginas seguintes lista os {EVIDENCE['documented_fields']} campos, confrontados com information_schema.COLUMNS. O esquema executável está em mysql/01_schema.sql.")]
story.append(PageBreak())

# Dicionário, dividido por tabela
with (ROOT / "docs" / "dicionario_de_dados_mysql.csv").open(encoding="utf-8", newline="") as stream:
    dictionary = list(csv.DictReader(stream, delimiter=";"))
for idx, group in enumerate((("category", "supplier", "customer", "product"), ("batch", "sale", "stock_event"))):
    story.append(heading("4.4  Dicionário de dados" + (" (continuação)" if idx else "")))
    for table_name in group:
        story.append(sub(table_name))
        rows = [r for r in dictionary if r["tabela"] == table_name]
        story.append(table(["Campo", "Tipo", "Descrição", "Regra"],
                           [[r["campo"], r["tipo_mysql"], r["descricao"], r["regra"]] for r in rows],
                           [95, 90, 185, 140]))
        story.append(Spacer(1, 5 * mm))
    story.append(PageBreak())

# Governança
story += [heading("4.5  Qualidade e governança"),
          table(["Dimensão", "Regra implementada ou verificação"], [
              ["Completude", "Campos obrigatórios NOT NULL; motivo obrigatório para perda."],
              ["Unicidade", "SKU, código de cliente e referência de entrada únicos."],
              ["Validade", "Quantidade positiva; unidade enumerada; prazo do fornecedor de 1 a 90 dias; validade ISO."],
              ["Consistência", "FKs e CHECK; gatilho com trava do lote impede saldo negativo."],
              ["Atualidade", "Saldo calculado das movimentações; lotes vencidos excluídos do saldo vendável."],
          ], [100, 410]),
          sub("Ingestão e tratamento de dados sujos"),
          P("Fluxo da prova de conceito: gerador determinístico → SQL de carga em transação → validações MySQL (FK, UNIQUE, CHECK e gatilho) → tabelas normalizadas → visões de saldo → oito consultas. Uma entrada duplicada é recusada por chave única. O teste de baixa acima do saldo foi rejeitado pelo gatilho sem alterar o lote. A consulta de qualidade detecta lote negativo, venda divergente e vínculo incoerente entre venda e lote. Lotes vencidos ainda com saldo são tratados como alerta operacional, não como erro de integridade."),
          sub("LGPD, acesso e backup"),
          P("Os 500 mil clientes usam códigos e nomes artificiais, sem identificação de pessoa real. Se a solução coletar dados reais, deve definir finalidade, base legal, minimização, prazo de retenção e direitos dos titulares; execução de contrato é hipótese a avaliar conforme o fluxo (LGPD, art. 7º, V). O servidor MySQL escuta apenas em 127.0.0.1; giro_demo tem leitura e giro_app tem escrita restrita ao esquema da aplicação. As senhas locais ficam fora do Git. Foi gerado um dump SQL e testada a restauração em esquema separado com as mesmas contagens. Em produção, seriam necessários backup automático externo, teste periódico de restauração, controle de acesso por função e monitoramento."),
          P("Referência legal: Lei 13.709/2018, texto compilado em planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm.", "SmallCustom")]
story.append(PageBreak())

# Evidências, parte 1
q = EVIDENCE["queries"]
story += [heading("4.6  Prova de conceito - consultas"),
          P(f"Banco MySQL real: esquema giro_a3, versão {EVIDENCE['mysql_version']}. Amostra fictícia: {number(EVIDENCE['table_counts']['product'])} produtos, {number(EVIDENCE['table_counts']['customer'])} clientes, {number(EVIDENCE['table_counts']['batch'])} lotes, {number(EVIDENCE['table_counts']['sale'])} vendas e {number(EVIDENCE['table_counts']['stock_event'])} eventos. Os resultados integrais estão em evidencias/mysql_resultados_consultas.json."),
          sub("PN01 - Produtos a repor"),
          table(["SKU", "Produto", "Saldo", "Ponto"],
                [[r["sku"], r["name"], r["stock"], r["reorder_point"]] for r in q["01_reposicao"]],
                [80, 300, 65, 65]),
          P("O Pao integral tem 10 unidades frente ao ponto de 15. Fonte: mysql/consultas/01_reposicao.sql.", "SmallCustom"),
          sub("PN02 - Lotes próximos da validade"),
          table(["SKU", "Produto", "Lote", "Saldo", "Validade"],
                [[r["sku"], r["name"], r["batch_id"], r["available_quantity"], r["expires_on"]] for r in q["02_validade"][:8]],
                [75, 240, 45, 55, 95]),
          P(f"Mostrados 8 de {len(q['02_validade'])} lotes próximos da validade; o arquivo JSON guarda todos os resultados.", "SmallCustom"),
          sub("PN03 - Receita por dia"),
          table(["Dia", "Vendas", "Receita"],
                [[r["day"], r["sales"], brl(r["revenue_cents"])] for r in q["03_vendas_diarias"]],
                [150, 100, 260])]
story.append(PageBreak())

# Evidências, parte 2
story += [heading("4.6  Consultas e validação (continuação)"),
          sub("PN04 - Capital por categoria"),
          table(["Categoria", "Produtos", "Valor a custo"],
                [[r["category"], r["products"], brl(r["value_cents"])] for r in q["04_valor_categoria"][:6]],
                [245, 95, 170]),
          P(f"Mostradas 6 de {len(q['04_valor_categoria'])} categorias.", "SmallCustom"),
          sub("PN05 - Menor cobertura"),
          table(["Produto", "Saldo", "Média diária", "Cobertura"],
                [[r["name"], r["stock"], r["daily_average"], f"{r['coverage_days']} dias"] for r in q["05_giro_produto"][:8]],
                [255, 60, 90, 105]),
          P(f"Mostrados 8 de {len(q['05_giro_produto'])} produtos com histórico de venda recente.", "SmallCustom"),
          sub("PN06 - Perdas registradas"),
          table(["Produto", "Motivo", "Qtd.", "Custo"],
                [[r["name"], r["reason"], r["lost_quantity"], brl(r["lost_cost_cents"])] for r in q["06_perdas"][:6]],
                [205, 155, 50, 100]),
          P(f"Mostradas 6 de {len(q['06_perdas'])} combinações de produto e motivo.", "SmallCustom")]
story.append(PageBreak())
story += [heading("4.6  Clientes e validação"),
          sub("PN07 - Clientes fictícios por receita"),
          table(["Código", "Cliente", "Compras", "Receita"],
                [[r["code"], r["name"], r["purchases"], brl(r["revenue_cents"])] for r in q["08_clientes"][:5]],
                [80, 210, 80, 140]),
          sub("Verificações executadas"),
          table(["Verificação", "Resultado"], [
              ["Consulta de qualidade", f"{EVIDENCE['quality_issues']} problemas"],
              ["Teste de saldo negativo", EVIDENCE["negative_stock_trigger"]],
              ["Perda sem motivo", EVIDENCE["loss_reason_check"]],
              ["Cliente inexistente", EVIDENCE["customer_fk_check"]],
              ["Backup MySQL", EVIDENCE["restore_test"]],
              ["Dicionário vs. esquema", f"{EVIDENCE['documented_fields']} campos conferidos"],
              ["Nomes sem acentos", "Conferidos em 4 tabelas de cadastro"],
          ], [255, 255])]
story.append(PageBreak())

# Limites, roteiro e fontes
story += [heading("4.7  Limitações e próximos passos"),
          P("A base cobre itens embalados em quantidades inteiras de um centro de estoque. O cliente é fictício e opcional na venda; não há cadastro real, autenticação de operadores, integração com caixa ou pedido automático ao fornecedor. O gerador cria volume para a apresentação, mas não demonstra desempenho em produção nem redução real de perdas. A regra de reposição usa média de sete dias, prazo de entrega mais dois dias e piso mínimo; não modela promoção nem sazonalidade."),
          P("Em 100x do volume testado, seriam cerca de 75 milhões de vendas e baixas correspondentes. Seria preciso medir concorrência e latência, avaliar particionamento por data, agregados, replicação e políticas de arquivamento. Para vários centros, acrescentar store_id, isolamento e perfis por unidade, além de automatizar backup e recuperação. Operação offline exigiria sincronização, ainda não implementada."),
          sub("Aprendizado técnico para o grupo revisar"),
          P("Um alerta confiável depende primeiro de uma definição precisa de saldo. Lote, venda e baixa precisam estar ligados por chaves, restrições e transações. A escolha de MySQL prioriza controle relacional, multiusuário e inspeção da base. O custo de operar o servidor é uma troca consciente."),
          sub("Defesa oral sugerida"),
          P("'Escolhemos MySQL porque estoque depende de relações entre produto, lote, venda, cliente e baixa, com integridade referencial e transações. Carregamos mais de 2 mil produtos, 500 mil clientes fictícios e 750 mil vendas. Sete consultas respondem perguntas de negócio; a oitava confere a qualidade. Testamos o gatilho de saldo, a restauração do dump e os fluxos do site. O Redis guarda só cache. A arquitetura ainda tem um centro de estoque; múltiplos centros exigiriam identificador e isolamento.'"),
          sub("Uso de IA e revisão"),
          P("Ferramentas de IA auxiliaram a redação, o código SQL/Python e a preparação do relatório. Antes da entrega, o grupo deve registrar nomes dos integrantes, turma, duração do pitch e o que cada integrante revisou. Os resultados do banco foram gerados por scripts locais e são reproduzíveis; não são dados reais de clientes."),
          sub("Arquivos entregues e referências"),
          P("mysql/01_schema.sql; mysql/02_seed.sql; mysql/03_volume_seed.sql; mysql/04_trigger.sql; mysql/consultas/01-08; docs/dicionario_de_dados_mysql.csv; entrega/GIRO_mysql_A3.sql; evidencias/mysql_resultados_consultas.json; scripts/gerar_amostra_mysql.py; scripts/validar_mysql.py."),
          P("Enunciado: A3 - Projeto Startup de Dados, disciplina Análise de Dados e Big Data. MySQL InnoDB: https://dev.mysql.com/doc/refman/8.4/en/innodb-introduction.html. SQLite: https://www.sqlite.org/whentouse.html. PostgreSQL: https://www.postgresql.org/docs/17/mvcc-intro.html. LGPD: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm.", "SmallCustom")]


def screenshot(name):
    path = ROOT / "evidencias" / name
    with PILImage.open(path) as source:
        preview = source.crop((0, 0, source.width, min(source.height, 900)))
        stream = BytesIO()
        preview.save(stream, format="PNG")
    stream.seek(0)
    flowable = Image(stream, width=400, height=400 * preview.height / preview.width)
    flowable.hAlign = "CENTER"
    return flowable


story += [PageBreak(), heading("Apêndice — fluxos na aplicação"),
          P("Capturas reais da interface local conectada ao MySQL. O roteiro completo para demonstrar cada ação está em docs/GUIA_DE_USO_PITCH.md; os scripts de validação estão em scripts/testar_front.py e scripts/testar_fluxo_web.py."),
          sub("1. Visão geral, indicadores e prioridades"), screenshot("giro_visao_geral.png"),
          Spacer(1, 3 * mm), sub("2. Catálogo com busca e paginação"), screenshot("giro_produtos.png"),
          PageBreak(), heading("Apêndice — operação comprovada"),
          P("O teste de navegador cadastra produto sem informar ID, edita o cadastro, registra entrada, recusa venda acima do saldo, vende com cliente, registra perda e confere o saldo final e o histórico."),
          sub("3. Venda com prévia de valor e seleção de cliente"), screenshot("giro_registro_venda.png"),
          Spacer(1, 3 * mm), sub("4. Perda com motivo obrigatório"), screenshot("giro_registro_perda.png")]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                        topMargin=20 * mm, bottomMargin=20 * mm,
                        title="GIRO - Relatório A3", author="Grupo GIRO")
doc.build(story, onFirstPage=page_frame, onLaterPages=page_frame)
print(OUTPUT)
