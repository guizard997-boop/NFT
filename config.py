import os

# Telegram Bot Token от @BotFather
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_BOT_TOKEN_ОТ_BOTFATHER")

# Ключ от TonAPI (https://tonconsole.com)
TONAPI_KEY = os.getenv("TONAPI_KEY", "ВАШ_TONAPI_KEY")

# Главный контракт маркетплейса на TON
MARKETPLACE_ADDRESS = os.getenv(
    "MARKETPLACE_ADDRESS", 
    "EQC2_MRKT_OR_GETGEMS_MARKETPLACE_ADDRESS"
)

# Чтение списков Telegram ID из Railway (передаются через запятую, например: 123456,789012)
def parse_ids_from_env(env_name: str) -> list[int]:
    raw_val = os.getenv(env_name, "")
    if not raw_val:
        return []
    return [int(x.strip()) for x in raw_val.split(",") if x.strip().isdigit()]

# Список ID администраторов (из переменной ADMIN_IDS)
ADMIN_IDS = parse_ids_from_env("ADMIN_IDS")
ADMIN_USER_ID = ADMIN_IDS[0] if ADMIN_IDS else 123456789  # Главный админ

# Разрешенный список пользователей для рассылки (из переменной WHITELIST_IDS)
WHITELIST_IDS = parse_ids_from_env("WHITELIST_IDS")

# Максимальный лимит пользователей
MAX_SUBSCRIBERS = int(os.getenv("MAX_SUBSCRIBERS", "5"))

# Интервал проверки
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "3"))
