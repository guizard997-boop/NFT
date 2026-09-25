import asyncio
import json
import logging
import os

from pytonapi import Tonapi
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    BotCommand, 
    BotCommandScopeDefault
)

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
tonapi = Tonapi(api_key=config.TONAPI_KEY)

# Активные коллекции с постоянным потоком сделок (Telegram Юзернеймы, Номера +888)
COLLECTIONS_TO_MONITOR = [
    "EQCA14o1-4BkOcY1LJK9W3-L_Jq3e1",  # Telegram Usernames
    "EQAO2X6432_32gA86WNaM13J-2M_432",  # Anonymous Telegram Numbers
]

DB_FILE = "subscribers.json"
processed_event_ids = set()


def load_subscribers() -> list[int]:
    """Загрузка списка подписчиков."""
    if config.WHITELIST_IDS:
        return config.WHITELIST_IDS[:config.MAX_SUBSCRIBERS]

    if not os.path.exists(DB_FILE):
        initial = [config.ADMIN_USER_ID] if config.ADMIN_USER_ID else []
        save_subscribers(initial)
        return initial
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Ошибка чтения {DB_FILE}: {e}")
        return [config.ADMIN_USER_ID] if config.ADMIN_USER_ID else []


def save_subscribers(subs: list[int]):
    """Сохранение подписчиков в локальный файл."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения {DB_FILE}: {e}")


def is_admin(user_id: int) -> bool:
    if config.ADMIN_IDS:
        return user_id in config.ADMIN_IDS
    return user_id == config.ADMIN_USER_ID


async def setup_bot_commands():
    commands = [
        BotCommand(command="start", description="🚀 Запустить / Статус"),
        BotCommand(command="help", description="❓ Справка"),
        BotCommand(command="status", description="📊 Состояние мониторинга"),
        BotCommand(command="list", description="👥 Список подписчиков (Админ)"),
        BotCommand(command="add", description="➕ Добавить ID (Админ)"),
        BotCommand(command="remove", description="➖ Удалить ID (Админ)"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    subs = load_subscribers()

    if user_id in subs:
        await message.answer(
            f"👋 **Привет, {message.from_user.first_name}!**\n\n"
            f"Мониторинг NFT-рынка активен.\n"
            f"Подписчиков: `{len(subs)}/{config.MAX_SUBSCRIBERS}`.",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"👋 Ваш Telegram ID: `{user_id}`\n"
            f"Передайте его администратору или используйте `/add {user_id}` (если вы админ).",
            parse_mode="Markdown"
        )


@dp.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(
        "📖 **Справка:**\n"
        "Бот отслеживает события покупки, продажи и аукционов NFT в сети TON и присылает их в реальном времени.\n\n"
        "**Команды админа:**\n"
        "• `/add <USER_ID>`\n"
        "• `/remove <USER_ID>`\n"
        "• `/list`",
        parse_mode="Markdown"
    )


@dp.message(Command("status"))
async def status_handler(message: types.Message):
    subs = load_subscribers()
    user_id = message.from_user.id
    await message.answer(
        f"🖥 **Статус бота:**\n\n"
        f"• **Ваш ID:** `{user_id}`\n"
        f"• **Админ:** `{'Да' if is_admin(user_id) else 'Нет'}`\n"
        f"• **Подписчиков:** `{len(subs)}/{config.MAX_SUBSCRIBERS}`\n"
        f"• **Статус потока:** `Работает 🟢`",
        parse_mode="Markdown"
    )


@dp.message(Command("add"))
async def add_subscriber(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Нет прав.")
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer("⚠️ Формат: `/add USER_ID`", parse_mode="Markdown")

    new_id = int(args[1])
    subs = load_subscribers()
    if new_id in subs:
        return await message.answer("ℹ️ Ужe добавлен.")
    if len(subs) >= config.MAX_SUBSCRIBERS:
        return await message.answer("⚠️ Достигнут лимит пользователей!")

    subs.append(new_id)
    save_subscribers(subs)
    await message.answer(f"✅ Пользователь `{new_id}` добавлен!", parse_mode="Markdown")


@dp.message(Command("remove"))
async def remove_subscriber(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Нет прав.")
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer("⚠️ Формат: `/remove USER_ID`", parse_mode="Markdown")

    remove_id = int(args[1])
    subs = load_subscribers()
    if remove_id not in subs:
        return await message.answer("ℹ️ Не найден.")

    subs.remove(remove_id)
    save_subscribers(subs)
    await message.answer(f"🗑 Пользователь `{remove_id}` удален!", parse_mode="Markdown")


@dp.message(Command("list"))
async def list_subscribers(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    subs = load_subscribers()
    subs_text = "\n".join([f"• `{uid}`" for uid in subs])
    await message.answer(f"📊 **Подписчики ({len(subs)}):**\n\n{subs_text}", parse_mode="Markdown")


async def send_alert_to_all(nft_name: str, price_ton: str, nft_address: str):
    """Рассылка сообщения всем подписчикам."""
    nft_link = f"https://getgems.io/nft/{nft_address}"
    text = (
        f"⚡️ **СВЕЖИЙ ЛОТ / СДЕЛКА!**\n\n"
        f"🏷 **Название:** `{nft_name}`\n"
        f"💰 **Цена/Ставка:** `{price_ton} TON`\n"
        f"📍 **Адрес:** `{nft_address}`"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть на Getgems", url=nft_link)]
    ])

    subscribers = load_subscribers()
    for user_id in subscribers:
        try:
            await bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Ошибка отправки пользователю {user_id}: {e}")


async def monitor_nft_activity():
    """Фоновый поток сбора активности."""
    logging.info("Слушатель событий TON запущен...")

    while True:
        for collection in COLLECTIONS_TO_MONITOR:
            try:
                activity = tonapi.nft.get_collection_history(account_id=collection, limit=10)

                for event in activity.events:
                    event_id = event.event_id
                    if event_id in processed_event_ids:
                        continue

                    processed_event_ids.add(event_id)

                    for action in event.actions:
                        if action.type == "NftPurchase":
                            nft = action.nft_purchase.nft
                            price = action.nft_purchase.amount.value / 10**9
                            await send_alert_to_all(
                                nft.metadata.get("name", "NFT"),
                                f"{price:.2f}",
                                nft.address.to_userfriendly()
                            )
                        elif action.type == "MarketplaceAction":
                            nft = action.marketplace_action.nft
                            price = action.marketplace_action.price.value / 10**9
                            await send_alert_to_all(
                                nft.metadata.get("name", "NFT"),
                                f"{price:.2f}",
                                nft.address.to_userfriendly()
                            )

                if len(processed_event_ids) > 2000:
                    processed_event_ids.clear()

            except Exception as e:
                logging.error(f"Ошибка опроса коллекции {collection}: {e}")

        await asyncio.sleep(config.CHECK_INTERVAL)


async def main():
    await setup_bot_commands()
    logging.info("Бот готов к работе.")

    # Проверочное сообщение админу при успешном запуске контейнера
    if config.ADMIN_USER_ID:
        try:
            await bot.send_message(
                chat_id=config.ADMIN_USER_ID,
                text="🟢 **Сервер успешно перезапущен и мониторинг активен!**",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить тестовый старт админу: {e}")

    asyncio.create_task(monitor_nft_activity())
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
