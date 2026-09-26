"""Один раз: создать SESSION_STRING для доступа к маркету Stars."""
import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

async def main():
    if not API_ID or not API_HASH:
        print("Задай API_ID и API_HASH (my.telegram.org)")
        print("  export API_ID=12345")
        print("  export API_HASH=abcdef...")
        return
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start()
    s = client.session.save()
    print("\n=== SESSION_STRING (скопируй в Variables) ===\n")
    print(s)
    print("\n=============================================\n")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
