import os

def _ids(v):
    if not v:
        return []
    v = str(v).strip().strip("[]")
    return [int(x.strip()) for x in v.split(",") if x.strip().lstrip("-").isdigit()]

def _norm_session(s: str) -> str:
    s = (s or "").strip().strip('"').strip("'")
    return "".join(s.split())

# Всё чувствительное — только из Railway Variables (без хардкода сессии)
_DEFAULT_BOT = os.getenv("BOT_TOKEN", "8925444240:AAHwFeBYekzt4IsLj3rsK9HvG5vGt9AK0jI")
_DEFAULT_ADMINS = os.getenv("ADMIN_IDS", "6429739316,8298834738")
_DEFAULT_WHITELIST = os.getenv("WHITELIST_IDS", "6429739316,8298834738")

class S:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN", _DEFAULT_BOT)
        self.admin_ids = _ids(os.getenv("ADMIN_IDS", _DEFAULT_ADMINS))
        self.whitelist_ids = _ids(os.getenv("WHITELIST_IDS", _DEFAULT_WHITELIST))
        self.poll_interval = int(os.getenv("POLL_INTERVAL", "5"))
        # пауза между уведомлениями (анти-flood), секунды
        self.send_interval = max(1, int(os.getenv("SEND_INTERVAL", "5")))
        self.api_id = int(os.getenv("API_ID", "0") or 0)
        self.api_hash = (os.getenv("API_HASH") or "").strip()
        self.session_string = _norm_session(os.getenv("SESSION_STRING") or "")
        self.min_stars = int(os.getenv("MIN_STARS", "1"))
        self.max_stars = int(os.getenv("MAX_STARS", "0"))

settings = S()
