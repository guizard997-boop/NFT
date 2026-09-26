import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Telegram ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# --- TonAPI ---
# Ключ не обязателен, но снимает жёсткие лимиты на запросы.
# Получить можно на https://tonconsole.com
TONAPI_KEY = os.getenv("TONAPI_KEY", "")
TONAPI_BASE_URL = "https://tonapi.io/v2"

# Адреса коллекций NFT для мониторинга, через запятую в .env:
# NFT_COLLECTIONS=EQxxxxx...,EQyyyyy...
NFT_COLLECTIONS = [
    addr.strip()
    for addr in os.getenv("NFT_COLLECTIONS", "").split(",")
    if addr.strip()
]

# Как часто опрашивать TonAPI (в секундах)
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "20"))

# Сколько событий запрашивать за один опрос каждой коллекции
EVENTS_LIMIT = int(os.getenv("EVENTS_LIMIT", "20"))

# --- Health check веб-сервер (для Railway / Render и т.п.) ---
HEALTHCHECK_PORT = int(os.getenv("PORT", "8080"))

# --- Getgems ---
GETGEMS_NFT_URL = "https://getgems.io/nft/{address}"

# --- Файлы хранения данных ---
SUBSCRIBERS_FILE = os.path.join("data", "subscribers.json")
STATE_FILE = os.path.join("data", "state.json")
