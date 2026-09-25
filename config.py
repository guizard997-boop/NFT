import os
from typing import List


def parse_ids(value: str | None) -> List[int]:
    if not value:
        return []
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    result = []
    for part in value.split(","):
        part = part.strip().strip('"').strip("'")
        if part and part.lstrip("-").isdigit():
            result.append(int(part))
    return result


class Settings:
    def __init__(self):
        self.bot_token: str = os.getenv("BOT_TOKEN", "")
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is required")

        self.admin_ids: List[int] = parse_ids(os.getenv("ADMIN_IDS", ""))
        self.whitelist_ids: List[int] = parse_ids(os.getenv("WHITELIST_IDS", ""))
        self.getgems_api_key: str = os.getenv("GETGEMS_API_KEY", "")
        self.poll_interval: int = int(os.getenv("POLL_INTERVAL", "25"))
        self.max_age_seconds: int = int(os.getenv("MAX_AGE_SECONDS", "60"))


settings = Settings()