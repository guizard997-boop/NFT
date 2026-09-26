# Telegram Stars & Gifts NFT Tracker (Railway Ready)

Бот для автоматического поиска и отслеживания лотов NFT / Telegram Gifts, продаваемых за **Telegram Stars** с выводом `@username` продавца.

## Переменные окружения в Railway:

Добавьте в разделе **Variables** проекта на Railway:
- `BOT_TOKEN` — Токен бота от @BotFather.
- `API_ID` — API ID с сайта my.telegram.org.
- `API_HASH` — API Hash с сайта my.telegram.org.
- `TARGET_CHAT_ID` — ID канала или чата для отправки уведомлений.
- `HEALTHCHECK_PORT` — Порт для пробы (по умолчанию используется переменная `PORT` от Railway).
