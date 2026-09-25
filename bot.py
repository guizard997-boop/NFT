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

DB_FILE = "subscribers.json"
processed_tx_hashes = set()


def load_subscribers() -> list[int]:
    """Загружает список подписчиков."""
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
    """Сохраняет список ID подписчиков."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения в {DB_FILE}: {e}")


def is_admin(user_id: int) -> bool:
    if config.ADMIN_IDS:
        return user_id in config.ADMIN_IDS
    return user_id == config.ADMIN_USER_ID


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    subs = load_subscribers()
    user_id = message.from_user.id

    if user_id in subs:
        await message.answer(
            f"🔥 **Максимальный поток включен!**\n\n"
            f"Вам будут приходить **ВСЕ** транзакции и лоты без фильтров.",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"👋 Ваш Telegram ID: `{user_id}`\n"
            f"Добавьте его через /add или в Railway.",
            parse_mode="Markdown"
        )


async def broadcast_nft_alert(nft_address: str, price_ton: float):
    """Отправляет сигнал БЕЗ ФИЛЬТРОВ."""
    try:
        nft_item = await tonapi.nft.get_item_by_address(nft_address)
        metadata = nft_item.metadata or {}
        nft_name = metadata.get("name", "Лот / NFT")

        nft_link = f"https://getgems.io/nft/{nft_address}"

        text = (
            f"⚡️ **НОВЫЙ ЛОТ / ТРАНЗАКЦИЯ!**\n\n"
            f"🏷 **Название:** `{nft_name}`\n"
            f"💰 **Цена:** `{price_ton:.2f} TON`\n"
            f"📍 **Адрес:** `{nft_address}`"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Открыть на Getgems", url=nft_link)]
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

        logging.info(f"[СПАМ-СИГНАЛ] Отправлено: {nft_name} ({price_ton} TON)")

    except Exception as e:
        logging.error(f"Ошибка парсинга NFT ({nft_address}): {e}")


async def monitor_blockchain():
    logging.info("Слушатель блокчейна запущен в МАКСИМАЛЬНОМ режиме...")

    while True:
        try:
            # Забираем 50 последних транзакций за один раз
            tx_data = await tonapi.blockchain.get_account_transactions(
                account_id=config.MARKETPLACE_ADDRESS,
                limit=50
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
                        # Отправляем ВСЁ подряд
                        await broadcast_nft_alert(nft_address.to_raw(), price_ton)

            if len(processed_tx_hashes) > 5000:
                processed_tx_hashes.clear()

        except Exception as e:
            logging.error(f"Ошибка при опросе TonAPI: {e}")

        # Проверка каждую 1 секунду
        await asyncio.sleep(1)


async def main():
    logging.info("Бот запущен.")
    asyncio.create_task(monitor_blockchain())
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Остановлен.")
