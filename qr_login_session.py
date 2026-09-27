"""
Вход в Telegram по QR без SMS.
1) Создаёт QR-картинку
2) Ждёт скана
3) Печатает SESSION_STRING
"""
import asyncio
import os
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession

# --- твои данные ---
API_ID = int(os.getenv("API_ID", "34757056"))
API_HASH = os.getenv("API_HASH", "9145b7ffd164786c47c3af0e42d1be9c")

# куда сохранить QR
OUT_DIR = Path("/storage/emulated/0/Download")  # Android / Pydroid
if not OUT_DIR.exists():
    OUT_DIR = Path.home() / "Download"
if not OUT_DIR.exists():
    OUT_DIR = Path(".")

QR_PATH = OUT_DIR / "telegram_qr.png"
SESSION_PATH = OUT_DIR / "session_string.txt"


def save_qr_image(url: str, path: Path) -> None:
    try:
        import qrcode
    except ImportError:
        print("Ставлю qrcode...")
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "qrcode[pil]", "-q"])
        import qrcode

    img = qrcode.make(url)
    img.save(path)
    print(f"QR сохранён: {path}")


async def main():
    print("API_ID:", API_ID)
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        s = client.session.save()
        print("Уже авторизован. SESSION_STRING:")
        print(s)
        SESSION_PATH.write_text(s, encoding="utf-8")
        print("Сохранено:", SESSION_PATH)
        await client.disconnect()
        return

    qr = await client.qr_login()
    print("URL:", qr.url)
    save_qr_image(qr.url, QR_PATH)
    print()
    print("Открой файл с QR и отсканируй в Telegram:")
    print("  Настройки → Устройства → Подключить устройство")
    print(f"  Файл: {QR_PATH}")
    print("Жду скана (до 2 мин)...")

    try:
        await qr.wait(timeout=120)
    except Exception as e:
        print("Таймаут/ошибка:", e)
        print("Обновляю QR...")
        qr = await qr.recreate()
        print("URL:", qr.url)
        save_qr_image(qr.url, QR_PATH)
        print("Отсканируй НОВЫЙ QR:", QR_PATH)
        await qr.wait(timeout=120)

    s = client.session.save()
    print()
    print("=== SESSION_STRING ===")
    print(s)
    print("LEN:", len(s))
    print("======================")
    SESSION_PATH.write_text(s, encoding="utf-8")
    print("Сохранено в:", SESSION_PATH)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
