import logging

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from config import ADMIN_ID
from monitor import send_test_alert
from storage import add_subscriber, load_state, load_subscribers

logger = logging.getLogger("handlers")

router = Router()


def is_admin(user_id: int) -> bool:
    return ADMIN_ID != 0 and user_id == ADMIN_ID


@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    added = add_subscriber(user_id)

    lines = [f"👋 Привет! Ваш Telegram ID: <code>{user_id}</code>"]
    if added:
        lines.append("✅ Вы подписаны на уведомления о событиях NFT.")
    else:
        lines.append("ℹ️ Вы уже подписаны на уведомления.")

    await message.answer("\n".join(lines))


@router.message(Command("status"))
async def cmd_status(message: Message):
    user_id = message.from_user.id
    subscribers = load_subscribers()
    state = load_state()

    text = (
        f"📊 <b>Статус</b>\n\n"
        f"ВЀ