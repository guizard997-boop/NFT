import os

def _ids(v):
    if not v:
        return []
    v = str(v).strip().strip("[]")
    return [int(x.strip()) for x in v.split(",") if x.strip().lstrip("-").isdigit()]

# === ВШИТО (env может переопределить) ===
_DEFAULT_BOT = "8793921623:AAEl76MKZMDyoJGNTvXeqGdAwQ15So7MBgg"
_DEFAULT_ADMINS = "6429739316,8298834738"
_DEFAULT_WHITELIST = "6429739316,8298834738"
_DEFAULT_API_ID = "34757056"
_DEFAULT_API_HASH = "9145b7ffd164786c47c3af0e42d1be9c"
_DEFAULT_SESSION = """1ApWapzMBu1-Qdm8YXt0gIXAQotw_LGoN3gZA44I9tPCFLu02z_Tw0HDp7A2UOsmH1AtdB1KMIR3KSJ2euw60nABW7a_mA1r-MF3fNQdSFLcLnVF2MNNIhPEYLrZ9RowFGCv3jYPC6Iwf05B5OpLaEAtBXJ2REY1hA4Jyvu0w6EkR5unHpMggIWLZQ7-fCwKHi9y62EneDeQ2x1sD5Dw5-PkTKaEf0BkN-U5Hqb_Sw-DVxUozL90HriuM24raed8iwVz7o8a_c-GqeSxKpD60_Wu8Y63D07n13xQwnG6gygZbNZ1LWcm0P5e5tKPu3IVYYRSu_qZAqIdIW7ZFgEtAt3VsdPbTwx8="""

def _norm_session(s: str) -> str:
    s = (s or "").strip().strip('"').strip("'")
    return "".join(s.split())

class S:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN", _DEFAULT_BOT)
        self.admin_ids = _ids(os.getenv("ADMIN_IDS", _DEFAULT_ADMINS))
        self.whitelist_ids = _ids(os.getenv("WHITELIST_IDS", _DEFAULT_WHITELIST))
        self.poll_interval = int(os.getenv("POLL_INTERVAL", "25"))
        self.api_id = int(os.getenv("API_ID", _DEFAULT_API_ID) or 0)
        self.api_hash = os.getenv("API_HASH", _DEFAULT_API_HASH).strip()
        self.session_string = _norm_session(os.getenv("SESSION_STRING", _DEFAULT_SESSION))
        self.min_stars = int(os.getenv("MIN_STARS", "1"))
        self.max_stars = int(os.getenv("MAX_STARS", "0"))

settings = S()
