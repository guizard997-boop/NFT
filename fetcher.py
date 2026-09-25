"""
Модуль получения новых листингов.

Сейчас реализованы заглушки + пример структуры под реальные API.
В продакшене нужно подставить рабочие эндпоинты:

- Getgems: https://api.getgems.io/public-api (нужен API key, 10 GRAM/мес)
- MRKT:    https://api.tgmrkt.io (нужна авторизация через Telegram WebApp)
- Portals: аналогично, часто через неофициальные клиенты

Функция fetch_all_new_listings() должна возвращать список Listing,
у которых listed_at не старше MAX_AGE_SECONDS.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import List
import aiohttp

from models import Listing
from config import settings


# Простое хранилище уже отправленных id (в памяти + можно сохранить в файл)
_seen_ids: set[str] = set()


def mark_seen(listing_id: str):
    _seen_ids.add(listing_id)


def is_seen(listing_id: str) -> bool:
    return listing_id in _seen_ids


async def fetch_getgems(session: aiohttp.ClientSession) -> List[Listing]:
    """Пример запроса к Getgems (нужен API key)."""
    if not settings.getgems_api_key:
        return []

    # Пример: можно запрашивать конкретные коллекции подарков
    # url = f"https://api.getgems.io/public-api/v1/nfts/on-sale/{collection_address}"
    # headers = {"Authorization": settings.getgems_api_key}
    # ...
    return []


async def fetch_mrkt(session: aiohttp.ClientSession) -> List[Listing]:
    """
    MRKT (tgmrkt.io) — неофициальный API.
    Обычно требует Authorization: token, полученный через Telegram WebApp initData.
    """
    # Пример структуры:
    # url = "https://api.tgmrkt.io/api/v1/gifts/saling"
    # payload = {"ordering": "Price", "lowToHigh": True, "count": 50, ...}
    return []


async def fetch_portals(session: aiohttp.ClientSession) -> List[Listing]:
    """Portals — аналогично MRKT, неофициальные клиенты."""
    return []


async def fetch_all_new_listings() -> List[Listing]:
    """
    Собирает свежие листинги со всех маркетов.
    Фильтрует по времени (≤ MAX_AGE_SECONDS) и уже виденным.
    """
    now = datetime.now(timezone.utc)
    results: List[Listing] = []

    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_getgems(session),
            fetch_mrkt(session),
            fetch_portals(session),
        ]
        all_lists = await asyncio.gather(*tasks, return_exceptions=True)

        for lst in all_lists:
            if isinstance(lst, Exception):
                continue
            for item in lst:
                if is_seen(item.id):
                    continue

                # Проверка свежести
                if item.listed_at:
                    age = (now - item.listed_at).total_seconds()
                    if age > settings.max_age_seconds:
                        continue

                results.append(item)
                mark_seen(item.id)

    return results


# ====================== DEMO / MOCK ======================
# Чтобы бот сразу можно было тестировать — демо-генератор.
# Удали или закомментируй, когда подключишь реальные API.

_demo_counter = 0

async def fetch_demo_listings() -> List[Listing]:
    """Генерирует фейковые листинги для теста (каждые ~N запусков)."""
    global _demo_counter
    _demo_counter += 1

    if _demo_counter % 3 != 0:  # не каждый раз
        return []

    now = datetime.now(timezone.utc)
    demo = [
        Listing(
            id=f"demo-black-{int(time.time())}",
            name="Lunar Snake",
            number="109967",
            price_ton=18.5,
            market="MRKT",
            url="https://t.me/mrkt",
            is_black_backdrop=True,
            listed_at=now,
            backdrop="Black",
        ),
        Listing(
            id=f"demo-cheap-{int(time.time())}",
            name="Ice Cream",
            number="282213",
            price_ton=2.1,
            market="Portals",
            url="https://t.me/portals",
            is_black_backdrop=False,
            listed_at=now,
        ),
    ]
    fresh = [x for x in demo if not is_seen(x.id)]
    for x in fresh:
        mark_seen(x.id)
    return fresh


# Переключаем на демо, пока нет реальных ключей
async def fetch_all_new_listings() -> List[Listing]:
    return await fetch_demo_listings()