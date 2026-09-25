from dataclasses import dataclass
from typing import Optional


@dataclass
class Category:
    emoji: str
    title: str
    priority: int  # higher = more important


CATEGORIES = {
    "black": Category(emoji="🖤", title="ЧЁРНЫЙ ФОН", priority=100),
    "under_3": Category(emoji="💧", title="ДО 3 TON", priority=10),
    "3_10": Category(emoji="💎", title="3–10 TON", priority=20),
    "10_30": Category(emoji="🔶", title="10–30 TON", priority=30),
    "50_100": Category(emoji="💜", title="50–100 TON", priority=40),
}


def get_category(price_ton: float, is_black_backdrop: bool) -> Optional[Category]:
    """
    Returns the best matching category.
    Black backdrop has absolute priority.
    """
    if is_black_backdrop:
        return CATEGORIES["black"]

    if price_ton <= 3:
        return CATEGORIES["under_3"]
    if 3 < price_ton <= 10:
        return CATEGORIES["3_10"]
    if 10 < price_ton <= 30:
        return CATEGORIES["10_30"]
    if 50 <= price_ton <= 100:
        return CATEGORIES["50_100"]

    return None  # outside interesting ranges → skip