"""
Трекер NFT-подарков Telegram за Stars (официальный resale market).
"""
import asyncio
import logging
import struct
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.tlobject import TLRequest

from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("stars-bot")

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
paused = False
stats = {"n": 0, "last": None}
seen: set[str] = set()
user_client: TelegramClient | None = None


# ---- custom TL: payments.getResaleStarGifts (слой новее telethon 1.37) ----
# payments.getResaleStarGifts#7a5fa236
# flags:# sort_by_price:flags.1?true sort_by_num:flags.2?true for_craft:flags.4?true
# stars_only:flags.5?true attributes_hash:flags.0?long gift_id:long
# attributes:flags.3?Vector<StarGiftAttributeId> offset:string limit:int
# = payments.ResaleStarGifts;

class GetResaleStarGiftsRequest(TLRequest):
    CONSTRUCTOR_ID = 0x7A5FA236
    SUBCLASS_OF_ID = 0x8B4F3C8F  # arbitrary

    def __init__(
        self,
        gift_id: int,
        offset: str,
        limit: int,
        sort_by_price: bool = False,
        sort_by_num: bool = False,
        for_craft: bool = False,
        stars_only: bool = True,
        attributes_hash: int | None = None,
        attributes: list | None = None,
    ):
        self.gift_id = int(gift_id)
        self.offset = offset or ""
        self.limit = int(limit)
        self.sort_by_price = bool(sort_by_price)
        self.sort_by_num = bool(sort_by_num)
        self.for_craft = bool(for_craft)
        self.stars_only = bool(stars_only)
        self.attributes_hash = attributes_hash
        self.attributes = attributes

    def to_dict(self):
        return {
            "_": "GetResaleStarGiftsRequest",
            "gift_id": self.gift_id,
            "offset": self.offset,
            "limit": self.limit,
            "stars_only": self.stars_only,
        }

    def _bytes(self):
        # pack TL request manually (method not in telethon 1.37 schema)
        flags = 0
        if self.attributes_hash is not None:
            flags |= 1 << 0
        if self.sort_by_price:
            flags |= 1 << 1
        if self.sort_by_num:
            flags |= 1 << 2
        if self.attributes is not None:
            flags |= 1 << 3
        if self.for_craft:
            flags |= 1 << 4
        if self.stars_only:
            flags |= 1 << 5

        def pack_string(s: str) -> bytes:
            data = s.encode("utf-8")
            length = len(data)
            if length < 254:
                out = bytes([length]) + data
            else:
                out = bytes([254, length & 0xFF, (length >> 8) & 0xFF, (length >> 16) & 0xFF]) + data
            pad = (-len(out)) % 4
            return out + (b"\x00" * pad)

        b = struct.pack("<I", self.CONSTRUCTOR_ID)
        b += struct.pack("<I", flags)
        if self.attributes_hash is not None:
            b += struct.pack("<q", int(self.attributes_hash))
        b += struct.pack("<q", self.gift_id)
        if self.attributes is not None:
            b += struct.pack("<i", 0x1CB5C415)
            b += struct.pack("<i", len(self.attributes))
            for a in self.attributes:
                if hasattr(a, "_bytes"):
                    b += a._bytes()
        b += pack_string(self.offset)
        b += struct.pack("<i", self.limit)
        return b

    @classmethod
    def from_reader(cls, reader):
        raise NotImplementedError


def ok(uid: int) -> bool:
    return uid in settings.whitelist_ids or uid in settings.admin_ids


def adm(uid: int) -> bool:
    return uid in settings.admin_ids


async def broadcast(text: str, kb=None):
    targets = set(settings.whitelist_ids) | set(settings.admin_ids)
    for uid in targets:
        try:
            await bot.send_message(
                uid, text, parse_mode=ParseMode.HTML, reply_markup=kb, disable_web_page_preview=False
            )
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
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⭐ Открыть в Telegram", url=link)]]
    )
    return text, kb


