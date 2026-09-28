import os

def _ids(v):
    if not v:
        return []
    v = str(v).strip().strip("[]")
    return [int(x.strip()) for x in v.split(",") if x.strip().lstrip("-").isdigit()]

_DEFAULT_BOT = "8793921623:AAFRMZExSs_bekpOuE4b77acEsDw0mSf70I"
_DEFAULT_ADMINS = "6429739316,8298834738"
_DEFAULT_WHITELIST = "6429739316,8298834738"
_DEFAULT_API_ID = "35910670"
_DEFAULT_API_HASH = "f99cb3c0aeb9ac1f34ee9473fb5c6123"
_DEFAULT_SESSION = "1ApWapzMBu8OTC2bD-xCLaKHcBoqpC-J2GaNwMB9h42R37Q6vGsdeGYtJhpAdCfpRcMUegJdHiBv6Ju-SS-8kUMmBYl3yA4BFVjuDz4AThpXWQuJkmON15L_vgH-8vlH6UVkIO3PvKYPVTT72G515q_rqY3Llgdk5HDNfthSkeXr0hekPSY4d_MZea0YtvZiKctdX2D_TU4rPkxwsEuNv16W00km9UcUk2T8vu7mUN0jfmbRuLGiFuqWUW40EY0Kd72sYCl_0OBzwtTwVfm8snWimsJG6-o4nJPg2Ktm1irH2eih4WWhJysyH9ozxcX-I99N8wMp51x_rNww-ShV3ndNcFIvJZ3o="

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