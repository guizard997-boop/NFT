import json
import os
from typing import Set

from config import SUBSCRIBERS_FILE, STATE_FILE

_DEFAULT_STATE = {
    "last_event_ids": {},   # {collection_address: [event_id, ...]}
    "total_events": 0,      # счётчик всех обработанных релевантных событий
}


def _ensure_dir(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


# ---------- Подписчики ----------

def load_subscribers() -> Set[int]:
    _ensure_dir(SUBSCRIBERS_FILE)
    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(int(x) for x in data)
    except (json.JSONDecodeError, ValueError, TypeError):
        return set()


def save_subscribers(subscribers: Set[int]) -> None:
    _ensure_dir(SUBSCRIBERS_FILE)
    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(subscribers), f, ensure_ascii=False, indent=2)


def add_subscriber(user_id: int) -> bool:
    """Возвращает True, если подписчик был добавлен впервые."""
    subs = load_subscribers()
    if user_id in subs:
        return False
    subs.add(user_id)
    save_subscribers(subs)
    return True


# ---------- Состояние мониторинга ----------

def load_state() -> dict:
    _ensure_dir(STATE_FILE)
    if not os.path.exists(STATE_FILE):
        return json.loads(json.dumps(_DEFAULT_STATE))
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, value in _DEFAULT_STATE.items():
            data.setdefault(key, value)
        return data
    except (json.JSONDecodeError, ValueError):
        return json.loads(json.dumps(_DEFAULT_STATE))


def save_state(state: dict) -> None:
    _ensure_dir(STATE_FILE)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def increment_total_events(state: dict, by: int = 1) -> None:
    state["total_events"] = state.get("total_events", 0) + by