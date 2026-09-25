import asyncio
import json
import logging
import os

# Прямой импорт асинхронного клиента для предотвращения ошибок импорта
try:
    from pytonapi import AsyncTonapi as TonapiClient
except ImportError:
    try:
        from pytonapi.async_tonapi import AsyncTonapi as TonapiClient
    except ImportError:
        from pytonapi import Tonapi as TonapiClient

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

# Инициализация клиента
tonapi = TonapiClient(api_key=config.TONAPI_KEY)

DB_FILE = "subscribers.json"
processed_tx_hashes = set()


def load_subscribers() -> list[int]:
    """Загружает список подписчиков (приоритет у WHITELIST_IDS из Railway)."""
    if config.WHITELIST_IDS:
        return config.WHITELIST_IDS[:config.MAX_SUBSCRIBERS]

    if not os.path.exists(DB_FILE):
        initial_subs = [config.ADMIN_USER_ID]
        save_subscribers(initial_subs)
        return initial_subs
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Ошибка чтения {DB_FILE}: {e}")
        return [config.ADMIN_USER_ID]


def save_subscribers(subs: list[int]):
    """Сохраняет список ID подписчиков в локальный JSON."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения в {DB_FILE}: {e}")


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора."""
    if config.ADMIN_IDS:
        return user_id in config.ADMIN_IDS
    return user_id == config.ADMIN_USER_ID


