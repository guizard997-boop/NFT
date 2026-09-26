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
# TONAPI_KEY не обязателен, но снимает жёсткие лимиты на запросы.
# Получить можно на https://tonconsole.com
TONAPI_KEY = _get_str("TONAPI_KEY")
TONAPI_BASE_URL = "https://tonapi.io/v2"

# Адреса коллекций NFT для мониторинга, через запятую:
# NFT_COLLECTIONS=EQxxxxx...,EQyyyyy...
NFT_COLLECTIONS = _get_list("NFT_COLLECTIONS")

# Как часто опрашивать TonAPI (в секундах)
POLL_INTERVAL = _get_int("POLL_INTERVAL", 20)

# Сколько событий запрашивать за один опрос каждой коллекции
EVENTS_LIMIT = _get_int("EVENTS_LIMIT", 20)

# --- Health check веб-сервер (Railway сам подставляет PORT) ---
HEALTHCHECK_PORT = _get_int("PORT", 8080)

# --- Getgems ---
GETGEMS_NFT_URL = "https://getgems.io/nft/{address}"

# --- Файлы хранения данных ---
SUBSCRIBERS_FILE = os.path.join("data", "subscribers.json")
STATE_FILE = os.path.join("data", "state.json")


def validate_config() -> None:
    """Проверяет обязательные переменные окружения и явно падает с понятной
    ошибкой в логах Railway, если чего-то не хватает, вместо тихого сбоя."""
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if ADMIN_ID == 0:
        missing.append("ADMIN_ID")
    if not NFT_COLLECTIONS:
        missing.append("NFT_COLLECTIONS")

    if missing:
        raise RuntimeError(
            "Не заданы обязательные переменные окружения: "
            + ", ".join(missing)
            + ". Задайте их в Railway → Settings → Variables и перезапустите сервис."
        )