"""Redis cache-aside for the expensive, read-only dashboard projection.

MySQL remains the source of truth. A version key invalidates snapshots after writes.
"""

from __future__ import annotations

import json
import os
from threading import Lock
from time import monotonic

import redis

from giro import mysql_db

_client = redis.Redis.from_url(
    os.environ.get("GIRO_REDIS_URL", "redis://127.0.0.1:6379/0"),
    socket_connect_timeout=0.3,
    socket_timeout=0.3,
)
_lock = Lock()
_memory_lock = Lock()
_memory_version = 0
_memory_cache = None
_pending_invalidation = False
_redis_retry_at = 0.0
_VERSION_KEY = "giro:dashboard:version"
_TTL_SECONDS = 30
_REDIS_RETRY_SECONDS = 60


def status() -> str:
    try:
        return "redis" if _client.ping() else "memory"
    except redis.RedisError:
        return "memory"


def invalidate() -> None:
    global _pending_invalidation, _memory_version, _memory_cache, _redis_retry_at
    with _memory_lock:
        _memory_version += 1
        _memory_cache = None
    try:
        _client.incr(_VERSION_KEY)
        _pending_invalidation = False
    except redis.RedisError:
        _pending_invalidation = True
        _redis_retry_at = monotonic() + _REDIS_RETRY_SECONDS


def _version() -> str:
    global _pending_invalidation
    if _pending_invalidation:
        _client.incr(_VERSION_KEY)
        _pending_invalidation = False
    value = _client.get(_VERSION_KEY)
    return value.decode() if value else "0"


def dashboard_payload() -> tuple[bytes, str]:
    global _redis_retry_at
    if monotonic() < _redis_retry_at:
        return _memory_snapshot()
    try:
        version = _version()
        cached = _client.get(f"giro:dashboard:v{version}")
        if cached is not None:
            return cached, "HIT"
    except redis.RedisError:
        _redis_retry_at = monotonic() + _REDIS_RETRY_SECONDS
        return _memory_snapshot()

    # One local request builds a snapshot; concurrent requests reuse it.
    with _lock:
        try:
            version = _version()
            key = f"giro:dashboard:v{version}"
            cached = _client.get(key)
            if cached is not None:
                return cached, "HIT"
        except redis.RedisError:
            _redis_retry_at = monotonic() + _REDIS_RETRY_SECONDS
            return _memory_snapshot()
        payload = _build()
        try:
            if _version() == version:
                _client.set(key, payload, ex=_TTL_SECONDS)
        except redis.RedisError:
            _redis_retry_at = monotonic() + _REDIS_RETRY_SECONDS
            return payload, "MISS"
        return payload, "MISS"


def _memory_snapshot() -> tuple[bytes, str]:
    global _memory_cache
    with _memory_lock:
        if _memory_cache and _memory_cache[0] == _memory_version and _memory_cache[1] > monotonic():
            return _memory_cache[2], "HIT"
        payload = _build()
        _memory_cache = (_memory_version, monotonic() + _TTL_SECONDS, payload)
        return payload, "MISS"


def snapshot() -> tuple[dict, str]:
    payload, state = dashboard_payload()
    return json.loads(payload), state


def dashboard_summary() -> tuple[dict, str]:
    data, state = snapshot()
    products = data.pop("products")
    data["alert_products"] = sorted(
        (product for product in products if product["alert"] in ("out", "low")),
        key=lambda product: (product["stock"], product["id"]),
    )[:12]
    return data, state


def catalog_page(page: int, page_size: int, query: str, situation: str) -> tuple[dict, str]:
    data, state = snapshot()
    query = query.casefold().strip()
    products = [product for product in data["products"]
                if (not query or query in f"{product['name']} {product['sku']}".casefold())
                and (situation == "all" or situation == "risk" and product["alert"] in ("out", "low")
                     or situation == "expiry" and product["expiring_7d"] > 0)]
    start = (page - 1) * page_size
    return {"items": products[start:start + page_size], "total": len(products),
            "page": page, "page_size": page_size,
            "pages": max(1, (len(products) + page_size - 1) // page_size)}, state


def _build() -> bytes:
    return json.dumps(mysql_db.dashboard(), ensure_ascii=False).encode("utf-8")
