import asyncio, logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
import aiohttp
from config import settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")
bot = Bot(token=settings.bot_token)
dp = Dispatcher()
paused = False
stats = {"n": 0, "last": None}
seen = set()

CATS = [
    (lambda p, b: b, "🖤", "ЧЁРНЫЙ ФОН"),
    (lambda p, b: p <= 3, "💧", "ДО 3 TON"),
    (lambda p, b: 3 < p <= 10, "💎", "3–10 TON"),
    (lambda p, b: 10 < p <= 30, "🔶", "10–30 TON"),
    (lambda p, b: 50 <= p <= 100, "💜", "50–100 TON"),
]

def ok(uid): return uid in settings.whitelist_ids or uid in settings.admin_ids
def adm(uid): return uid in settings.admin_ids

def cat(price, black):
    for fn, e, t in CATS:
        if fn(price, black): return e, t
    return None

def fmt(name, num, price, market, url, black=False, backdrop=None):
    c = cat(price, black)
    if not c: return None, None
    e, t = c
    lines = [f"{e} <b>{t}</b>", "", f"🎁 <b>{name}" + (f" #{num}" if num else "") + "</b>",
             f"💰 Цена: <b>{price:.2f} TON</b>", f"🏪 Маркет: {market}"]
    if backdrop: lines.append(f"🎨 Фон: {backdrop}")
    lines.append("⏱ Выставлен: только что")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔗 Открыть", url=url)]])
    return "\n".join(lines), kb

