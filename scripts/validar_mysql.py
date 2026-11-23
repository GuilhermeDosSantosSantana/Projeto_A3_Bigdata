"""Valida o MySQL instalado, as consultas, o dicionario e o dump."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
BIN = Path(r"C:\Program Files\MySQL\MySQL Server 8.4\bin")
OPTIONS = ROOT / "mysql" / "runtime" / "root.cnf"
SCHEMA = "giro_a3"
RESTORE_SCHEMA = "giro_a3_restore_check"


def run_cli(sql: str, *, schema: str | None = None, expect_error: str | None = None) -> str:
    args = [str(BIN / "mysql.exe"), f"--defaults-extra-file={OPTIONS}",
            "--default-character-set=utf8mb4", "--batch", "--raw"]
    if schema:
        args.append(f"--database={schema}")
    args += ["--execute", sql]
    result = subprocess.run(args, capture_output=True, encoding="utf-8", errors="replace")
    if expect_error:
        if result.returncode == 0 or expect_error not in result.stderr:
            raise RuntimeError(f"Erro esperado ausente: {expect_error}; {result.stderr}")
        return result.stderr
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout


def query_rows(sql: str, *, schema: str | None = SCHEMA) -> list[dict[str, str | None]]:
    output = run_cli(sql, schema=schema).strip()
    if not output:
        return []
    lines = output.splitlines()
    headers = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        values = line.split("\t")
        if len(values) != len(headers):
            raise RuntimeError(f"Colunas divergentes: {line!r}")
        rows.append(dict(zip(headers, (None if v == "NULL" else v for v in values))))
    return rows


def main() -> None:
    if not OPTIONS.exists():
        raise RuntimeError("MySQL local não configurado: mysql/runtime/root.cnf ausente")
    version = query_rows("SELECT VERSION() AS version", schema=None)[0]["version"]
    queries = {}
    for path in sorted((ROOT / "mysql" / "consultas").glob("*.sql")):
        rows = query_rows(path.read_text(encoding="utf-8"))
        queries[path.stem] = rows

    counts = {name: int(query_rows(f"SELECT COUNT(*) AS n FROM {name}")[0]["n"])
              for name in ("category", "supplier", "customer", "product", "batch", "sale", "stock_event")}
    expected_counts = {"category": 12, "supplier": 40, "customer": 500000, "product": 2000,
                       "batch": 2498, "sale": 750000, "stock_event": 755002}
    if counts != expected_counts or queries["07_qualidade"]:
        raise RuntimeError(f"Contagens ou qualidade divergentes: {counts}")

    non_ascii = []
    for table in ("category", "supplier", "customer", "product"):
        bad = int(query_rows(f"SELECT COUNT(*) AS n FROM {table} "
                             "WHERE CHAR_LENGTH(name) <> LENGTH(name)")[0]["n"])
        if bad:
            non_ascii.append((table, bad))
    if non_ascii:
        raise RuntimeError(f"Acentos encontrados na amostra: {non_ascii[:3]}")

    fields = query_rows("""
      SELECT TABLE_NAME AS tabela, COLUMN_NAME AS campo, COLUMN_TYPE AS tipo,
             IS_NULLABLE AS permite_nulo, COLUMN_KEY AS chave
      FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = 'giro_a3' AND TABLE_NAME IN
            ('category','supplier','customer','product','batch','sale','stock_event')
      ORDER BY TABLE_NAME, ORDINAL_POSITION
    """, schema=None)
    with (ROOT / "docs" / "dicionario_de_dados.csv").open(encoding="utf-8", newline="") as f:
        original = {(r["tabela"], r["campo"]): r for r in csv.DictReader(f, delimiter=";")}
    original.update({
        ("customer", "id"): {"descricao": "Identificador do cliente ficticio", "regra": "PK"},
        ("customer", "code"): {"descricao": "Codigo ficticio do cliente", "regra": "Obrigatorio e unico"},
        ("customer", "name"): {"descricao": "Nome de demonstracao sem dado pessoal", "regra": "Obrigatorio e 3 a 80 caracteres"},
        ("sale", "customer_id"): {"descricao": "Cliente ficticio da venda", "regra": "FK customer.id opcional para venda anonima"},
    })
    if {(r["tabela"], r["campo"]) for r in fields} != set(original):
        raise RuntimeError("Dicionário e esquema MySQL divergem")
    dictionary_path = ROOT / "docs" / "dicionario_de_dados_mysql.csv"
    with dictionary_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["tabela", "campo", "tipo_mysql", "permite_nulo", "chave", "descricao", "regra"], delimiter=";")
        writer.writeheader()
        for field in fields:
            original_row = original[(field["tabela"], field["campo"])]
            writer.writerow({"tabela": field["tabela"], "campo": field["campo"],
                             "tipo_mysql": field["tipo"], "permite_nulo": field["permite_nulo"],
                             "chave": field["chave"], "descricao": original_row["descricao"],
                             "regra": original_row["regra"]})

    before = query_rows("SELECT available_quantity FROM batch_balance WHERE id=4")[0]
    error = run_cli("INSERT INTO stock_event(id,batch_id,kind,quantity,reason) "
                    "VALUES(999999,4,'LOSS',999,'Teste de excesso')", schema=SCHEMA,
                    expect_error="batch stock cannot be negative")
    after = query_rows("SELECT available_quantity FROM batch_balance WHERE id=4")[0]
    if before != after:
        raise RuntimeError("Gatilho de saldo falhou")
    reason_error = run_cli("INSERT INTO stock_event(id,batch_id,kind,quantity,reason) "
                           "VALUES(999998,4,'LOSS',1,NULL)", schema=SCHEMA,
                           expect_error="ck_event_shape")
    fk_error = run_cli("INSERT INTO sale(id,product_id,customer_id,quantity,unit_price_cents) "
                       "VALUES(9999999,1,9999999,1,100)", schema=SCHEMA,
                       expect_error="foreign key constraint fails")

    dump = ROOT / "entrega" / "GIRO_mysql_A3.sql"
    dump.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([str(BIN / "mysqldump.exe"), f"--defaults-extra-file={OPTIONS}",
                             "--default-character-set=utf8mb4", "--single-transaction",
                             "--triggers", "--set-gtid-purged=OFF", f"--result-file={dump}", SCHEMA],
                            capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode or dump.stat().st_size < 1000:
        raise RuntimeError(f"Dump MySQL falhou: {result.stderr}")
    run_cli(f"CREATE DATABASE IF NOT EXISTS {RESTORE_SCHEMA} CHARACTER SET utf8mb4")
    try:
        run_cli("source " + dump.as_posix(), schema=RESTORE_SCHEMA)
        restored = {name: int(query_rows(f"SELECT COUNT(*) AS n FROM {name}", schema=RESTORE_SCHEMA)[0]["n"])
                    for name in counts}
        if restored != counts:
            raise RuntimeError(f"Restauração divergente: {restored}")
    finally:
        run_cli(f"DROP DATABASE IF EXISTS {RESTORE_SCHEMA}")

    packed = dump.with_suffix(dump.suffix + ".gz")
    with dump.open("rb") as source, gzip.open(packed, "wb", compresslevel=6) as target:
        shutil.copyfileobj(source, target, 1024 * 1024)
    raw_hash = hashlib.sha256(dump.read_bytes()).hexdigest()
    packed_hash = hashlib.sha256()
    with gzip.open(packed, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            packed_hash.update(chunk)
    if packed_hash.hexdigest() != raw_hash:
        raise RuntimeError("Backup compactado divergiu do dump SQL")

    evidence = {
        "mysql_version": version,
        "schema": SCHEMA,
        "table_counts": counts,
        "documented_fields": len(fields),
        "queries": queries,
        "sample_has_only_ascii_names": True,
        "quality_issues": len(queries["07_qualidade"]),
        "negative_stock_trigger": "rejeitou baixa acima do saldo; saldo permaneceu igual",
        "trigger_error": error.strip().splitlines()[-1],
        "loss_reason_check": "rejeitou perda sem motivo",
        "loss_reason_error": reason_error.strip().splitlines()[-1],
        "customer_fk_check": "rejeitou venda para cliente inexistente",
        "customer_fk_error": fk_error.strip().splitlines()[-1],
        "dump": str(dump.relative_to(ROOT)),
        "dump_sha256": raw_hash,
        "compressed_dump": str(packed.relative_to(ROOT)),
        "compressed_dump_verified": True,
        "restore_test": "contagens iguais nas sete tabelas",
    }
    target = ROOT / "evidencias" / "mysql_resultados_consultas.json"
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"MySQL {version}: {len(counts)} tabelas, {len(fields)} campos")
    print("Consultas: 7 de negocio + 1 de qualidade; nomes sem acentos")
    print(f"Dump restaurado e conferido: {dump}")
    print(f"Evidências: {target}")


if __name__ == "__main__":
    main()
