from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Any


def parse_id_list(value: Any) -> List[int]:
    """Парсит список ID из строки '1,2,3' или уже из списка."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [int(x) for x in value]
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        return [int(x.strip()) for x in value.split(",") if x.strip()]
    raise ValueError(f"Не могу распарсить список ID: {value}")


class Settings(BaseSettings):
    bot_token: str = Field(..., alias="BOT_TOKEN")
    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")
    whitelist_ids: List[int] = Field(default_factory=list, alias="WHITELIST_IDS")
    getgems_api_key: str = Field(default="", alias="GETGEMS_API_KEY")
    poll_interval: int = Field(default=25, alias="POLL_INTERVAL")
    max_age_seconds: int = Field(default=60, alias="MAX_AGE_SECONDS")

    @field_validator("admin_ids", "whitelist_ids", mode="before")
    @classmethod
    def parse_ids(cls, v):
        return parse_id_list(v)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True


settings = Settings()
