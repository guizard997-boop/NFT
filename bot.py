import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from config import settings
from categories import get_category
from fetcher import fetch_all_new_listings
from models import Listing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.bot_token)
dp = Dispatcher()

# Состояние
is_paused = False
stats = {"sent_today": 0, "last_sent": None}


def is_allowed(user_id: int) -> bool:
    return user_id in settings.whitelist_ids or user_id in settings.admin_ids


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


def format_message(listing: Listing) -> tuple[str, InlineKeyboardMarkup | None]:
    cat = get_category(listing.price_ton, listing.is_black_backdrop)
    if not cat:
        return "", None

    lines = [
        f"{cat.emoji} <b>{cat.title}</b>",
        "",
        f"🎁 <b>{listing.display_name}</b>",
        f"💰 Цена: <b>{listing.price_ton:.2f} TON</b>",
        f"🏪 Маркет: {listing.market}",
    ]

    if listing.backdrop:
        lines.append(f"🎨 Фон: {listing.backdrop}")
    if listing.model:
        lines.append(f"🧩 Модель: {listing.model}")

    lines.append("⏱ Выставлен: только что")

    text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Открыть на маркете", url=listing.url)]
    ])

    return text, keyboard


async def send_to_whitelist(text: str, keyboard: InlineKeyboardMarkup | None = None):
    """Отправляет сообщение всем из whitelist + админам."""
    targets = set(settings.whitelist_ids) | set(settings.admin_ids)
    for uid in targets:
        try:
            await bot.send_message(
                chat_id=uid,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=False,
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить {uid}: {e}")


# ====================== КОМАНДЫ ======================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not is_allowed(message.from_user.id):
        await message.answer("⛔ Доступ запрещён. Этот бот только для ограниченного круга.")
        return

    await message.answer(
        "Бека шлююююха\n\n"
        "👋 <b>NFT Tracker Bot</b>\n\n"
        "Я отслеживаю новые листинги Telegram Gifts на MRKT / Portals / Getgems\n"
        "и присылаю только свежие (≤ 1 мин) по категориям:\n\n"
        "🖤 Чёрный фон\n"
        "💧 До 3 TON\n"
        "💎 3–10 TON\n"
        "🔶 10–30 TON\n"
        "💜 50–100 TON\n\n"
        "Команды: /help",
        parse_mode=ParseMode.HTML,
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    if not is_allowed(message.from_user.id):
        return

    text = (
        "<b>Команды:</b>\n\n"
        "/start — запуск\n"
        "/status — статус трекера\n"
        "/pause — поставить на паузу\n"
        "/resume — возобновить\n"
        "/help — эта справка\n\n"
    )
    if is_admin(message.from_user.id):
        text += (
            "<b>Админ-команды:</b>\n"
            "/users — список whitelist\n"
            "/add_user ID — добавить пользователя\n"
            "/remove_user ID — удалить пользователя\n"
        )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("status"))
async def cmd_status(message: Message):
    if not is_allowed(message.from_user.id):
        return

    status = "⏸ На паузе" if is_paused else "🟢 Работает"
    last = stats["last_sent"].strftime("%H:%M:%S") if stats["last_sent"] else "ещё не было"

    await message.answer(
        f"<b>Статус трекера</b>\n\n"
        f"Состояние: {status}\n"
        f"Отправлено сегодня: {stats['sent_today']}\n"
        f"Последняя отправка: {last}\n"
        f"Интервал опроса: {settings.poll_interval} сек\n"
        f"Макс. возраст: {settings.max_age_seconds} сек",
        parse_mode=ParseMode.HTML,
    )


@dp.message(Command("pause"))
async def cmd_pause(message: Message):
    if not is_allowed(message.from_user.id):
        return
    global is_paused
    is_paused = True
    await message.answer("⏸ Трекер поставлен на паузу.")


@dp.message(Command("resume"))
async def cmd_resume(message: Message):
    if not is_allowed(message.from_user.id):
        return
    global is_paused
    is_paused = False
    await message.answer("▶️ Трекер возобновлён.")


@dp.message(Command("users"))
async def cmd_users(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Только для админов.")
        return

    users = "\n".join(str(uid) for uid in settings.whitelist_ids) or "пусто"
    admins = "\n".join(str(uid) for uid in settings.admin_ids) or "пусто"
    await message.answer(
        f"<b>Whitelist:</b>\n<code>{users}</code>\n\n"
        f"<b>Admins:</b>\n<code>{admins}</code>",
        parse_mode=ParseMode.HTML,
    )


@dp.message(Command("add_user"))
async def cmd_add_user(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return

    if not command.args:
        await message.answer("Использование: /add_user 123456789")
        return

    try:
        uid = int(command.args.strip())
        if uid not in settings.whitelist_ids:
            settings.whitelist_ids.append(uid)
            await message.answer(f"✅ Пользователь {uid} добавлен в whitelist.")
        else:
            await message.answer("Уже в списке.")
    except ValueError:
        await message.answer("ID должен быть числом.")


@dp.message(Command("remove_user"))
async def cmd_remove_user(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return

    if not command.args:
        await message.answer("Использование: /remove_user 123456789")
        return

    try:
        uid = int(command.args.strip())
        if uid in settings.whitelist_ids:
            settings.whitelist_ids.remove(uid)
            await message.answer(f"✅ Пользователь {uid} удалён.")
        else:
            await message.answer("Нет в списке.")
    except ValueError:
        await message.answer("ID должен быть числом.")


# ====================== ФОНОВЫЙ ТРЕКЕР ======================

async def tracker_loop():
    logger.info("Трекер запущен")
    while True:
        try:
            if not is_paused:
                listings = await fetch_all_new_listings()
                for listing in listings:
                    cat = get_category(listing.price_ton, listing.is_black_backdrop)
                    if not cat:
                        continue

                    text, keyboard = format_message(listing)
                    if text:
                        await send_to_whitelist(text, keyboard)
                        stats["sent_today"] += 1
                        stats["last_sent"] = datetime.now()
                        logger.info(f"Отправлено: {listing.display_name} ({listing.price_ton} TON)")
        except Exception as e:
            logger.exception(f"Ошибка в трекере: {e}")

        await asyncio.sleep(settings.poll_interval)


async def main():
    # Сброс статистики в полночь можно добавить позже
    asyncio.create_task(tracker_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())