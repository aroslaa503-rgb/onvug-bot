from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject
from aiogram.enums import ParseMode

import database as db
import keyboards as kb
import config

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    # Реферал
    referrer_id = None
    if command.args and command.args.isdigit():
        referrer_id = int(command.args)
        if referrer_id == user_id:
            referrer_id = None

    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, username, full_name, referrer_id)
        # Можно добавить уведомление рефереру

    await message.answer(
        config.WELCOME_TEXT,
        reply_markup=kb.main_menu_kb(),
        parse_mode=ParseMode.HTML
    )


@router.message(F.text == "ℹ️ Помощь")
async def help_handler(message: Message):
    text = """ℹ️ <b>Помощь по боту</b>

<b>Что умею сейчас:</b>
• 💬 Умный чат с ИИ — просто пиши вопросы
• 🎨 Генерация картинок — напиши «нарисуй кота в космосе»
• 📸 Решение задач — пришли фото задачи

<b>Как пользоваться:</b>
1. Просто пиши текстом — я отвечу
2. Пришли фото задачи — решу по шагам
3. Напиши «нарисуй ...» — создам картинку

<b>Лимиты:</b>
Бесплатно даётся ограниченное количество запросов в день.
Чтобы снять ограничения — оформи подписку в разделе «💎 Тарифы».

<b>Скоро появится:</b>
🎬 Оживление фото
🌐 Создание сайтов
📱 Создание Mini App
🖥️ Деплой кода на сервер

По вопросам: напиши администратору."""
    await message.answer(text, parse_mode=ParseMode.HTML)


@router.message(F.text == "❌ Отмена")
async def cancel_handler(message: Message):
    await message.answer("Отменено.", reply_markup=kb.main_menu_kb())
