from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
import config
from services import ai as ai_service

router = Router()


class AIStates(StatesGroup):
    waiting_image_prompt = State()
    waiting_photo = State()


@router.message(F.text == "💬 Чат с ИИ")
async def start_chat(message: Message):
    await message.answer(
        "💬 Режим чата с ИИ включён.\n\nПросто пиши свой вопрос. Чтобы выйти — нажми «❌ Отмена».",
        reply_markup=kb.cancel_kb()
    )


@router.message(F.text == "🎨 Создать картинку")
async def start_image(message: Message, state: FSMContext):
    await state.set_state(AIStates.waiting_image_prompt)
    await message.answer(
        "🎨 Напиши, что нужно нарисовать.\nНапример: «кот в космосе в стиле аниме»",
        reply_markup=kb.cancel_kb()
    )


@router.message(F.text == "📸 Решить по фото")
async def start_photo_solve(message: Message, state: FSMContext):
    await state.set_state(AIStates.waiting_photo)
    await message.answer(
        "📸 Пришли фото задачи (можно с подписью).\nЯ попробую решить её по шагам.",
        reply_markup=kb.cancel_kb()
    )


@router.message(AIStates.waiting_image_prompt)
async def process_image_prompt(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.main_menu_kb())
        return

    can, reason = await db.can_make_request(message.from_user.id, is_image=True)
    if not can:
        await message.answer(reason, reply_markup=kb.main_menu_kb())
        await state.clear()
        return

    await message.answer("🎨 Генерирую картинку...")

    # Списание
    await db.spend_for_request(message.from_user.id, is_image=True, cost=config.PRICES["image_gen"])

    image_url = await ai_service.generate_image(message.text)
    if image_url:
        await message.answer_photo(image_url, caption=f"🎨 {message.text}")
    else:
        await message.answer("Не удалось сгенерировать картинку. Попробуй другую формулировку.")

    await state.clear()
    await message.answer("Что делаем дальше?", reply_markup=kb.main_menu_kb())


@router.message(AIStates.waiting_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    can, reason = await db.can_make_request(message.from_user.id)
    if not can:
        await message.answer(reason, reply_markup=kb.main_menu_kb())
        await state.clear()
        return

    await message.answer("🔍 Смотрю на задачу...")

    # Скачиваем фото
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_path = f"data/temp_{message.from_user.id}.jpg"
    await message.bot.download_file(file.file_path, file_path)

    await db.spend_for_request(message.from_user.id, cost=config.PRICES["photo_solve"])

    # Читаем байты для возможного vision/OCR
    with open(file_path, "rb") as f:
        image_bytes = f.read()

    caption = message.caption or ""
    result = await ai_service.solve_photo(image_bytes, caption)
    await message.answer(result, parse_mode=ParseMode.HTML)

    await state.clear()
    await message.answer("Что делаем дальше?", reply_markup=kb.main_menu_kb())


@router.message(AIStates.waiting_photo)
async def process_photo_wrong(message: Message):
    await message.answer("Пришли именно фото, пожалуйста.")


# === Обычные текстовые сообщения (чат) ===
@router.message(F.text & ~F.text.in_({
    "💬 Чат с ИИ", "🎨 Создать картинку", "📸 Решить по фото",
    "👤 Профиль", "💎 Тарифы", "💰 Пополнить", "🔗 Рефералка", "ℹ️ Помощь", "❌ Отмена"
}))
async def universal_chat(message: Message, state: FSMContext):
    # Если пользователь в каком-то состоянии — не перехватываем
    current_state = await state.get_state()
    if current_state:
        return

    can, reason = await db.can_make_request(message.from_user.id)
    if not can:
        await message.answer(reason)
        return

    await message.bot.send_chat_action(message.chat.id, "typing")

    await db.spend_for_request(message.from_user.id)

    response = await ai_service.ask(message.text)
    await message.answer(response)
