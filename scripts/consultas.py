"""Executa as consultas da A3 e grava resultados JSON quando autorizado."""

import json

from giro import db


def main():
    db.initialize()
    results = {}
    with db.database() as conn:
        for path in sorted((db.ROOT / "sql" / "consultas").glob("*.sql")):
            rows = conn.execute(path.read_text(encoding="utf-8")).fetchall()
            results[path.stem] = [dict(row) for row in rows]
    output = db.ROOT / "evidencias" / "resultados.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Resultados gravados em {output}")


if __name__ == "__main__":
    main()
