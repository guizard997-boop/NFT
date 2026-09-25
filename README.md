# NFT Tracker Bot (Telegram Gifts)

Бот для отслеживания новых листингов Telegram Gifts на **MRKT + Portals + Getgems**.

### Возможности
- Отправляет **только** листинги младше 1 минуты
- Категории:
  - 🖤 Чёрный фон (любая цена)
  - 💧 До 3 TON
  - 💎 3–10 TON
  - 🔶 10–30 TON
  - 💜 50–100 TON
- Whitelist — работает только для разрешённых пользователей
- Команды управления

### Быстрый старт

1. Создай бота у [@BotFather](https://t.me/BotFather) → получи токен
2. Узнай свой Telegram ID (через @userinfobot)
3. Скопируй `.env.example` → `.env` и заполни:

```env
BOT_TOKEN=123456:ABC-...
ADMIN_IDS=ТВОЙ_ID
WHITELIST_IDS=ТВОЙ_ID,ID_ДРУГА
GETGEMS_API_KEY=          # опционально
POLL_INTERVAL=25
MAX_AGE_SECONDS=60
```

4. Установи зависимости и запусти:

```bash
pip install -r requirements.txt
python bot.py
```

### Важно про API маркетов

Сейчас в `fetcher.py` стоит **демо-режим** (генерирует тестовые листинги).

Чтобы получать реальные данные:

1. **Getgems** — получи API key на https://getgems.io/public-api (10 GRAM/мес)
2. **MRKT** — нужен токен через Telegram WebApp (см. репозитории amrkt / boostNT/MRKT-API)
3. **Portals** — аналогично неофициальные клиенты

В `fetcher.py` уже есть заготовки функций `fetch_getgems`, `fetch_mrkt`, `fetch_portals`.

### Команды бота

| Команда | Описание |
|---------|----------|
| /start | Запуск |
| /status | Статус трекера |
| /pause | Пауза |
| /resume | Возобновить |
| /help | Справка |
| /users | Список whitelist (админ) |
| /add_user ID | Добавить пользователя |
| /remove_user ID | Удалить пользователя |

### Пример сообщения

```
🖤 ЧЁРНЫЙ ФОН

🎁 Lunar Snake #109967
💰 Цена: 18.50 TON
🏪 Маркет: MRKT
🎨 Фон: Black
⏱ Выставлен: только что

[🔗 Открыть на маркете]
```
