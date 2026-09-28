import os

def _ids(v):
    if not v:
        return []
    v = str(v).strip().strip("[]")
    return [int(x.strip()) for x in v.split(",") if x.strip().lstrip("-").isdigit()]

_DEFAULT_BOT = "8925444240:AAHwFeBYekzt4IsLj3rsK9HvG5vGt9AK0jI"
_DEFAULT_ADMINS = "6429739316,8298834738"
_DEFAULT_WHITELIST = "6429739316,8298834738"
_DEFAULT_API_ID = "35910670"
_DEFAULT_API_HASH = "f99cb3c0aeb9ac1f34ee9473fb5c6123"
_DEFAULT_SESSION = "1ApWapzMBu5uatRSDVHK1LWEJujnC1x9ld1RpxnovzwB5SZOTadI2LC_aRZGFXjv0ILg-104K2lMKWZT4G-WQMPnAVP2uyvbeM0WJd-aFPKWIE6_KHsiIEmFXWqjZwUpVZk-5-ojm7qp_xndyVWt_9dj4VyJC9XWpdpekMaK3Nat26Ay5w0-ZiiIBQGImzzJ51r9HFkPRE9BXYDkglHOKMDuYcME2rU7uIBsRhq4gYt9VHSv0jYNXFWR9S62t-ptzsSUWu7HBP7kx6i2qKq48PzQD8SP02w1UESRomgpqMdl682KKxYQ-R-IOEyEWoAJdSAyf5AS0udIsHj-mRjWx8WSf51q2tY8=
"

def _norm_session(s: str) -> str:
    s = (s or "").strip().strip('"').strip("'")
    return "".join(s.split())

class S:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN", _DEFAULT_BOT)
        self.admin_ids = _ids(os.getenv("ADMIN_IDS", _DEFAULT_ADMINS))
        self.whitelist_ids = _ids(os.getenv("WHITELIST_IDS", _DEFAULT_WHITELIST))
        self.poll_interval = int(os.getenv("POLL_INTERVAL", "5"))
        self.api_id = int(os.getenv("API_ID", _DEFAULT_API_ID) or 0)
        self.api_hash = os.getenv("API_HASH", _DEFAULT_API_HASH).strip()
        self.session_string = _norm_session(os.getenv("SESSION_STRING", _DEFAULT_SESSION))
        self.min_stars = int(os.getenv("MIN_STARS", "1"))
        self.max_stars = int(os.getenv("MAX_STARS", "0"))

settings = S()
