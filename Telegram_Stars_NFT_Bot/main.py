import re
import asyncio
from pyrogram import Client, filters
from aiogram import Bot, Dispatcher, types

# Конфигурация API Telegram
API_ID = 1234567               # Получить на my.telegram.org
API_HASH = "your_api_hash"     # Получить на my.telegram.org
BOT_TOKEN = "your_bot_token"   # Токен вашего бота от @BotFather
TARGET_CHAT_ID = -100123456789 # ID вашего канала/чата, куда бот будет слать уведомления

# Чат или каналы, где ищем объявления о продаже NFT/Gifts за звёзды
MONITORED_CHATS = ["@nft_stars_market", "@telegram_gifts_trade"]

# Инициализация клиентов
app = Client("user_session", api_id=API_ID, api_hash=API_HASH)
bot = Bot(token=BOT_TOKEN)

# Регулярное выражение для поиска упоминаний Telegram Stars и NFT/Gifts
STARS_PATTERN = re.compile(r"(\d+)\s*(звёзд|звезд|stars|⭐️|⭐)", re.IGNORECASE)
NFT_PATTERN = re.compile(r"(nft|gift|подарок|пепе|pepe|puro)", re.IGNORECASE)

@app.on_message(filters.chat(MONITORED_CHATS) & filters.text)
async def monitor_gifts_sales(client, message):
    text = message.text
    
    # Проверяем, есть ли в сообщении упоминания NFT/Gifts и цены в Stars
    stars_match = STARS_PATTERN.search(text)
    nft_match = NFT_PATTERN.search(text)
    
    if stars_match and nft_match:
        price_stars = stars_match.group(1)
        
        # Определение Username или контактов продавца
        if message.from_user:
            seller_username = f"@{message.from_user.username}" if message.from_user.username else f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"
        else:
            # Если сообщение отправлено от имени канала
            seller_username = f"@{message.chat.username}" if message.chat.username else message.chat.title

        # Ссылка на исходное сообщение
        message_link = message.link if message.link else "Ссылка недоступна"

        # Формирование уведомления
        caption = (
            f"⭐️ **Найден лот NFT / Telegram Gifts!**\n\n"
            f"👤 **Продавец:** {seller_username}\n"
            f"💰 **Цена:** {price_stars} Telegram Stars ⭐️\n"
            f"📝 **Описание:** {text[:200]}...\n\n"
            f"🔗 [Перейти к объявлению]({message_link})"
        )

        # Отправка уведомления в целевой канал/чат
        await bot.send_message(
            chat_id=TARGET_CHAT_ID, 
            text=caption, 
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

async def main():
    await app.start()
    print("Парсер Telegram Stars & Gifts запущен...")
    # Держим клиент активным
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
