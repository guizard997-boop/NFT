import asyncio
import re
import os
from aiohttp import web
from pyrogram import Client, filters
from aiogram import Bot

from config import BOT_TOKEN, API_ID, API_HASH, TARGET_CHAT_ID, HEALTHCHECK_PORT, validate_config

# Валидация конфигурации при запуске
validate_config()

# Инициализация клиентов
app = Client("user_session", api_id=int(API_ID), api_hash=API_HASH)
bot = Bot(token=BOT_TOKEN)

# Чат или каналы для мониторинга
MONITORED_CHATS = ["@nft_stars_market", "@telegram_gifts_trade"]

# Регулярные выражения
STARS_PATTERN = re.compile(r"(\d+)\s*(звёзд|звезд|stars|⭐️|⭐)", re.IGNORECASE)
NFT_PATTERN = re.compile(r"(nft|gift|подарок|пепе|pepe|puro)", re.IGNORECASE)

@app.on_message(filters.chat(MONITORED_CHATS) & filters.text)
async def monitor_gifts_sales(client, message):
    text = message.text
    
    stars_match = STARS_PATTERN.search(text)
    nft_match = NFT_PATTERN.search(text)
    
    if stars_match and nft_match:
        price_stars = stars_match.group(1)
        
        # Получение контакта продавца (@username)
        if message.from_user:
            seller_username = f"@{message.from_user.username}" if message.from_user.username else f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"
        else:
            seller_username = f"@{message.chat.username}" if message.chat.username else message.chat.title

        message_link = message.link if message.link else "Ссылка недоступна"

        caption = (
            f"⭐️ **Найден лот NFT / Telegram Gifts!**\n\n"
            f"👤 **Продавец:** {seller_username}\n"
            f"💰 **Цена:** {price_stars} Telegram Stars ⭐️\n"
            f"📝 **Описание:** {text[:200]}...\n\n"
            f"🔗 [Перейти к объявлению]({message_link})"
        )

        await bot.send_message(
            chat_id=TARGET_CHAT_ID, 
            text=caption, 
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

# Web-сервер для Railway Health Check
async def handle_healthcheck(request):
    return web.Response(text="OK", status=200)

async def start_healthcheck_server():
    server = web.Application()
    server.router.add_get('/', handle_healthcheck)
    server.router.add_get('/health', handle_healthcheck)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', HEALTHCHECK_PORT)
    await site.start()
    print(f"Healthcheck сервер запущен на порту {HEALTHCHECK_PORT}")

async def main():
    await start_healthcheck_server()
    await app.start()
    print("Парсер Telegram Stars & Gifts успешно запущен на Railway!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
