"""Confere paginacao, filtros, detalhes e cache sem alterar dados."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:3000"


def get(path):
    start = perf_counter()
    try:
        with urlopen(BASE + path, timeout=45) as response:
            return response.status, json.load(response), response.headers.get("X-Giro-Cache"), round((perf_counter() - start) * 1000)
    except HTTPError as error:
        return error.code, json.load(error), None, round((perf_counter() - start) * 1000)


def main():
    results = {}
    status, health, _, _ = get("/api/health")
    assert status == 200 and health["ok"] and health["database"] == "MySQL"
    results["health"] = health
    for name, first, second, size in (
        ("products", "/api/products?page=1", "/api/products?page=2", 12),
        ("customers", "/api/customers?q=CLI-00&page=1", "/api/customers?q=CLI-00&page=2", 12),
        ("movements", "/api/movements?page=1", "/api/movements?page=2", 20),
    ):
        code1, a, cache1, t1 = get(first)
        code2, b, cache2, t2 = get(second)
        assert code1 == code2 == 200 and len(a["items"]) == len(b["items"]) == size
        assert a["page"] == 1 and b["page"] == 2 and a["total"] == b["total"] > size
        assert {row["id"] for row in a["items"]}.isdisjoint({row["id"] for row in b["items"]}) if name != "movements" else True
        results[name] = {"total": a["total"], "page_size": size, "pages": a["pages"], "page_1_ms": t1, "page_2_ms": t2, "cache": [cache1, cache2]}

    for kind in ("ENTRY", "SALE", "LOSS"):
        code, data, _, _ = get(f"/api/movements?kind={kind}&page=1")
        assert code == 200 and all(row["kind"] == kind for row in data["items"])
        results[f"filter_{kind.lower()}"] = data["total"]
    for situation in ("risk", "expiry"):
        code, data, _, _ = get(f"/api/products?filter={situation}")
        assert code == 200 and data["page_size"] == 12
        results[f"filter_{situation}"] = data["total"]

    code, product, _, _ = get("/api/products/1")
    assert code == 200 and product["product"]["id"] == 1 and isinstance(product["batches"], list)
    code, customer, _, _ = get("/api/customers/1")
    assert code == 200 and customer["customer"]["id"] == 1 and isinstance(customer["sales"], list)
    results["details"] = "produto, lotes, eventos, cliente e compras carregados"

    for path in ("/api/products?page=0", "/api/products?filter=invalid", "/api/movements?kind=invalid"):
        code, _, _, _ = get(path)
        assert code == 400, path
    results["invalid_requests"] = "3 filtros/paginas invalidos recusados"

    _, _, cache1, t1 = get("/api/dashboard")
    _, _, cache2, t2 = get("/api/dashboard")
    results["dashboard_cache"] = {"first": cache1, "second": cache2, "first_ms": t1, "second_ms": t2}
    assert cache2 in ("HIT", "BYPASS")

    path = ROOT / "evidencias" / "api_fluxos.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: paginas, filtros, detalhes, recusas e cache. Evidencia: {path}")


if __name__ == "__main__":
    main()
