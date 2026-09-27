"""Один раз: создать SESSION_STRING (только Telethon + телефон/код)."""
import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.getenv("API_ID", "34757056"))
API_HASH = os.getenv("API_HASH", "9145b7ffd164786c47c3af0e42d1be9c")

async def main():
    print("API_ID:", API_ID)
    print("Вход по номеру телефона (не QR сторонних скриптов)...")
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start()
    s = client.session.save()
    # проверка что Telethon сам может прочитать
    try:
        StringSession(s)
        ok = "OK"
    except Exception as e:
        ok = f"FAIL: {e}"
    print("\n=== SESSION_STRING ===")
    print(s)
    print("=== END ===")
    print("Длина:", len(s), "| проверка:", ok)
    print("Скопируй ВСЮ строку между === одной линией в Railway SESSION_STRING")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
