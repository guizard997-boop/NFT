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

# Raw-адреса NFT-коллекций TON (Anonymous Numbers +888 и Telegram Usernames)
COLLECTIONS_TO_MONITOR = [
    "0:80d6be28577dd80041cd58d6e32bc417ed2adbd2d13b41dddfa485bc972e3a89",
    "0:08320b5da1e712392c5a2789bd079f8b3c9d77bbd51381373507d570eeed1d1d",
]

DB_FILE = "subscribers.json"
processed_event_ids = set()


# --- Health Check для хостинга ---
async def health_check(request):
    return web.Response(text="OK", status=200)

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Health Check сервер работает на порту {port}")


# --- Управление подписчиками ---
def load_subscribers() -> list[int]:
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
            f"Чтобы получать алерты, добавьте его через `/add {user_id}`.",
            parse_mode="Markdown"
        )


@dp.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(
        "📖 **Справка:**\n"
        "Бот отслеживает покупки и транзакции NFT в сети TON.\n\n"
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
        f"• **Подписчиков в базе:** `{len(subs)}/{config.MAX_SUBSCRIBERS}`\n"
        f"• **Обработано событий:** `{len(processed_event_ids)}`",
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
        return await message.answer("ℹ️ Уже в списке.")

    subs.append(new_id)
    save_subscribers(subs)
    await message.answer(f"✅ Пользователь `{new_id}` добавлен в подписчики!", parse_mode="Markdown")


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
        return await message.answer("ℹ️ Не найден в базе.")

    subs.remove(remove_id)
    save_subscribers(subs)
    await message.answer(f"🗑 Пользователь `{remove_id}` удален!", parse_mode="Markdown")


@dp.message(Command("list"))
async def list_subscribers(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    subs = load_subscribers()
    subs_text = "\n".join([f"• `{uid}`" for uid in subs]) if subs else "Список пуст."
    await message.answer(f"📊 **Подписчики ({len(subs)}):**\n\n{subs_text}", parse_mode="Markdown")


async def send_alert_to_all(title: str, price_str: str, nft_address: str):
    """Рассылка алертов подписчикам."""
    subscribers = load_subscribers()
    if not subscribers:
        logging.warning("⚠️ Найдено событие, но список подписчиков пуст!")
        return

    nft_link = f"https://getgems.io/nft/{nft_address}" if nft_address else "https://getgems.io"
    text = (
        f"⚡️ **СДЕЛАНО СОБЫТИЕ В TON!**\n\n"
        f"🏷 **Тип:** `{title}`\n"
        f"💰 **Сумма:** `{price_str}`\n"
        f"📍 **NFT:** `{nft_address[:12]}...{nft_address[-6:]}`" if len(nft_address) > 20 else f"📍 **NFT:** `{nft_address}`"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть на Getgems", url=nft_link)]
    ])

    for user_id in subscribers:
        try:
            await bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown", reply_markup=keyboard)
            logging.info(f"✅ Алерт отправлен пользователю {user_id}")
        except Exception as e:
            logging.error(f"❌ Ошибка отправки пользователю {user_id}: {e}")


# --- Мониторинг TonAPI ---
async def monitor_nft_activity():
    logging.info("Слушатель событий TON запущен...")
    
    headers = {"Accept": "application/json"}
    if getattr(config, "TONAPI_KEY", None):
        headers["Authorization"] = f"Bearer {config.TONAPI_KEY}"

    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            for collection in COLLECTIONS_TO_MONITOR:
                try:
                    url = f"https://tonapi.io/v2/accounts/{collection}/events?limit=5"
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
                            logging.info(f"🔎 Новое событие сети [{event_id[:10]}...]")

                            for action in event.get("actions", []):
                                action_type = action.get("type", "Unknown")
                                
                                # 1. Покупка NFT
                                if action_type == "NftPurchase":
                                    purchase = action.get("nft_purchase", {})
                                    price_raw = int(purchase.get("amount", {}).get("value", 0))
                                    price = price_raw / 10**9
                                    nft_addr = purchase.get("nft", {}).get("address", "")
                                    await send_alert_to_all("Покупка NFT", f"{price:.2f} TON", nft_addr)

                                # 2. Торговля на маркетплейсе
                                elif action_type == "MarketplaceAction":
                                    m_act = action.get("marketplace_action", {})
                                    price_raw = int(m_act.get("price", {}).get("value", 0))
                                    price = price_raw / 10**9
                                    nft_addr = m_act.get("nft", {}).get("address", "")
                                    await send_alert_to_all("Маркетплейс", f"{price:.2f} TON", nft_addr)

                                # 3. Любая передача NFT
                                elif action_type == "NftItemTransfer":
                                    transfer = action.get("nft_item_transfer", {})
                                    nft_addr = transfer.get("nft", "")
                                    await send_alert_to_all("Передача NFT", "—", nft_addr)

                    # Очистка памяти
                    if len(processed_event_ids) > 1000:
                        processed_event_ids.clear()

                except Exception as e:
                    logging.error(f"Ошибка опроса коллекции {collection}: {e}")

            await asyncio.sleep(getattr(config, "CHECK_INTERVAL", 5))


async def main():
    await setup_bot_commands()
    await start_health_server()
    logging.info("Бот готов к работе.")

    if config.ADMIN_USER_ID:
        try:
            await bot.send_message(
                chat_id=config.ADMIN_USER_ID,
                text="🟢 **Бот перезапущен! Проверь подписку командой /status.**",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить стартовое сообщение: {e}")

    asyncio.create_task(monitor_nft_activity())
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
