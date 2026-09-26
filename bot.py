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
    """Отвечает хостингу 200 OK, чтобы статус контейнера был зелёным."""
    return web.Response(text="OK", status=200)

async def start_health_server():
    """Запускает служебный HTTP-сервер."""
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
    """Загрузка списка подписчиков."""
    if getattr(config, "WHITELIST_IDS", None):
        return config.WHITELIST_IDS[:config.MAX_SUBSCRIBERS]

    if not os.path.exists(DB_FILE):
        initial = [config.ADMIN_USER_ID] if getattr(config, "ADMIN_USER_ID", None) else []
        save_subscribers(initial)
        return initial
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Ошибка чтения {DB_FILE}: {e}")
        return [config.ADMIN_USER_ID] if getattr(config, "ADMIN_USER_ID", None) else []


def save_subscribers(subs: list[int]):
    """Сохранение подписчиков в файл."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения {DB_FILE}: {e}")


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора."""
    admin_ids = getattr(config, "ADMIN_IDS", [])
    if admin_ids:
        return user_id in admin_ids
    return user_id == getattr(config, "ADMIN_USER_ID", None)


async def setup_bot_commands():
    """Регистрация меню команд Telegram."""
    commands = [
        BotCommand(command="start", description="🚀 Запустить / Статус"),
        BotCommand(command="help", description="❓ Справка"),
        BotCommand(command="status", description="📊 Состояние мониторинга"),
        BotCommand(command="test", description="🧪 Тестовая рассылка (Админ)"),
        BotCommand(command="list", description="👥 Список подписчиков (Админ)"),
        BotCommand(command="add", description="➕ Добавить ID (Админ)"),
        BotCommand(command="remove", description="➖ Удалить ID (Админ)"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


# --- Хэндлеры команд ---
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    subs = load_subscribers()

    if user_id in subs:
        await message.answer(
            f"👋 **Привет, {message.from_user.first_name}!**\n\n"
            f"Мониторинг NFT-рынка активен.\n"
            f"Подписчиков: `{len(subs)}/{getattr(config, 'MAX_SUBSCRIBERS', 50)}`.",
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
        "Бот отслеживает покупки и сделки NFT в сети TON.\n\n"
        "**Команды админа:**\n"
        "• `/test` — проверить рассылку\n"
        "• `/add <USER_ID>` — добавить подписчика\n"
        "• `/remove <USER_ID>` — удалить подписчика\n"
        "• `/list` — список подписчиков",
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
        f"• **Подписчиков в базе:** `{len(subs)}/{getattr(config, 'MAX_SUBSCRIBERS', 50)}`\n"
        f"• **Обработано событий:** `{len(processed_event_ids)}`",
        parse_mode="Markdown"
    )


@dp.message(Command("test"))
async def test_alert_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Только для администратора.")
    
    await message.answer("⏳ Запускаю тестовую рассылку...")
    await send_alert_to_all(
        title="ТЕСТОВОЕ СОБЫТИЕ", 
        price_str="888.00 TON", 
        nft_address="0:80d6be28577dd80041cd58d6e32bc417ed2adbd2d13b41dddfa485bc972e3a89"
    )
    await message.answer("✅ Тестовое сообщение отправлено всем подписчикам!")


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
    """Рассылка сообщений подписчикам."""
    subscribers = load_subscribers()
    if not subscribers:
        logging.warning("⚠️ Найдено событие, но список подписчиков пуст!")
        return

    nft_link = f"https://getgems.io/nft/{nft_address}" if nft_address else "https://getgems.io"
    short_addr = f"{nft_address[:10]}...{nft_address[-6:]}" if len(nft_address) > 20 else nft_address
    
    text = (
        f"⚡️ **СДЕЛАНО СОБЫТИЕ В TON!**\n\n"
        f"🏷 **Тип:** `{title}`\n"
        f"💰 **Цена / Сумма:** `{price_str}`\n"
        f"📍 **NFT:** `{short_addr}`"
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
    """Фоновый опрос TonAPI."""
    logging.info("Слушатель событий TON запущен...")
    
    headers = {"Accept": "application/json"}
    api_key = getattr(config, "TONAPI_KEY", None)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

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

                                # 2. Маркетплейс
                                elif action_type == "MarketplaceAction":
                                    m_act = action.get("marketplace_action", {})
                                    price_raw = int(m_act.get("price", {}).get("value", 0))
                                    price = price_raw / 10**9
                                    nft_addr = m_act.get("nft", {}).get("address", "")
                                    await send_alert_to_all("Маркетплейс", f"{price:.2f} TON", nft_addr)

                                # 3. Передача NFT
                                elif action_type == "NftItemTransfer":
                                    transfer = action.get("nft_item_transfer", {})
                                    nft_addr = transfer.get("nft", "")
                                    await send_alert_to_all("Передача NFT", "—", nft_addr)

                    if len(processed_event_ids) > 1000:
                        processed_event_ids.clear()

                except Exception as e:
                    logging.error(f"Ошибка опроса коллекции {collection}: {e}")

            interval = getattr(config, "CHECK_INTERVAL", 5)
            await asyncio.sleep(interval)


async def main():
    await setup_bot_commands()
    await start_health_server()
    logging.info("Бот готов к работе.")

    admin_id = getattr(config, "ADMIN_USER_ID", None)
    if admin_id:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text="🟢 **Бот успешно перезапущен и готов к работе!**",
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
