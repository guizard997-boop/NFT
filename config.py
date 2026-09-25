import os

def _ids(v):
    if not v:
        return []
    v = str(v).strip().strip("[]")
    return [int(x.strip()) for x in v.split(",") if x.strip().lstrip("-").isdigit()]

# Вшитые значения (можно переопределить через env)
_DEFAULT_TOKEN = "8793921623:AAEl76MKZMDyoJGNTvXeqGdAwQ15So7MBgg"
_DEFAULT_ADMINS = "6429739316,8298834738"
_DEFAULT_WHITELIST = "6429739316,8298834738"

class S:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN", _DEFAULT_TOKEN)
        self.admin_ids = _ids(os.getenv("ADMIN_IDS", _DEFAULT_ADMINS))
        self.whitelist_ids = _ids(os.getenv("WHITELIST_IDS", _DEFAULT_WHITELIST))
        self.poll_interval = int(os.getenv("POLL_INTERVAL", "20"))
        self.max_age_seconds = int(os.getenv("MAX_AGE_SECONDS", "60"))
        self.mrkt_token = os.getenv("MRKT_TOKEN", "").strip()
        self.getgems_token = os.getenv("GETGEMS_TOKEN", "").strip()

settings = S()
