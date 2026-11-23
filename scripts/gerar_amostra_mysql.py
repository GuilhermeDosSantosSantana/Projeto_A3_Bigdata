"""Gera uma amostra grande, deterministica e 100% ficticia para o MySQL."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "mysql" / "03_volume_seed.sql"
RNG = random.Random(20261123)

CATEGORIES = {
    1: ("Mercearia", "#6E9F6D", ["Feijao carioca", "Macarrao espaguete", "Farinha de trigo", "Oleo de soja", "Molho de tomate", "Sal refinado", "Milho verde", "Aveia em flocos"], ["500 g", "1 kg", "2 kg", "5 kg"]),
    2: ("Frios e laticinios", "#7295BB", ["Iogurte natural", "Requeijao", "Manteiga", "Queijo prato", "Presunto fatiado", "Creme de leite", "Leite fermentado", "Queijo ralado"], ["170 g", "200 g", "500 g", "1 kg"]),
    3: ("Padaria", "#DDA46B", ["Pao de forma", "Torrada integral", "Biscoito de polvilho", "Bolo simples", "Pao de queijo", "Rosquinha", "Baguete", "Pao de leite"], ["200 g", "350 g", "500 g", "1 kg"]),
    4: ("Hortifruti", "#B2BC64", ["Maca bandeja", "Pera bandeja", "Tomate bandeja", "Cenoura bandeja", "Batata bandeja", "Alface unidade", "Uva bandeja", "Morango bandeja"], ["250 g", "500 g", "1 kg", "2 kg"]),
    5: ("Limpeza", "#A88CC5", ["Sabao liquido", "Desinfetante", "Agua sanitaria", "Limpador multiuso", "Amaciante", "Detergente", "Esponja dupla face", "Saco de lixo"], ["500 ml", "1 L", "2 L", "5 L"]),
    6: ("Bebidas", "#61A9B7", ["Agua mineral", "Suco de laranja", "Refrigerante cola", "Cha gelado", "Agua de coco", "Energetico", "Suco de uva", "Isotonico"], ["250 ml", "350 ml", "1 L", "2 L"]),
    7: ("Higiene", "#C48DB9", ["Sabonete", "Shampoo", "Condicionador", "Creme dental", "Papel higienico", "Desodorante", "Escova dental", "Lenco umedecido"], ["100 g", "200 ml", "400 ml", "1 pct"]),
    8: ("Congelados", "#8EAFC9", ["Pizza congelada", "Lasanha", "Hamburguer bovino", "Batata palito", "Legumes mistos", "Pao de alho", "Nuggets", "Sorvete"], ["300 g", "500 g", "1 kg", "2 kg"]),
    9: ("Pet", "#B99F80", ["Racao canina", "Racao felina", "Biscoito canino", "Areia sanitaria", "Sache felino", "Petisco canino", "Brinquedo pet", "Tapete higienico"], ["100 g", "500 g", "1 kg", "3 kg"]),
    10: ("Papelaria", "#9B9DC9", ["Caderno", "Caneta azul", "Lapis grafite", "Borracha", "Papel sulfite", "Marcador", "Cola branca", "Envelope"], ["1 un", "4 un", "10 un", "20 un"]),
    11: ("Utilidades", "#B6A687", ["Pote plastico", "Copo descartavel", "Prato descartavel", "Papel aluminio", "Filme plastico", "Vela", "Pilha alcalina", "Guardanapo"], ["1 un", "10 un", "50 un", "100 un"]),
    12: ("Snacks", "#D1A265", ["Batata chips", "Amendoim", "Barra de cereal", "Biscoito salgado", "Chocolate", "Pipoca pronta", "Mix de castanhas", "Wafer"], ["50 g", "100 g", "200 g", "500 g"]),
}
BRANDS = ["Bom Dia", "Vale Verde", "Casa Boa", "Sol Nascente", "Sabor Mais", "Ponto Certo"]


def quote(value: str) -> str:
    if not value.isascii() or "'" in value:
        raise ValueError(f"Texto invalido para amostra sem acentos: {value!r}")
    return f"'{value}'"


def write_insert(stream, table: str, columns: str, rows, size: int = 1000) -> None:
    chunk = []
    for row in rows:
        chunk.append(row)
        if len(chunk) >= size:
            stream.write(f"INSERT INTO {table}({columns}) VALUES\n " + ",\n ".join(chunk) + ";\n")
            chunk.clear()
    if chunk:
        stream.write(f"INSERT INTO {table}({columns}) VALUES\n " + ",\n ".join(chunk) + ";\n")


def main() -> None:
    """Escreve SQL em streaming: memoria limitada ao catalogo de 2 mil produtos."""
    product_count = 2000
    customer_count = 500000
    sale_count = 750000
    loss_count = 5000
    stream = OUTPUT.open("w", encoding="ascii", newline="\n")
    stream.write(f"-- Amostra sintetica: {product_count} produtos, {customer_count} clientes, {sale_count} vendas.\n")
    stream.write("-- Reexecutar apenas em banco novo, apos 01_schema.sql e 02_seed.sql.\n")
    stream.write("USE giro_a3;\nSTART TRANSACTION;\n")
    categories = [f"({cid},{quote(name)},{quote(color)})"
                  for cid, (name, color, _, _) in CATEGORIES.items() if cid >= 6]
    write_insert(stream, "category", "id,name,color", categories)
    suppliers = [f"({sid},{quote(f'Fornecedor Demo {sid:03d}')})" for sid in range(5, 41)]
    write_insert(stream, "supplier", "id,name", suppliers)
    customers = (f"({cid},{quote(f'CLI-{cid:06d}')},{quote(f'Cliente Ficticio {cid:06d}')})"
                 for cid in range(9, customer_count + 1))
    write_insert(stream, "customer", "id,code,name", customers)

    products = []
    batches = []
    category_sequence = Counter()
    prices = {}
    for pid in range(9, 2001):
        cid = 1 + (pid - 9) % len(CATEGORIES)
        category_sequence[cid] += 1
        variant = category_sequence[cid] - 1
        _, _, families, sizes = CATEGORIES[cid]
        family = families[variant % len(families)]
        size = sizes[(variant // len(families)) % len(sizes)]
        brand = BRANDS[(variant // (len(families) * len(sizes))) % len(BRANDS)]
        name = f"{family} {size} {brand}"
        sku = f"GIR-{pid:04d}"
        supplier = 5 + (pid % 36)
        unit = "un" if cid in (2, 4, 8, 10, 11) else "pct"
        min_stock = RNG.randint(8, 25)
        lead_days = RNG.randint(1, 14)
        price = RNG.randint(399, 5999)
        cost = round(price * RNG.uniform(0.48, 0.76))
        prices[pid] = price
        products.append(f"({pid},{quote(sku)},{quote(name)},{cid},{supplier},{quote(unit)},"
                        f"{min_stock},{lead_days},{price})")
        qty = RNG.randint(2500, 5000)
        expiry = "NULL" if cid in (5, 7, 10, 11) else f"UTC_DATE() + INTERVAL {RNG.randint(1, 180)} DAY"
        batches.append(f"({pid},{pid},{qty},{cost},{expiry},{quote(f'DEMO-LOTE-{pid:04d}')},"
                       f"UTC_TIMESTAMP() - INTERVAL {RNG.randint(1, 28)} DAY)")
    write_insert(stream, "product", "id,sku,name,category_id,supplier_id,unit,min_stock,lead_days,sale_price_cents", products)

    extra_batch_id = 2001
    for pid in range(9, 2001, 4):
        cost = round(prices[pid] * 0.62)
        cid = 1 + (pid - 9) % len(CATEGORIES)
        expiry = "NULL" if cid in (5, 7, 10, 11) else f"UTC_DATE() + INTERVAL {RNG.randint(20, 180)} DAY"
        batches.append(f"({extra_batch_id},{pid},{RNG.randint(40, 90)},{cost},{expiry},"
                       f"{quote(f'DEMO-EXTRA-{pid:04d}')},UTC_TIMESTAMP() - INTERVAL 2 DAY)")
        extra_batch_id += 1
    write_insert(stream, "batch", "id,product_id,quantity_received,unit_cost_cents,expires_on,source_ref,received_at", batches)

    def sale_details():
        rng = random.Random(20261124)
        for sale_id in range(9, sale_count + 1):
            yield (sale_id, rng.randint(9, product_count), rng.randint(1, customer_count),
                   rng.randint(1, 4), rng.randint(0, 89))

    sale_rows = (f"({sid},{pid},{cid},{qty},{prices[pid]},UTC_TIMESTAMP() - INTERVAL {days} DAY)"
                 for sid, pid, cid, qty, days in sale_details())
    write_insert(stream, "sale", "id,product_id,customer_id,quantity,unit_price_cents,sold_at", sale_rows)

    event_rows = (f"({sid + 2},{pid},'SALE',{qty},{sid},NULL,UTC_TIMESTAMP() - INTERVAL {days} DAY)"
                  for sid, pid, _cid, qty, days in sale_details())
    write_insert(stream, "stock_event", "id,batch_id,kind,quantity,sale_id,reason,occurred_at", event_rows)

    loss_rng = random.Random(20261125)
    loss_rows = []
    for event_id in range(sale_count + 3, sale_count + 3 + loss_count):
        pid = loss_rng.randint(9, product_count)
        qty = loss_rng.randint(1, 3)
        reason = loss_rng.choice(["Avaria no transporte", "Embalagem danificada", "Quebra no armazenamento"])
        days = loss_rng.randint(0, 30)
        loss_rows.append(f"({event_id},{pid},'LOSS',{qty},NULL,{quote(reason)},"
                         f"UTC_TIMESTAMP() - INTERVAL {days} DAY)")
    write_insert(stream, "stock_event", "id,batch_id,kind,quantity,sale_id,reason,occurred_at", loss_rows)
    stream.write("COMMIT;\n")
    stream.close()
    print(f"Gerado: {OUTPUT} ({product_count} produtos, {customer_count} clientes, {sale_count} vendas)")


if __name__ == "__main__":
    main()
