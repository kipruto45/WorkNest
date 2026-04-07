from __future__ import annotations

from django.core.cache import cache


def _increment_counter(key: str) -> int:
    current = int(cache.get(key, 0) or 0) + 1
    cache.set(key, current, timeout=None)
    return current


def _decrement_counter(key: str) -> int:
    current = max(int(cache.get(key, 0) or 0) - 1, 0)
    if current:
        cache.set(key, current, timeout=None)
    else:
        cache.delete(key)
    return current


def _user_presence_key(user_id) -> str:
    return f"realtime:presence:user:{user_id}"


def _team_presence_key(team_id) -> str:
    return f"realtime:presence:team:{team_id}"


def register_user_connection(*, user_id) -> int:
    return _increment_counter(_user_presence_key(user_id))


def unregister_user_connection(*, user_id) -> int:
    return _decrement_counter(_user_presence_key(user_id))


def register_team_connection(*, team_id) -> int:
    return _increment_counter(_team_presence_key(team_id))


def unregister_team_connection(*, team_id) -> int:
    return _decrement_counter(_team_presence_key(team_id))


def get_user_connection_count(*, user_id) -> int:
    return int(cache.get(_user_presence_key(user_id), 0) or 0)


def get_team_connection_count(*, team_id) -> int:
    return int(cache.get(_team_presence_key(team_id), 0) or 0)


def is_user_online(*, user_id) -> bool:
    return get_user_connection_count(user_id=user_id) > 0
