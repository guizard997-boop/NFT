import logging
import os
from typing import List

logger = logging.getLogger("config")

# Локальный .env подхватывается только если файл есть (для запуска на своём
# компьютере). На Railway переменные приходят из Railway Variables — там
# .env не нужен и не используется, load_dotenv() на них не влияет.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    if raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError:
        logger.warning(
            "Переменная окружения %s='%s' не является числом, использую значение по умолчанию %s",
            name, raw, default,
        )
        return default


def _get_list(name: str) -> List[str]:
    raw = os.environ.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Telegram ---
# Задаются в Railway → Variables: BOT_TOKEN, ADMIN_ID
BOT_TOKEN = _get_str("BOT_TOKEN")
ADMIN_ID = _get_int("ADMIN_ID", 0)

# --- TonAPI ---
# TONAPI_KEY не обязателен, но снимает жёсткие лимиты на запроср