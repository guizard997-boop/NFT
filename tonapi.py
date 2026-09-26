import logging
from typing import Any, Dict, List, Optional

import aiohttp

from config import TONAPI_BASE_URL, TONAPI_KEY

logger = logging.getLogger("tonapi")

NANOTON = 1_000_000_000


def _headers() -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    if TONAPI_KEY:
        headers["Authorization"] = f"Bearer {TONAPI_KEY}"
    return headers


async def get_account_events(
    session: aiohttp.ClientSession,
    account_id: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Запрашивает последние события (events/actions) для аккаунта — в нашем
    случае адреса NFT-коллекции — через публичный TonAPI v2.

    Эндпоинт: GET https://tonapi.io/v2/accounts/{account_id}/events

    ВАЖНО: TonAPI — внешний сервис, и структура полей в ответе может со
    временем меняться (добавляться новые типы action.type и т.п.).
    Если бот перестанет находить нужные события — сверьтесь с актуальной
    документацией на https://tonapi.io/api-v2 и поправьте функцию
    monitor.classify_action() под новую схему.
    """
    url = f"{TONAPI_BASE_URL}/accounts/{account_id}/events"
    params = {"limit": limit}

    try:
        async with session.get(
            url, headers=_headers(), params=params, timeout=aiohttp.ClientTimeout(total=20)
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                logger.warning("TonAPI %s -> HTTP %s: %s", account_id, resp.status, body[:200])
                return []
            data = await resp.json()
            return data.get("events", [])
    except Exception as e:
        logger.error("Ошибка запроса к TonAPI для %s: %s", account_id, e)
        return []


def nanoton_to_ton(value: Optional[Any]) -> float:
    if value is None or value == "":
        return 0.0
    try:
        value_int = int(value)
    except (ValueError, TypeError):
        logger.warning("Не удалось преобразовать сумму '%s' в число", value)
        return 0.0
    return round(value_int / NANOTON, 4)


def short_address(address: Optional[str]) -> str:
    if not address:
        return "неизвестно"
    if len(address) <= 12:
        return address
    return f"{address[:6]}...{address[-4:]}"
