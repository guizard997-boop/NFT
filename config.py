import os

# Считываем переменные окружения из Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
HEALTHCHECK_PORT = int(os.getenv("HEALTHCHECK_PORT", os.getenv("PORT", "8080")))

def validate_config():
    """Проверка наличия всех необходимых переменных окружения."""
    missing = []
    
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not API_ID:
        missing.append("API_ID")
    if not API_HASH:
        missing.append("API_HASH")
        
    if missing:
        raise ValueError(
            f"❌ Ошибка конфигурации! Отсутствуют обязательные переменные окружения в Railway: {', '.join(missing)}"
        )
