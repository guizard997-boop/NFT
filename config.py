import os

def _ids(v):
    if not v:
        return []
    v = str(v).strip().strip("[]")
    return [int(x.strip()) for x in v.split(",") if x.strip().lstrip("-").isdigit()]

_DEFAULT_BOT = "8793921623:AAEl76MKZMDyoJGNTvXeqGdAwQ15So7MBgg"
_DEFAULT_ADMINS = "6429739316,8298834738"
_DEFAULT_WHITELIST = "6429739316,8298834738"

def _norm_session(s: str) -> str:
    """Только пробелы/переносы/кавычки. Padding НЕ трогаем — Telethon сам разберёт."""
    s = (s or "").strip().strip('"').strip("'")
    s = "".join(s.split())  # убрать \n \r пробелы
    return s

class S:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN", _DEFAULT_BOT)
        self.admin_ids = _ids(os.getenv("ADMIN_IDS", _DEFAULT_ADMINS))
        self.whitelist_ids = _ids(os.getenv("WHITELIST_IDS", _DEFAULT_WHITELIST))
        self.poll_interval = int(os.getenv("POLL_INTERVAL", "25"))
        self.api_id = int(os.getenv("API_ID", "0") or 0)
        self.api_hash = os.getenv("API_HASH", "").strip()
        self.session_string = _norm_session(os.getenv("SESSION_STRING", ""))
        self.min_stars = int(os.getenv("MIN_STARS", "1"))
        self.max_stars = int(os.getenv("MAX_STARS", "0"))

settings = S()
