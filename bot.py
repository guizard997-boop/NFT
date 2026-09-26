import asyncio
import json
import logging
import os
import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    BotCommand, 
    BotCommandScopeDefault
)

import config

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Корректные Raw-адреса NFT-коллекций TON
COLLECTIONS_TO_MONITOR = [
    "0:80d6be28577dd80041cd58d6e32bc417ed2adbd2d13b41dddfa485bc972e3a89",  # Anonymous Numbers (+888)
    "0:08320b5da1e712392c5a2789bd079f8b3c9d77bbd51381373507d570eeed1d1d",  # Telegram Usernames
]

DB_FILE = "subscribers.json"
processed_event_ids = set()


# --- Веб-сервер для Health Check хостинга ---
async def health_check(request):
    """Отвечает хостингу 200 OK, чтобы статус горел зеленым."""
    return web.Response(text="OK", status=200)

async def start_health_server():
    """Запускает служебный HTTP-порт."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Берет порт из переменных окружения хостинга или ставит 8080 по умолчанию
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Health Check сервер успешно запущен на порту {port}")


# --- Работа с БД подписчиков ---
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
    """Сохранение подписчиков в файл."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения {DB_FILE}: {e}")


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора."""
    if config.ADMIN_IDS:
        return user_id in config.ADMIN_IDS
    return user_id == config.ADMIN_USER_ID


async def setup_bot_commands():
    """Регистрация команд в меню Telegram."""
    commands = [
        BotCommand(command="start", description="🚀 Запустить / Статус"),
        BotCommand(command="help", description="❓ Справка"),
        BotCommand(command="status", description="📊 Состояние мониторинга"),
        BotCommand(command="list", description="👥 Список подписчиков (Админ)"),
        BotCommand(command="add", description="➕ Добавить ID (Админ)"),
        BotCommand(command="remove", description="➖ Удалить ID (Админ)"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


# --- Хэндлеры бота ---
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
            f"Передайте его администратору или используйте `/add {user_id}`.",
            parse_mode="Markdown"
        )


@dp.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(
        "📖 **Справка:**\n"
        "Бот отслеживает события покупки и продаж NFT в сети TON.\n\n"
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
        return await message.answer("ℹ️ Уже добавлен.")
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
    """Рассылка уведомления всем подписчикам."""
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


# --- Поток мониторинга TonAPI ---
async def monitor_nft_activity():
    """Фоновый опрос TonAPI через HTTP."""
    logging.info("Слушатель событий TON запущен...")
    
    headers = {
        "Authorization": f"Bearer {config.TONAPI_KEY}",
        "Accept": "application/json"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            for collection in COLLECTIONS_TO_MONITOR:
                try:
                    url = f"https://tonapi.io/v2/accounts/{collection}/events?limit=10"
                    async with session.get(url) as response:
                        if response.status != 200:
                            err_text = await response.text()
                            logging.error(f"TonAPI Error [{response.status}]: {err_text}")
                            continue

                        data = await response.json()
                        events = data.get("events", [])

                        for event in events:
                            event_id = event.get("event_id")
                            if not event_id or event_id in processed_event_ids:
                                continue

                            processed_event_ids.add(event_id)

                            for action in event.get("actions", []):
                                action_type = action.get("type")

                                if action_type == "NftPurchase" and "nft_purchase" in action:
                                    purchase = action["nft_purchase"]
                                    nft = purchase.get("nft", {})
                                    price_raw = int(purchase.get("amount", {}).get("value", 0))
                                    price = price_raw / 10**9
                                    nft_name = nft.get("metadata", {}).get("name", "NFT")
                                    nft_address = nft.get("address", "")
                                    
                                    await send_alert_to_all(nft_name, f"{price:.2f}", nft_address)

                                elif action_type == "MarketplaceAction" and "marketplace_action" in action:
                                    m_action = action["marketplace_action"]
                                    nft = m_action.get("nft", {})
                                    price_raw = int(m_action.get("price", {}).get("value", 0))
                                    price = price_raw / 10**9
                                    nft_name = nft.get("metadata", {}).get("name", "NFT")
                                    nft_address = nft.get("address", "")

                                    await send_alert_to_all(nft_name, f"{price:.2f}", nft_address)

                    if len(processed_event_ids) > 2000:
                        processed_event_ids.clear()

                except Exception as e:
                    logging.error(f"Ошибка опроса коллекции {collection}: {e}")

            await asyncio.sleep(config.CHECK_INTERVAL)


# --- Главная функция ---
async def main():
    await setup_bot_commands()
    await start_health_server()  # Поднимает веб-сервер для зелёного статуса
    logging.info("Бот готов к работе.")

    if config.ADMIN_USER_ID:
        try:
            await bot.send_message(
                chat_id=config.ADMIN_USER_ID,
                text="🟢 **Сервер успешно перезапущен и мониторинг активен!**",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить старт: {e}")

    asyncio.create_task(monitor_nft_activity())
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