@dp.message(Command("start"))
async def c_start(m: Message):
    if not ok(m.from_user.id):
        return await m.answer("⛔ Нет доступа.")
    await m.answer(
        "Бека шлююююха\n\n"
        "⭐ <b>Stars Gift Tracker</b>\n"
        "Только подарки за <b>Telegram Stars</b>.\n"
        "Название · цена ⭐ · продавец · ссылка\n\n"
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


async def ensure_user_client() -> TelegramClient | None:
    global user_client
    if user_client and user_client.is_connected():
        return user_client
    if not settings.api_id or not settings.api_hash or not settings.session_string:
        log.warning("Нет API_ID / API_HASH / SESSION_STRING")
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


def _as_dict(obj):
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        try:
            return obj.to_dict()
        except Exception:
            pass
    d = {}
    for k in dir(obj):
        if k.startswith("_"):
            continue
        try:
            v = getattr(obj, k)
            if callable(v):
                continue
            d[k] = v
        except Exception:
            pass
    return d


def _stars_from(obj) -> int | None:
    if obj is None:
        return None
    if isinstance(obj, int):
        return obj if obj > 0 else None
    if isinstance(obj, (list, tuple)):
        for x in obj:
            s = _stars_from(x)
            if s:
                return s
        return None
    d = _as_dict(obj)
    for key in ("amount", "stars", "value"):
        if key in d and d[key] is not None:
            try:
                v = int(d[key])
                if v > 0:
                    return v
            except Exception:
                pass
    return None


def parse_resale_result(result) -> list[dict]:
    """Достаём список подарков из ответа (даже если тип «сырой»)."""
    out = []
    d = _as_dict(result)
    gifts = d.get("gifts") or d.get("resale_gifts") or []
    if not gifts and isinstance(result, (list, tuple)):
        gifts = result

    users = {}
    for u in d.get("users") or []:
        ud = _as_dict(u)
        uid = ud.get("id")
        if uid:
            users[int(uid)] = ud

    for g in gifts:
        gd = _as_dict(g)
        # иногда gift вложен
        inner = _as_dict(gd.get("gift")) if gd.get("gift") else gd

        gid = inner.get("id") or gd.get("id")
        if not gid:
            continue
        name = inner.get("title") or inner.get("name") or gd.get("title") or "Gift"
        num = inner.get("num") or gd.get("num")
        slug = inner.get("slug") or gd.get("slug") or ""

        stars = None
        for key in ("resell_stars", "resale_stars", "stars", "resell_amount", "amount"):
            stars = _stars_from(inner.get(key) if key in inner else gd.get(key))
            if stars:
                break
        if not stars:
            continue
        if stars < settings.min_stars:
            continue
        if settings.max_stars and stars > settings.max_stars:
            continue

        seller = "—"
        owner_name = inner.get("owner_name") or gd.get("owner_name")
        if owner_name:
            seller = f"@{owner_name}" if not str(owner_name).startswith("@") else str(owner_name)
        else:
            owner = inner.get("owner_id") or gd.get("owner_id")
            od = _as_dict(owner) if owner is not None and not isinstance(owner, int) else {}
            uid = od.get("user_id") or (owner if isinstance(owner, int) else None)
            if uid and int(uid) in users:
                u = users[int(uid)]
                if u.get("username"):
                    seller = f"@{u['username']}"
                else:
                    seller = (f"{u.get('first_name') or ''} {u.get('last_name') or ''}").strip() or f"id:{uid}"
            elif uid:
                seller = f"id:{uid}"

        link = f"https://t.me/nft/{slug}" if slug else "https://t.me/"
        out.append(
            {
                "id": f"stars-{gid}-{num or 0}-{stars}",
                "name": str(name),
                "num": num,
                "stars": int(stars),
                "seller": seller,
                "slug": slug,
                "link": link,
            }
        )
    return out


async def fetch_stars_listings(client: TelegramClient) -> list[dict]:
    req = GetResaleStarGiftsRequest(
        gift_id=0,
        offset="",
        limit=50,
        stars_only=True,
        sort_by_price=False,
        sort_by_num=False,
    )
    try:
        result = await client(req)
        return parse_resale_result(result)
    except Exception as e:
        # если сервер не принял кастомный конструктор / слой — лог
        log.warning("GetResaleStarGifts failed: %s", e)
        return []


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
