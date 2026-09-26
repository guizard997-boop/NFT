import asyncio
import json
import logging
import os
import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

import config

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Инициализация
bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Мониторим 2 коллекции (Anonymous +888 и Telegram Usernames)
COLLECTIONS = [
    "0:80d6be28577dd80041cd58d6e32bc417ed2adbd2d13b41dddfa485bc972e3a89",
    "0:08320b5da1e712392c5a2789bd079f8b3c9d77bbd51381373507d570eeed1d1d",
]

DB_FILE = "subscribers.json"
PROCESSED_EVENTS = set()


# --- База данных подписчиков ---
def get_subscribers() -> list[int]:
    if not os.path.exists(DB_FILE):
        admin = getattr(config, "ADMIN_USER_ID", None)
        initial = [admin] if admin else []
        save_subscribers(initial)
        return initial
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Ошибка чтения DB: {e}")
        return []

def save_subscribers(subs: list[int]):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(list(set(subs)), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения DB: {e}")

def is_admin(user_id: int) -> bool:
    admin_id = getattr(config, "ADMIN_USER_ID", None)
    admin_ids = getattr(config, "ADMIN_IDS", [])
    return user_id == admin_id or user_id in admin_ids


# --- Health Check для хостинга ---
async def start_health_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    app.router.add_get("/health", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Health check запущен на порту {port}")


# --- Telegram команды ---
@dp.message(CommandStart())
async def cmd_start(msg: types.Message):
    user_id = msg.from_user.id
    subs = get_subscribers()
    if user_id not in subs:
        subs.append(user_id)
        save_subscribers(subs)
        await msg.answer(f"✅ Ты подписан на алерты! Твой ID: `{user_id}`", parse_mode="Markdown")
    else:
        await msg.answer(f"👋 Мониторинг активен. Твой ID: `{user_id}`", parse_mode="Markdown")

@dp.message(Command("status"))
async def cmd_status(msg: types.Message):
    subs = get_subscribers()
    await msg.answer(
        f"📊 **Статус:**\n"
        f"• Твой ID: `{msg.from_user.id}`\n"
        f"• Админ: `{'Да' if is_admin(msg.from_user.id) else 'Нет'}`\n"
        f"• Подписчиков: `{len(subs)}`\n"
        f"• Событий обработано: `{len(PROCESSED_EVENTS)}`",
        parse_mode="Markdown"
    )

@dp.message(Command("test"))
async def cmd_test(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return await msg.answer("⛔ Только для админа.")
    await msg.answer("🧪 Запуск теста рассылки...")
    await broadcast_alert("ТЕСТОВОЕ СОБЫТИЕ", "100.00 TON", "0:80d6be28577dd80041cd58d6e32bc417ed2adbd2d13b41dddfa485bc972e3a89")

@dp.message(Command("add"))
async def cmd_add(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return
    args = msg.text.split()
    if len(args) > 1 and args[1].isdigit():
        new_id = int(args[1])
        subs = get_subscribers()
        subs.append(new_id)
        save_subscribers(subs)
        await msg.answer(f"✅ Добавлен: `{new_id}`", parse_mode="Markdown")

@dp.message(Command("list"))
async def cmd_list(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return
    subs = get_subscribers()
    await msg.answer(f"👥 Список: {subs}")


# --- Рассылка ---
async def broadcast_alert(event_type: str, price: str, nft_address: str):
    subs = get_subscribers()
    if not subs:
        logging.warning("Событие найдено, но список подписчиков пуст.")
        return

    nft_link = f"https://getgems.io/nft/{nft_address}" if nft_address else "https://getgems.io"
    text = (
        f"🚨 **NFT СДЕЛКА В TON!**\n\n"
        f"📌 **Тип:** `{event_type}`\n"
        f"💰 **Цена:** `{price}`\n"
        f"📍 **Адрес:** `{nft_address[:10]}...{nft_address[-6:]}`"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Открыть на Getgems", url=nft_link)]
    ])

    for uid in subs:
        try:
            await bot.send_message(chat_id=uid, text=text, parse_mode="Markdown", reply_markup=kb)
            logging.info(f"Алерт ушел пользователю {uid}")
        except Exception as e:
            logging.error(f"Не удалось отправить пользователю {uid}: {e}")


# --- Парсинг TonAPI ---
async def fetch_ton_events():
    logging.info("Цикл TonAPI запущен...")
    
    headers = {"Accept": "application/json"}
    api_key = getattr(config, "TONAPI_KEY", None)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            for collection in COLLECTIONS:
                try:
                    url = f"https://tonapi.io/v2/accounts/{collection}/events?limit=10"
                    async with session.get(url, timeout=10) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            logging.error(f"TonAPI Ошибка HTTP {resp.status}: {body[:100]}")
                            continue

                        data = await resp.json()
                        events = data.get("events", [])

                        for ev in events:
                            event_id = ev.get("event_id")
                            if not event_id or event_id in PROCESSED_EVENTS:
                                continue

                            # Фиксируем новое событие
                            PROCESSED_EVENTS.add(event_id)
                            logging.info(f"🔥 Новое событие из TON: {event_id[:12]}")

                            actions = ev.get("actions", [])
                            for act in actions:
                                act_type = act.get("type")
                                
                                # 1. Прямая покупка NFT
                                if act_type == "NftPurchase" and "nft_purchase" in act:
                                    p = act["nft_purchase"]
                                    price = int(p.get("amount", {}).get("value", 0)) / 10**9
                                    addr = p.get("nft", {}).get("address", "")
                                    await broadcast_alert("Покупка NFT", f"{price:.2f} TON", addr)

                                # 2. Действия на маркетплейсах
                                elif act_type == "MarketplaceAction" and "marketplace_action" in act:
                                    m = act["marketplace_action"]
                                    price = int(m.get("price", {}).get("value", 0)) / 10**9
                                    addr = m.get("nft", {}).get("address", "")
                                    await broadcast_alert("Маркетплейс", f"{price:.2f} TON", addr)

                                # 3. Трансферы / смены владельца
                                elif act_type == "NftItemTransfer" and "nft_item_transfer" in act:
                                    t = act["nft_item_transfer"]
                                    addr = t.get("nft", "")
                                    await broadcast_alert("Передача NFT", "—", addr)

                    if len(PROCESSED_EVENTS) > 2000:
                        PROCESSED_EVENTS.clear()

                except Exception as e:
                    logging.error(f"Сбой при опросе коллекции {collection}: {e}")

            interval = getattr(config, "CHECK_INTERVAL", 5)
            await asyncio.sleep(interval)


# --- Точка входа ---
async def main():
    # Регистрируем команды в меню Telegram
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить"),
        BotCommand(command="status", description="Статус"),
        BotCommand(command="test", description="Тест"),
        BotCommand(command="add", description="Добавить ID"),
        BotCommand(command="list", description="Список ID"),
    ])
    
    await start_health_server()
    
    # Фоновая задача опроса API
    asyncio.create_task(fetch_ton_events())
    
    logging.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
