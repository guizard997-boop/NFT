"""
Трекер NFT-подарков Telegram, выставленных ЗА ЗВЁЗДЫ (официальный resale market).
Источник: payments.getResaleStarGifts (stars_only).
"""
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.payments import GetResaleStarGiftsRequest
from telethon.tl import types as tl

from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("stars-bot")

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
paused = False
stats = {"n": 0, "last": None}
seen: set[str] = set()
user_client: TelegramClient | None = None

def ok(uid: int) -> bool:
    return uid in settings.whitelist_ids or uid in settings.admin_ids

def adm(uid: int) -> bool:
    return uid in settings.admin_ids

async def broadcast(text: str, kb=None):
    targets = set(settings.whitelist_ids) | set(settings.admin_ids)
    for uid in targets:
        try:
            await bot.send_message(uid, text, parse_mode=ParseMode.HTML, reply_markup=kb, disable_web_page_preview=False)
        except Exception as e:
            log.warning("send %s: %s", uid, e)

def fmt_item(item: dict) -> tuple[str, InlineKeyboardMarkup | None]:
    stars = item["stars"]
    name = item["name"]
    num = item.get("num")
    seller = item.get("seller") or "—"
    slug = item.get("slug") or ""
    link = item.get("link") or (f"https://t.me/nft/{slug}" if slug else "https://t.me/")

    title = f"{name}" + (f" #{num}" if num else "")
    text = (
        f"⭐ <b>ПРОДАЖА ЗА STARS</b>\n\n"
        f"🎁 <b>{title}</b>\n"
        f"💰 Цена: <b>{stars}</b> ⭐\n"
        f"👤 Продавец: {seller}\n"
        f"🔗 <a href=\"{link}\">Открыть подарок</a>\n"
        f"⏱ Только что на маркете Telegram"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Открыть в Telegram", url=link)]
    ])
    return text, kb

# ---- commands ----
@dp.message(Command("start"))
async def c_start(m: Message):
    if not ok(m.from_user.id):
        return await m.answer("⛔ Нет доступа.")
    await m.answer(
        "Бека шлююююха\n\n"
        "⭐ <b>Stars Gift Tracker</b>\n"
        "Только подарки за <b>Telegram Stars</b> на официальном маркете.\n"
        "Шлёт: название, цену ⭐, продавца, ссылку.\n\n"
        "/status · /help",
        parse_mode=ParseMode.HTML,
    )

@dp.message(Command("help"))
async def c_help(m: Message):
    if not ok(m.from_user.id):
        return
    t = "/start /status /pause /resume /help"
    if adm(m.from_user.id):
        t += "\nАдмин: /users /add_user ID /remove_user ID"
    await m.answer(t)

@dp.message(Command("status"))
async def c_status(m: Message):
    if not ok(m.from_user.id):
        return
    st = "⏸ пауза" if paused else "🟢 работает"
    last = stats["last"].strftime("%H:%M:%S") if stats["last"] else "—"
    mt = "user-session OK" if (user_client and user_client.is_connected()) else "нет сессии"
    await m.answer(
        f"{st}\nМаркет Stars: {mt}\nОтправлено: {stats['n']}\nПоследнее: {last}\nИнтервал: {settings.poll_interval}с"
    )

@dp.message(Command("pause"))
async def c_pause(m: Message):
    if not ok(m.from_user.id):
        return
    global paused
    paused = True
    await m.answer("⏸ Пауза")

@dp.message(Command("resume"))
async def c_resume(m: Message):
    if not ok(m.from_user.id):
        return
    global paused
    paused = False
    await m.answer("▶️ Работает")

@dp.message(Command("users"))
async def c_users(m: Message):
    if not adm(m.from_user.id):
        return await m.answer("Только админ")
    await m.answer(
        f"Whitelist:\n<code>{settings.whitelist_ids}</code>\nAdmins:\n<code>{settings.admin_ids}</code>",
        parse_mode=ParseMode.HTML,
    )

@dp.message(Command("add_user"))
async def c_add(m: Message, command: CommandObject):
    if not adm(m.from_user.id):
        return
    try:
        uid = int(command.args.strip())
        if uid not in settings.whitelist_ids:
            settings.whitelist_ids.append(uid)
            await m.answer(f"✅ {uid}")
        else:
            await m.answer("Уже есть")
    except Exception:
        await m.answer("/add_user ID")

@dp.message(Command("remove_user"))
async def c_rm(m: Message, command: CommandObject):
    if not adm(m.from_user.id):
        return
    try:
        uid = int(command.args.strip())
        if uid in settings.whitelist_ids:
            settings.whitelist_ids.remove(uid)
            await m.answer(f"✅ удалён {uid}")
        else:
            await m.answer("Нет в списке")
    except Exception:
        await m.answer("/remove_user ID")

# ---- Telegram Stars marketplace ----
async def ensure_user_client() -> TelegramClient | None:
    global user_client
    if user_client and user_client.is_connected():
        return user_client
    if not settings.api_id or not settings.api_hash or not settings.session_string:
        log.warning("Нет API_ID / API_HASH / SESSION_STRING — маркет Stars недоступен")
        return None
    user_client = TelegramClient(
        StringSession(settings.session_string),
        settings.api_id,
        settings.api_hash,
    )
    await user_client.connect()
    if not await user_client.is_user_authorized():
        log.error("SESSION_STRING невалидна")
        return None
    log.info("Telethon session connected")
    return user_client

