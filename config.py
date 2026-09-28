import os

def _ids(v):
    if not v:
        return []
    v = str(v).strip().strip("[]")
    return [int(x.strip()) for x in v.split(",") if x.strip().lstrip("-").isdigit()]

_DEFAULT_BOT = "8925444240:AAHwFeBYekzt4IsLj3rsK9HvG5vGt9AK0jI"
_DEFAULT_ADMINS = "6429739316,8298834738"
_DEFAULT_WHITELIST = "6429739316,8298834738"
_DEFAULT_API_ID = "34757056"
_DEFAULT_API_HASH = "9145b7ffd164786c47c3af0e42d1be9c"
_DEFAULT_SESSION = "1ApWapzMBu6muVnHqrqkg2OA1ppQF3-Gm0hcKkhtj4v3So0-PIQ6xcdi8nEdpK6WAuO9j18SSxPDEc0A4BbU7m8koQZL2D6YA9_YOwJ8Z1cQh7DrmvQo97CPow127yGjNFRvj9uUbK42iJlM1i8AhvC9JDgmqJSu7c2UaaQAUNYGD6dpL3JjSryJ7v_oSAWxewO557bIAnr7jEyufRppGKhXFsUwmss2jF4GjlEWsiG09xlUS7w_xCXPRBpLvpjmjLUKtoMy4_u-XlwaHUh_uRDnnccfBEcYgNouFwu0yRlTwynHkgqdPTOGlSWc-wlbZceSaA8zLk_5lngDwP9gHGHZuhp6IS4I="

def _norm_session(s: str) -> str:
    s = (s or "").strip().strip('"').strip("'")
    return "".join(s.split())

class S:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN", _DEFAULT_BOT)
        self.admin_ids = _ids(os.getenv("ADMIN_IDS", _DEFAULT_ADMINS))
        self.whitelist_ids = _ids(os.getenv("WHITELIST_IDS", _DEFAULT_WHITELIST))
        self.poll_interval = int(os.getenv("POLL_INTERVAL", "10"))
        self.api_id = int(os.getenv("API_ID", _DEFAULT_API_ID) or 0)
        self.api_hash = os.getenv("API_HASH", _DEFAULT_API_HASH).strip()
        self.session_string = _norm_session(os.getenv("SESSION_STRING", _DEFAULT_SESSION))
        self.min_stars = int(os.getenv("MIN_STARS", "1"))
        self.max_stars = int(os.getenv("MAX_STARS", "0"))

settings = S()
