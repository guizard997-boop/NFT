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


def s