def _stars_amount(obj) -> int | None:
    """Достать число Stars из разных типов TL."""
    if obj is None:
        return None
    if isinstance(obj, int):
        return obj
    # StarsAmount / starsAmount
    amount = getattr(obj, "amount", None)
    if amount is not None:
        try:
            return int(amount)
        except Exception:
            pass
    if hasattr(obj, "stars"):
        try:
            return int(obj.stars)
        except Exception:
            pass
    return None

def _parse_gift(g) -> dict | None:
    """Разобрать starGiftUnique / resale gift в dict."""
    # Telethon объекты: starGiftUnique и обёртки resale
    gift = g
    if hasattr(g, "gift"):
        gift = g.gift

    gid = str(getattr(gift, "id", None) or getattr(g, "id", None) or "")
    if not gid:
        return None

    name = getattr(gift, "title", None) or getattr(gift, "name", None) or "Gift"
    num = getattr(gift, "num", None)
    slug = getattr(gift, "slug", None) or ""

    # цена в stars
    stars = None
    for attr in ("resell_stars", "resale_stars", "stars", "resell_amount", "amount"):
        v = getattr(gift, attr, None) or getattr(g, attr, None)
        s = _stars_amount(v)
        if s is not None and s > 0:
            stars = s
            break
    # resell_amount может быть списком StarsAmount
    ra = getattr(gift, "resell_amount", None) or getattr(g, "resell_amount", None)
    if stars is None and ra is not None:
        if isinstance(ra, (list, tuple)):
            for x in ra:
                s = _stars_amount(x)
                if s:
                    stars = s
                    break
        else:
            stars = _stars_amount(ra)

    if not stars or stars <= 0:
        return None
    if stars < settings.min_stars:
        return None
    if settings.max_stars and stars > settings.max_stars:
        return None

    # продавец
    seller = "—"
    owner = getattr(gift, "owner_id", None) or getattr(g, "owner_id", None)
    owner_name = getattr(gift, "owner_name", None) or getattr(g, "owner_name", None)
    owner_addr = getattr(gift, "owner_address", None)
    if owner_name:
        seller = f"@{owner_name}" if not str(owner_name).startswith("@") else str(owner_name)
    elif owner is not None:
        # PeerUser / int
        uid = getattr(owner, "user_id", None) or getattr(owner, "channel_id", None) or owner
        seller = f"id:{uid}"
    elif owner_addr:
        seller = str(owner_addr)[:16] + "…"

    link = f"https://t.me/nft/{slug}" if slug else f"https://t.me/"

    return {
        "id": f"stars-{gid}-{num or 0}-{stars}",
        "name": str(name),
        "num": num,
        "stars": int(stars),
        "seller": seller,
        "slug": slug,
        "link": link,
    }

async def fetch_stars_listings(client: TelegramClient) -> list[dict]:
    """Тянем resale подарки только за Stars."""
    out: list[dict] = []
    try:
        # gift_id=0 часто = все типы; offset пагинация
        # flags: stars_only
        result = await client(GetResaleStarGiftsRequest(
            gift_id=0,
            offset="",
            limit=50,
            stars_only=True,
        ))
    except TypeError:
        # старая telethon без stars_only — пробуем без флага и фильтруем сами
        try:
            result = await client(GetResaleStarGiftsRequest(
                gift_id=0,
                offset="",
                limit=50,
            ))
        except Exception as e:
            log.warning("GetResaleStarGifts: %s", e)
            return []
    except Exception as e:
        log.warning("GetResaleStarGifts: %s", e)
        return []

    gifts = getattr(result, "gifts", None) or getattr(result, "resale_gifts", None) or []
    users = {u.id: u for u in (getattr(result, "users", None) or [])}

    for g in gifts:
        item = _parse_gift(g)
        if not item:
            continue
        # обогатить продавца из users
        owner = getattr(getattr(g, "gift", g), "owner_id", None)
        if owner is not None:
            uid = getattr(owner, "user_id", None) or (owner if isinstance(owner, int) else None)
            if uid and uid in users:
                u = users[uid]
                uname = getattr(u, "username", None)
                if uname:
                    item["seller"] = f"@{uname}"
                else:
                    fn = (getattr(u, "first_name", "") or "") + " " + (getattr(u, "last_name", "") or "")
                    item["seller"] = fn.strip() or f"id:{uid}"
        out.append(item)
    return out

async def tracker_loop():
    log.info("Stars tracker starting…")
    while True:
        try:
            if not paused:
                client = await ensure_user_client()
                if client:
                    items = await fetch_stars_listings(client)
                    for x in items:
                        if x["id"] in seen:
                            continue
                        seen.add(x["id"])
                        text, kb = fmt_item(x)
                        await broadcast(text, kb)
                        stats["n"] += 1
                        stats["last"] = datetime.now()
                        log.info("sent %s %s⭐ %s", x["name"], x["stars"], x["seller"])
                    if len(seen) > 8000:
                        seen.clear()
        except Exception as e:
            log.exception(e)
        await asyncio.sleep(settings.poll_interval)

async def main():
    asyncio.create_task(tracker_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
