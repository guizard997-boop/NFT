from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from typing import List, Any


def parse_id_list(value: Any) -> List[int]:
    """Надёжно парсит ID из строки, списка или числа."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        result = []
        for x in value:
            if isinstance(x, int):
                result.append(x)
            elif isinstance(x, str) and x.strip().lstrip("-").isdigit():
                result.append(int(x.strip()))
        return result
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.startswith("[") and cleaned.endswith("]"):
            cleaned = cleaned[1:-1]
        parts = [p.strip().strip('"').strip("'") for p in cleaned.split(",")]
        return [int(p) for p in parts if p and p.lstrip("-").isdigit()]
    raise ValueError(f"Не могу распарсить список ID: {value!r}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    bot_token: str = Field(..., validation_alias="BOT_TOKEN")
    admin_ids_raw: str = Field(default="", validation_alias="ADMIN_IDS")
    whitelist_ids_raw: str = Field(default="", validation_alias="WHITELIST_IDS")
    getgems_api_key: str = Field(default="", validation_alias="GETGEMS_API_KEY")
    poll_interval: int = Field(default=25, validation_alias="POLL_INTERVAL")
    max_age_seconds: int = Field(default=60, validation_alias="MAX_AGE_SECONDS")

    # Мутабельные списки (можно менять командами /add_user и /remove_user)
    admin_ids: List[int] = []
    whitelist_ids: List[int] = []

    @model_validator(mode="after")
    def fill_id_lists(self):
        self.admin_ids = parse_id_list(self.admin_ids_raw)
        self.whitelist_ids = parse_id_list(self.whitelist_ids_raw)
        return self


settings = Settings()