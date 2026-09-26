import logging

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from config import ADMIN_ID
from monitor import send_test_alert
from storage import add_subscriber, load_state, load_subscribers

logger = logging.getLogger("handlers")

router = Router()


def is_admin(user_id: int) -> bool:
    return ADMIN_ID != 0 and user_id == ADMIN_ID


@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    added = add_subscriber(user_id)

    lines = [f"👋 Привет! Ваш Telegram ID: <code>{user_id}</code>"]
    if added:
        lines.append("✅ Вы подписаны на уведомления о событиях NFT.")
    else:
        lines.append("ℹ️ Вы уже подписаны на уведомления.")

    await message.answer("\n".join(lines))


@router.message(Command("status"))
async def cmd_status(message: Message):
    user_id = message.from_user.id
    subscribers = load_subscribers()
    state = load_state()

    text = (
        f"📊 <b>Статус</b>\n\n"
        f"Ваш ID: <code>{user_id}</code>\n"
        f"Админ: {'да ✅' if is_admin(user_id) else 'нет'}\n"
        f"Подписчиков: <b>{len(subscribers)}</b>\n"
        f"Обработано событий: <b>{state.get('total_events', 0)}</b>"
    )
    await message.answer(text)


@router.message(Command("test"))
async def cmd_test(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Эта команда доступна только администратору.")
        return

    await send_test_alert(bot)
    await message.answer("✅ Тестовое уведомление разослано подписчикам.")


@router.message(Command("add"))
async def cmd_add(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Эта команда доступна только администратору.")
        return

    if not command.args:
        await message.answer("Использование: /add <telegram_id>")
        return

    try:
        new_id = int(command.args.strip().split()[0])
    except ValueError:
        await message.answer("Некорректный ID. Пример: /add 123456789")
        return

    added = add_subscriber(new_id)
    if added:
        await message.answer(f"✅ Пользователь <code>{new_id}</code> добавлен в подписчики.")
    else:
        await message.answer(f"ℹ️ Пользователь <code>{new_id}</code> уже был подписан.")


@router.message(Command("list"))
async def cmd_list(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Эта команда доступна только администратору.")
        return

    subscribers = sorted(load_subscribers())
    if not subscribers:
        await message.answer("Список подписчиков пуст.")
        return

    ids_text = "\n".join(f"• <code>{uid}</code>" for uid in subscribers)
    await message.answer(f"👥 <b>Подписчики ({len(subscribers)}):</b>\n\n{ids_text}")
