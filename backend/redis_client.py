"""Redis 会话缓存"""
import json
import os

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
HISTORY_TTL = 60 * 60 * 24 * 7  # 会话缓存 7 天

_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def _key(session_id: str) -> str:
    return f"travel:history:{session_id}"


def get_history(session_id: str) -> list:
    raw = _client.get(_key(session_id))
    return json.loads(raw) if raw else []


def append_message(session_id: str, role: str, content: str) -> None:
    history = get_history(session_id)
    history.append({"role": role, "content": content})
    key = _key(session_id)
    _client.set(key, json.dumps(history, ensure_ascii=False))
    _client.expire(key, HISTORY_TTL)