async def broadcast(text, kb=None):
    for uid in set(settings.whitelist_ids) | set(settings.admin_ids):
        try: await bot.send_message(uid, text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception as e: log.warning("send %s: %s", uid, e)

@dp.message(Command("start"))
async def c_start(m: Message):
    if not ok(m.from_user.id): return await m.answer("⛔ Доступ запрещён.")
    await m.answer("Бека шлююююха\n\n👋 <b>NFT Tracker</b>\nMRKT + Getgems\n≤1 мин · 🖤/цены\n/help", parse_mode=ParseMode.HTML)

@dp.message(Command("help"))
async def c_help(m: Message):
    if not ok(m.from_user.id): return
    t = "/start /status /pause /resume /help"
    if adm(m.from_user.id): t += "\nАдмин: /users /add_user ID /remove_user ID"
    await m.answer(t)

@dp.message(Command("status"))
async def c_status(m: Message):
    if not ok(m.from_user.id): return
    st = "⏸ пауза" if paused else "🟢 работает"
    last = stats["last"].strftime("%H:%M:%S") if stats["last"] else "—"
    src = []
    if settings.mrkt_token: src.append("MRKT")
    if settings.getgems_token: src.append("Getgems")
    await m.answer(f"{st}\nИсточники: {', '.join(src) or 'нет токенов'}\nОтправлено: {stats['n']}\nПоследнее: {last}")

@dp.message(Command("pause"))
async def c_pause(m: Message):
    if not ok(m.from_user.id): return
    global paused; paused = True
    await m.answer("⏸ Пауза")

@dp.message(Command("resume"))
async def c_resume(m: Message):
    if not ok(m.from_user.id): return
    global paused; paused = False
    await m.answer("▶️ Работает")

@dp.message(Command("users"))
async def c_users(m: Message):
    if not adm(m.from_user.id): return await m.answer("Только админ")
    await m.answer(f"Whitelist:\n<code>{settings.whitelist_ids or 'пусто'}</code>\nAdmins:\n<code>{settings.admin_ids or 'пусто'}</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("add_user"))
async def c_add(m: Message, command: CommandObject):
    if not adm(m.from_user.id): return
    try:
        uid = int(command.args.strip())
        if uid not in settings.whitelist_ids:
            settings.whitelist_ids.append(uid)
            await m.answer(f"✅ {uid}")
        else: await m.answer("Уже есть")
    except: await m.answer("/add_user ID")

@dp.message(Command("remove_user"))
async def c_rm(m: Message, command: CommandObject):
    if not adm(m.from_user.id): return
    try:
        uid = int(command.args.strip())
        if uid in settings.whitelist_ids:
            settings.whitelist_ids.remove(uid)
            await m.answer(f"✅ удалён {uid}")
        else: await m.answer("Нет в списке")
    except: await m.answer("/remove_user ID")

def _is_black(backdrop) -> bool:
    if not backdrop: return False
    s = str(backdrop).lower()
    return "black" in s or "чёрн" in s or "черн" in s

def _price_ton(v) -> float | None:
    try:
        p = float(v)
        if p > 1_000_000:  # nanotons
            p = p / 1e9
        return p
    except (TypeError, ValueError):
        return None

async def fetch_mrkt(session: aiohttp.ClientSession) -> list:
    if not settings.mrkt_token:
        return []
    url = "https://api.tgmrkt.io/api/v1/gifts/saling"
    headers = {
        "Authorization": settings.mrkt_token,
        "Referer": "https://cdn.tgmrkt.io/",
        "Content-Type": "application/json",
    }
    body = {
        "collectionNames": [], "modelNames": [], "backdropNames": [], "symbolNames": [],
        "ordering": None, "lowToHigh": False, "maxPrice": None, "minPrice": None,
        "mintable": None, "number": None, "count": 20, "cursor": "", "query": None, "promotedFirst": False,
    }
    try:
        async with session.post(url, headers=headers, json=body, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status != 200:
                log.warning("MRKT %s", r.status)
                return []
            data = await r.json()
    except Exception as e:
        log.warning("MRKT: %s", e)
        return []

    out = []
    for g in data.get("gifts") or data.get("items") or []:
        gid = str(g.get("id") or g.get("giftId") or g.get("saleId") or "")
        if not gid or gid in seen:
            continue
        price = _price_ton(g.get("price") or g.get("salePrice") or g.get("tonPrice"))
        if price is None:
            continue
        name = g.get("name") or g.get("title") or g.get("collectionName") or "Gift"
        num = g.get("number") or g.get("num") or g.get("giftNumber")
        if num is not None:
            num = str(num)
        backdrop = g.get("backdrop") or g.get("backdropName") or g.get("background")
        if isinstance(backdrop, dict):
            backdrop = backdrop.get("name") or backdrop.get("title")
        model = g.get("model") or g.get("modelName")
        if isinstance(model, dict):
            model = model.get("name")
        if model and name == "Gift":
            name = str(model)
        link = g.get("url") or g.get("link") or "https://t.me/mrkt"
        black = _is_black(backdrop)
        if not cat(price, black):
            continue
        out.append({
            "id": f"mrkt-{gid}", "name": str(name), "num": num, "price": price,
            "market": "MRKT", "url": link, "black": black,
            "backdrop": str(backdrop) if backdrop else None,
        })
    return out

async def fetch_getgems(session: aiohttp.ClientSession) -> list:
    """Getgems offchain gifts on sale. Нужен GETGEMS_TOKEN (Bearer, ~2 дня)."""
    if not settings.getgems_token:
        return []
    url = "https://api.getgems.io/public-api/v1/nfts/offchain/on-sale/gifts"
    headers = {
        "Authorization": f"Bearer {settings.getgems_token}" if not settings.getgems_token.lower().startswith("bearer ") else settings.getgems_token,
        "Accept": "application/json",
    }
    params = {"limit": 30}
    try:
        async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status == 401:
                log.warning("Getgems: токен невалиден/истёк")
                return []
            if r.status != 200:
                text = await r.text()
                log.warning("Getgems %s: %s", r.status, text[:200])
                return []
            data = await r.json()
    except Exception as e:
        log.warning("Getgems: %s", e)
        return []

    items = data.get("nfts") or data.get("items") or data.get("data") or []
    if isinstance(data, list):
        items = data

    out = []
    for g in items:
        gid = str(g.get("address") or g.get("id") or g.get("nftAddress") or "")
        if not gid or gid in seen:
            continue

        # цена
        sale = g.get("sale") or g.get("fix") or {}
        price = _price_ton(
            sale.get("price") if isinstance(sale, dict) else None
            or g.get("price")
            or g.get("fullPrice")
            or g.get("tonPrice")
        )
        if price is None:
            continue

        meta = g.get("metadata") or g.get("content") or {}
        name = (
            g.get("name")
            or meta.get("name")
            or g.get("collection", {}).get("name") if isinstance(g.get("collection"), dict) else None
            or "Gift"
        )
        num = g.get("index") or g.get("number") or meta.get("number")
        if num is not None:
            num = str(num)

        # backdrop / attributes
        backdrop = None
        attrs = meta.get("attributes") or g.get("attributes") or []
        if isinstance(attrs, list):
            for a in attrs:
                if not isinstance(a, dict):
                    continue
                t = str(a.get("trait_type") or a.get("type") or "").lower()
                if "backdrop" in t or "background" in t or "фон" in t:
                    backdrop = a.get("value") or a.get("name")
                    break
        black = _is_black(backdrop)

        link = g.get("url") or (f"https://getgems.io/nft/{gid}" if gid else "https://getgems.io")
        if not cat(price, black):
            continue

        out.append({
            "id": f"gg-{gid}",
            "name": str(name),
            "num": num,
            "price": price,
            "market": "Getgems",
            "url": link,
            "black": black,
            "backdrop": str(backdrop) if backdrop else None,
        })
    return out

async def fetch_new():
    out = []
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            fetch_mrkt(session),
            fetch_getgems(session),
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, list):
                out.extend(r)
            elif isinstance(r, Exception):
                log.warning("fetch: %s", r)
    return out

async def loop():
    log.info("tracker | MRKT=%s Getgems=%s", bool(settings.mrkt_token), bool(settings.getgems_token))
    while True:
        try:
            if not paused:
                for x in await fetch_new():
                    if x["id"] in seen:
                        continue
                    seen.add(x["id"])
                    text, kb = fmt(x["name"], x.get("num"), x["price"], x["market"], x["url"], x.get("black", False), x.get("backdrop"))
                    if text:
                        await broadcast(text, kb)
                        stats["n"] += 1
                        stats["last"] = datetime.now()
                        log.info("sent %s %.2f %s", x["name"], x["price"], x["market"])
                if len(seen) > 5000:
                    seen.clear()
        except Exception as e:
            log.exception(e)
        await asyncio.sleep(settings.poll_interval)

async def main():
    asyncio.create_task(loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
