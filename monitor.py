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

    nft_addre