import os

def _ids(v):
    if not v:
        return []
    v = str(v).strip().strip("[]")
    return [int(x.strip()) for x in v.split(",") if x.strip().lstrip("-").isdigit()]

def _norm_session(s: str) -> str:
    s = (s or "").strip().strip('"').strip("'")
    return "".join(s.split())

def _int_env(name: str, default: int = 0) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except ValueError:
        return default

def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except ValueError:
        return default

_DEFAULT_BOT = os.getenv("BOT_TOKEN", "8925444240:AAHwFeBYekzt4IsLj3rsK9HvG5vGt9AK0jI")
_DEFAULT_ADMINS = os.getenv("ADMIN_IDS", "6429739316,8298834738")
_DEFAULT_WHITELIST = os.getenv("WHITELIST_IDS", "6429739316,8298834738,8796645389")

class S:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN", _DEFAULT_BOT)
        self.admin_ids = _ids(os.getenv("ADMIN_IDS", _DEFAULT_ADMINS))
        self.whitelist_ids = _ids(os.getenv("WHITELIST_IDS", _DEFAULT_WHITELIST))
        self.poll_interval = int(os.getenv("POLL_INTERVAL", "5"))
        self.send_interval = max(1, int(os.getenv("SEND_INTERVAL", "5")))
        self.api_id = int(os.getenv("API_ID", "0") or 0)
        self.api_hash = (os.getenv("API_HASH") or "").strip()
        self.session_string = _norm_session(os.getenv("SESSION_STRING") or "")
        self.min_stars = int(os.getenv("MIN_STARS", "1"))
        self.max_stars = int(os.getenv("MAX_STARS", "0"))

        # курс Stars → TON (для категорий как в Tracker)
        self.stars_to_ton = _float_env("STARS_TO_TON", 0.0093)

        # группа-форум (например -1001234567890). 0 = не слать в группу
        self.group_id = _int_env("GROUP_ID", 0)

        # ID топиков (message_thread_id). 0 = тема не настроена
        self.topic_under_3 = _int_env("TOPIC_UNDER_3", 0)      # 💧 До 3 TON
        self.topic_3_10 = _int_env("TOPIC_3_10", 0)            # 💎 3–10 TON
        self.topic_10_30 = _int_env("TOPIC_10_30", 0)          # 🔶 10–30 TON
        self.topic_30_50 = _int_env("TOPIC_30_50", 0)          # 🔶 30–50 TON
        self.topic_50_100 = _int_env("TOPIC_50_100", 0)        # 💎 50–100 TON
        self.topic_100_plus = _int_env("TOPIC_100_PLUS", 0)    # 👑 100+ TON
        self.topic_black = _int_env("TOPIC_BLACK", 0)          # 🖤 Чёрный фон (если будет признак)

        # слать также в ЛС админам/whitelist: 1/0
        self.dm_enabled = os.getenv("DM_ENABLED", "1").strip() not in ("0", "false", "no")

settings = S()
