# ⭐ Stars Gift Tracker

Бот ловит **NFT-подарки Telegram, выставленные за Stars** на официальном маркете, и шлёт:
- название и номер
- цену в ⭐
- username / имя продавца
- ссылку `t.me/nft/...`

## 1. Что нужно

| Переменная | Где взять |
|------------|-----------|
| `BOT_TOKEN` | уже вшит (@treckernft_bot) |
| `API_ID` | https://my.telegram.org → API development tools |
| `API_HASH` | там же |
| `SESSION_STRING` | скрипт `login.py` (один раз) |

Админы уже вшиты: `6429739316`, `8298834738`.

## 2. Локальная установка

```bash
pip install -r requirements.txt

# один раз — сессия user-аккаунта
export API_ID=12345678
export API_HASH=your_api_hash
python login.py
# скопируй SESSION_STRING

export SESSION_STRING='...'
python bot.py
```

## 3. Railway

Variables:
```
API_ID=...
API_HASH=...
SESSION_STRING=...
POLL_INTERVAL=25
```

Deploy → `python bot.py` (Procfile уже есть).

## 4. Команды

`/start` `/status` `/pause` `/resume` `/help`  
Админ: `/users` `/add_user ID` `/remove_user ID`

## Важно

- Маркет **Stars** доступен только через **user-сессию** (не bot token).
- Аккаунт для `SESSION_STRING` лучше отдельный (не основной).
- Официальный API: `payments.getResaleStarGifts` + `stars_only`.
