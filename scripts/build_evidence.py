"""Gera banco SQLite limpo e evidências reproduzíveis para a A3."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import csv
from datetime import datetime, timezone

from giro import db


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = db.ROOT / "historico" / "sqlite" / "GIRO_prototipo_A3.sqlite3"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    old_path = db.DB_PATH
    db.DB_PATH = target
    try:
        db.initialize()
        with db.database() as conn:
            results = {}
            query_files = sorted((db.ROOT / "sql" / "consultas").glob("*.sql"))
            for path in query_files:
                results[path.stem] = [dict(row) for row in conn.execute(path.read_text(encoding="utf-8"))]
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = [dict(row) for row in conn.execute("PRAGMA foreign_key_check")]
            counts = {
                name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                for name in ("category", "supplier", "product", "batch", "sale", "stock_event")
            }
            sqlite_version = conn.execute("SELECT sqlite_version()").fetchone()[0]
            actual_fields = {
                (name, row["name"])
                for name in counts
                for row in conn.execute(f"PRAGMA table_info({name})")
            }
            with (db.ROOT / "docs" / "dicionario_de_dados.csv").open(encoding="utf-8", newline="") as stream:
                documented_fields = {(row["tabela"], row["campo"]) for row in csv.DictReader(stream, delimiter=";")}
            if actual_fields != documented_fields:
                raise RuntimeError(f"Dicionário divergente: faltam {actual_fields - documented_fields}; sobram {documented_fields - actual_fields}")
            schema_inventory = {
                name: {
                    "columns": [dict(row) for row in conn.execute(f"PRAGMA table_info({name})")],
                    "foreign_keys": [dict(row) for row in conn.execute(f"PRAGMA foreign_key_list({name})")],
                    "indexes": [dict(row) for row in conn.execute(f"PRAGMA index_list({name})")],
                }
                for name in counts
            }
            backup_path = db.ROOT / "historico" / "sqlite" / "GIRO_backup_A3.sqlite3"
            with sqlite3.connect(backup_path) as backup_conn:
                conn.backup(backup_conn)
                backup_integrity = backup_conn.execute("PRAGMA integrity_check").fetchone()[0]
        evidence = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "database": str(target.relative_to(db.ROOT)),
            "sqlite_version": sqlite_version,
            "schema_sha256": digest(db.ROOT / "sql" / "01_schema.sql"),
            "seed_sha256": digest(db.ROOT / "sql" / "02_seed.sql"),
            "integrity_check": integrity,
            "foreign_key_violations": foreign_keys,
            "table_counts": counts,
            "documented_fields": len(documented_fields),
            "schema_inventory": schema_inventory,
            "backup": str(backup_path.relative_to(db.ROOT)),
            "backup_integrity_check": backup_integrity,
            "queries": results,
        }
        output = db.ROOT / "evidencias" / "resultados_consultas.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        if integrity != "ok" or backup_integrity != "ok" or foreign_keys or results["07_qualidade"]:
            raise RuntimeError("Validação do banco falhou; consulte resultados_consultas.json")
        print(f"Banco: {target}")
        print(f"Evidências: {output}")
        print(f"Consultas de negócio: {len(query_files) - 1}; integridade: {integrity}")
    finally:
        db.DB_PATH = old_path


if __name__ == "__main__":
    main()
