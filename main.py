import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from config import BOT_TOKEN, HEALTHCHECK_PORT, validate_config
from handlers import router
from monitor import monitor_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("main")


async def handle_health(request: web.Request) -> web.Response:
    return web.Response(text="OK", status=200)


async def run_healthcheck_server() -> None:
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=HEALTHCHECK_PORT)
    await site.start()
    logger.info("Health-check сервер запущен на порту %s", HEALTHCHECK_PORT)

    # Держим корутину живой, пока не отменят
    await asyncio.Event().wait()


async def main() -> None:
    validate_config()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    await asyncio.gather(
        dp.start_polling(bot),
        monitor_loop(bot),
        run_healthcheck_server(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
