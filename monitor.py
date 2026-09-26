import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import (
    EVENTS_LIMIT,
    GETGEMS_NFT_URL,
    NFT_COLLECTIONS,
    POLL_INTERVAL,
)
from storage import (
    increment_total_events,
    load_state,
    load_subscribers,
    save_state,
)
from tonapi import get_account_events, nanoton_to_ton, normalize_nft_address, short_address

logger = logging.getLogger("monitor")

# Сколько последних event_id хранить на коллекцию, чтобы не разрастался файл
MAX_STORED_EVENT_IDS = 300

# --- Категории событий, которые нас интересуют ---
# TonAPI помечает действия внутри события полем action.type.
# Ниже — эвристическая классификация под три категории из ТЗ.
CATEGORY_PURCHASE = "purchase"
CATEGORY_MARKETPLACE = "marketplace"
CATEGORY_TRANSFER = "transfer"

CATEGORY_LABELS = {
    CATEGORY_PURCHASE: "🛒 Покупка NFT",
    CATEGORY_MARKETPLACE: "🏷 Действие на маркетплейсе",
    CATEGORY_TRANSFER: "🔁 Передача NFT",
}

# Явные совпадения по типу action, которые отдаёт TonAPI
PURCHASE_TYPES = {"NftPurchase"}
TRANSFER_TYPES = {"NftItemTransfer"}
# Всё, что похоже на активность маркетплейса, но не прямая покупка/перевод
MARKETPLACE_KEYWORDS = ("Auction", "Sale", "Listing", "Bid", "OfferPut", "OfferCancel")


def classify_action(action: Dict[str, Any]) -> Optional[str]:
    """Определяет категорию действия TonAPI или None, если оно нам не интересно."""
    action_type = action.get("type", "")

    if action_type in PURCHASE_TYPES:
        return CATEGORY_PURCHASE
    if action_type in TRANSFER_TYPES:
        return CATEGORY_TRANSFER
    if any(keyword.lower() in action_type.lower() for keyword in MARKETPLACE_KEYWORDS):
        return CATEGORY_MARKETPLACE
    return None


def extract_details(action: Dict[str, Any], category: str) -> Dict[str, Any]:
    """Достаёт сумму сделки и адрес NFT из тела конкретного action.

    Разные типы action у TonAPI кладут данные в разные под-объекты
    (например action["NftPurchase"], action["NftItemTransfer"]).
    Пробуем несколько вариантов, чтобы быть устойчивее к разночтениям схемы.
    """
    action_type = action.get("type", "")
    payload = action.get(action_type, {}) or {}

    nft_address = None
    amount_ton = 0.0

    # Адрес NFT
    nft_info = payload.get("nft")
    if isinstance(nft_info, dict):
        nft_address = nft_info.get("address")
    elif isinstance(nft_info, str):
        nft_address = nft_info

    nft_address = normalize_nft_address(nft_address)

    # Сумма сделки (обычно в нанотонах в поле amount / price)
    price_info = payload.get("amount") or payload.get("price")
    if isinstance(price_info, dict):
        amount_ton = nanoton_to_ton(price_info.get("value") or price_info.get("amount"))
    elif isinstance(price_info, (int, float, str)):
        amount_ton = nanoton_to_ton(price_info)

    return {
        "nft_address": nft_address,
        "amount_ton": amount_ton,
    }


def build_alert_text(category: str, details: Dict[str, Any], collection_address: str) -> str:
    label = CATEGORY_LABELS.get(category, "Событие")
    nft_address = details.get("nft_address") or collection_address
    amount = details.get("amount_ton", 0.0)

    lines = [f"<b>{label}</b>", ""]
    if amount:
        lines.append(f"💰 Сумма: <b>{amount} TON</b>")
    lines.append(f"🖼 NFT: <code>{short_address(nft_address)}</code>")

    return "\n".join(lines)


def build_alert_keyboard(nft_address: Optional[str], collection_address: str) -> InlineKeyboardMarkup:
    address = nft_address or collection_address
    url = GETGEMS_NFT_URL.format(address=address)
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Открыть на Getgems", url=url)]]
    )


async def broadcast_alert(bot: Bot, text: str, keyboard: InlineKeyboardMarkup) -> None:
    subscribers = load_subscribers()
    for user_id in subscribers:
        try:
            await bot.send_message(user_id, text, reply_markup=keyboard)
        except Exception as e:
            logger.warning("Не удалось отправить сообщение %s: %s", user_id, e)


async def poll_collection(
    session: aiohttp.ClientSession,
    bot: Bot,
    collection_address: str,
    state: dict,
    first_run: bool,
) -> None:
    events = await get_account_events(session, collection_address, limit=EVENTS_LIMIT)
    if not events:
        return

    seen_ids: List[str] = state["last_event_ids"].get(collection_address, [])
    seen_set = set(seen_ids)
    new_seen_ids = list(seen_ids)

    # TonAPI обычно отдаёт события от новых к старым — развернём для
    # хронологического порядка обработки/рассылки.
    for event in reversed(events):
        event_id = event.get("event_id") or event.get("lt")
        if event_id is None or event_id in seen_set:
            continue

        seen_set.add(event_id)
        new_seen_ids.append(event_id)

        # На первом запуске просто запоминаем историю, не спамим алертами
        # по старым событиям, накопленным до запуска бота.
        if first_run:
            continue

        for action in event.get("actions", []):
            try:
                category = classify_action(action)
                if category is None:
                    continue

                details = extract_details(action, category)
                text = build_alert_text(category, details, collection_address)
                keyboard = build_alert_keyboard(details.get("nft_address"), collection_address)

                await broadcast_alert(bot, text, keyboard)
                increment_total_events(state)
            except Exception as e:
                logger.exception(
                    "Не удалось обработать action в событии %s коллекции %s: %s",
                    event_id, collection_address, e,
                )

    # Храним только последние MAX_STORED_EVENT_IDS id, чтобы файл не рос бесконечно
    state["last_event_ids"][collection_address] = new_seen_ids[-MAX_STORED_EVENT_IDS:]


async def monitor_loop(bot: Bot) -> None:
    if not NFT_COLLECTIONS:
        logger.warning(
            "Список NFT_COLLECTIONS пуст — мониторинг не запущен. "
            "Укажите адреса коллекций через переменную окружения NFT_COLLECTIONS."
        )
        return

    state = load_state()
    first_run = True

    async with aiohttp.ClientSession() as session:
        while True:
            for collection_address in NFT_COLLECTIONS:
                try:
                    await poll_collection(session, bot, collection_address, state, first_run)
                except Exception as e:
                    logger.exception("Ошибка мониторинга коллекции %s: %s", collection_address, e)

            save_state(state)
            first_run = False
            await asyncio.sleep(POLL_INTERVAL)


async def send_test_alert(bot: Bot) -> None:
    """Используется командой /test — рассылает тестовое уведомление о сделке."""
    text = build_alert_text(
        CATEGORY_PURCHASE,
        {"nft_address": "EQTestTestTestTestTestTestTestTestTestTestTest", "amount_ton": 12.5},
        collection_address="EQTestCollection",
    )
    text += "\n\n<i>Это тестовое уведомление, отправлено вручную через /test</i>"
    keyboard = build_alert_keyboard("EQTestTestTestTestTestTestTestTestTestTestTest", "EQTestCollection")
    await broadcast_alert(bot, text, keyboard)