async def setup_bot_commands():
    """Регистрация кнопки 'Меню' в Telegram."""
    commands = [
        BotCommand(command="start", description="🚀 Запустить / Проверить подписку"),
        BotCommand(command="help", description="❓ Справка по фильтрам"),
        BotCommand(command="status", description="📊 Ваш Telegram ID и статус"),
        BotCommand(command="list", description="👥 Список пользователей (Админ)"),
        BotCommand(command="add", description="➕ Добавить пользователя (Админ)"),
        BotCommand(command="remove", description="➖ Удалить пользователя (Админ)"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    subs = load_subscribers()
    user_id = message.from_user.id

    if user_id in subs:
        await message.answer(
            f"👋 **Привет, {message.from_user.first_name}!**\n\n"
            f"Ваш аккаунт подключен к рассылке сигналов.\n"
            f"Активных участников: `{len(subs)}/{config.MAX_SUBSCRIBERS}`.\n\n"
            f"Используйте /help для просмотра настроек.",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"👋 **Привет, {message.from_user.first_name}!**\n\n"
            f"Ваш Telegram ID: `{user_id}`\n"
            f"Передайте этот ID администратору бота для добавления.",
            parse_mode="Markdown"
        )


@dp.message(Command("help"))
async def help_handler(message: types.Message):
    help_text = (
        "📖 **Справка по категориям:**\n\n"
        "💧 **До 3 TON** — Бюджетные лоты\n"
        "💎 **3–10 TON** — Средний диапазон\n"
        "🔶 **10–30 TON** — Премиум лоты\n"
        "💎 **50–100 TON** — Крупные лоты\n"
        "🖤 **Чёрный фон** — Редкий фон\n\n"
        "⚙️ **Управление (Админ):**\n"
        "• `/add <USER_ID>` — Добавить ID\n"
        "• `/remove <USER_ID>` — Удалить ID\n"
        "• `/list` — Посмотреть список"
    )
    await message.answer(help_text, parse_mode="Markdown")


@dp.message(Command("status"))
async def status_handler(message: types.Message):
    subs = load_subscribers()
    user_id = message.from_user.id
    admin_flag = "Да" if is_admin(user_id) else "Нет"
    sub_flag = "Активна" if user_id in subs else "Отсутствует"

    status_text = (
        f"🖥 **Статус бота:**\n\n"
        f"• **Ваш ID:** `{user_id}`\n"
        f"• **Подписка:** `{sub_flag}`\n"
        f"• **Права админа:** `{admin_flag}`\n"
        f"• **Участников:** `{len(subs)}/{config.MAX_SUBSCRIBERS}`\n"
        f"• **Мониторинг:** `Работает 🟢`"
    )
    await message.answer(status_text, parse_mode="Markdown")


@dp.message(Command("add"))
async def add_subscriber(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Только администратор может добавлять пользователей.")

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer("⚠️ Использование: `/add USER_ID`", parse_mode="Markdown")

    new_id = int(args[1])
    subs = load_subscribers()

    if new_id in subs:
        return await message.answer("ℹ️ Пользователь уже находится в списке.")

    if len(subs) >= config.MAX_SUBSCRIBERS:
        return await message.answer(f"⚠️ Лимит в {config.MAX_SUBSCRIBERS} человек достигнут!")

    subs.append(new_id)
    save_subscribers(subs)
    await message.answer(f"✅ Пользователь `{new_id}` добавлен! ({len(subs)}/{config.MAX_SUBSCRIBERS})", parse_mode="Markdown")


@dp.message(Command("remove"))
async def remove_subscriber(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Только администратор может удалять пользователей.")

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.answer("⚠️ Использование: `/remove USER_ID`", parse_mode="Markdown")

    remove_id = int(args[1])
    subs = load_subscribers()

    if remove_id not in subs:
        return await message.answer("ℹ️ Пользователь не найден.")

    subs.remove(remove_id)
    save_subscribers(subs)
    await message.answer(f"🗑 Пользователь `{remove_id}` удален! ({len(subs)}/{config.MAX_SUBSCRIBERS})", parse_mode="Markdown")


@dp.message(Command("list"))
async def list_subscribers(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    subs = load_subscribers()
    subs_text = "\n".join([f"• `{uid}`" for uid in subs])
    await message.answer(f"📊 **Подписчики ({len(subs)}/{config.MAX_SUBSCRIBERS}):**\n\n{subs_text}", parse_mode="Markdown")


def categorize_nft(price_ton: float, attributes: dict) -> list[str]:
    categories = []

    if 3.0 <= price_ton <= 10.0:
        categories.append("💎 3–10 TON")
    elif 10.0 < price_ton <= 30.0:
        categories.append("🔶 10–30 TON")
    elif price_ton < 3.0:
        categories.append("💧 До 3 TON")
    elif 50.0 <= price_ton <= 100.0:
        categories.append("💎 50–100 TON")

    bg_color = str(attributes.get("Background", attributes.get("background", ""))).lower()
    if any(color in bg_color for color in ["black", "черный", "#000000", "0x000000"]):
        categories.append("🖤 Чёрный фон")

    return categories


async def broadcast_nft_alert(nft_address: str, price_ton: float):
    try:
        nft_item = await tonapi.nft.get_item_by_address(nft_address)
        metadata = nft_item.metadata or {}
        nft_name = metadata.get("name", "Неизвестный NFT")
        attributes_raw = metadata.get("attributes", [])

        attr_dict = {}
        if isinstance(attributes_raw, list):
            for attr in attributes_raw:
                if isinstance(attr, dict):
                    attr_dict[attr.get("trait_type", "")] = attr.get("value", "")
        elif isinstance(attributes_raw, dict):
            attr_dict = attributes_raw

        categories = categorize_nft(price_ton, attr_dict)

        if categories:
            cat_list_str = "\n".join([f"• {c}" for c in categories])
            nft_link = f"https://getgems.io/nft/{nft_address}"

            text = (
                f"🚨 **Новый лот в сети TON!**\n\n"
                f"🏷 **Название:** `{nft_name}`\n"
                f"💰 **Цена:** `{price_ton:.2f} TON`\n\n"
                f"📌 **Категории:**\n{cat_list_str}"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Открыть лот", url=nft_link)]
            ])

            subscribers = load_subscribers()

            for user_id in subscribers:
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                except Exception as send_err:
                    logging.error(f"Ошибка отправки ID {user_id}: {send_err}")

            logging.info(f"[СИГНАЛ] Отправлено {len(subscribers)} пользователям: {nft_name}")

    except Exception as e:
        logging.error(f"Ошибка парсинга NFT ({nft_address}): {e}")


async def monitor_blockchain():
    logging.info("Слушатель блокчейна TON запущен...")

    while True:
        try:
            tx_data = await tonapi.blockchain.get_account_transactions(
                account_id=config.MARKETPLACE_ADDRESS,
                limit=15
            )

            for tx in reversed(tx_data.transactions):
                tx_hash = tx.hash
                if tx_hash in processed_tx_hashes:
                    continue

                processed_tx_hashes.add(tx_hash)

                if tx.success and tx.in_msg and tx.in_msg.value > 0:
                    price_ton = tx.in_msg.value / 10**9
                    nft_address = tx.in_msg.source.address if tx.in_msg.source else None

                    if nft_address:
                        await broadcast_nft_alert(nft_address.to_raw(), price_ton)

            if len(processed_tx_hashes) > 2000:
                processed_tx_hashes.clear()

        except Exception as e:
            logging.error(f"Ошибка при опросе TonAPI: {e}")

        await asyncio.sleep(config.CHECK_INTERVAL)


async def main():
    await setup_bot_commands()
    logging.info("Бот готов и запущен на Railway.")
    asyncio.create_task(monitor_blockchain())
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
