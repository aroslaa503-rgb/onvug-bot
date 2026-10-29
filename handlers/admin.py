from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
import config
from services import ai as ai_module

router = Router()


class AdminStates(StatesGroup):
    waiting_api_provider = State()
    waiting_api_name = State()
    waiting_api_key = State()
    waiting_api_model = State()
    waiting_api_url = State()
    waiting_api_limit = State()


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def admin_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔑 API ключи", callback_data="admin_apis"))
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    builder.row(InlineKeyboardButton(text="💰 Выдать баланс", callback_data="admin_give_info"))
    return builder.as_markup()


def apis_kb(keys: list):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить ключ", callback_data="admin_api_add"))
    for k in keys:
        status = "✅" if k["is_active"] and k["is_alive"] else "🔴"
        paid = "💰" if k["is_paid"] else "🆓"
        builder.row(InlineKeyboardButton(
            text=f"{status}{paid} {k['name']} ({k['used_today']}/{k['daily_limit']})",
            callback_data=f"admin_api_view:{k['id']}"
        ))
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="admin_back"))
    return builder.as_markup()


def api_view_kb(key_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_api_del:{key_id}"),
        InlineKeyboardButton(text="🔄 Вкл/Выкл", callback_data=f"admin_api_toggle:{key_id}")
    )
    builder.row(InlineKeyboardButton(text="« К списку", callback_data="admin_apis"))
    return builder.as_markup()


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🔧 <b>Админ-панель</b>", reply_markup=admin_main_kb(), parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🔧 <b>Админ-панель</b>", reply_markup=admin_main_kb(), parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    import aiosqlite
    async with aiosqlite.connect(config.DB_PATH) as conn:
        async with conn.execute("SELECT COUNT(*) FROM users") as c:
            total_users = (await c.fetchone())[0]
        async with conn.execute("SELECT COUNT(*) FROM api_keys WHERE bot_id = 0") as c:
            keys_count = (await c.fetchone())[0]

    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🔑 API ключей: {keys_count}"
    )
    await callback.message.edit_text(text, reply_markup=admin_main_kb(), parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data == "admin_give_info")
async def admin_give_info(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "Чтобы выдать баланс, напиши:\n"
        "<code>/give user_id сумма тип</code>\n\n"
        "Тип: main / bonus / withdrawable\n"
        "Пример: <code>/give 123456789 100 main</code>",
        parse_mode=ParseMode.HTML
    )


# ==================== API КЛЮЧИ ====================

@router.callback_query(F.data == "admin_apis")
async def admin_apis(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    keys = await ai_module.list_api_keys(bot_id=0)
    text = "🔑 <b>API ключи главного бота</b>\n\n"
    if not keys:
        text += "Пока нет ни одного ключа.\nНажми «Добавить ключ»."
    else:
        text += f"Всего ключей: {len(keys)}\nНажми на ключ, чтобы управлять."

    await callback.message.edit_text(text, reply_markup=apis_kb(keys), parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data == "admin_api_add")
async def admin_api_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_api_provider)
    await callback.message.edit_text(
        "Введи <b>провайдера</b> ключа:\n\n"
        "Примеры: <code>groq</code>, <code>openrouter</code>, <code>gemini</code>, <code>openai</code>\n\n"
        "Или /cancel для отмены.",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(AdminStates.waiting_api_provider)
async def admin_api_provider(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("Отменено.")
        return

    await state.update_data(provider=message.text.strip().lower())
    await state.set_state(AdminStates.waiting_api_name)
    await message.answer(
        "Введи <b>название</b> ключа (для себя):\n"
        "Например: <code>Gemini #1</code> или <code>Groq основной</code>",
        parse_mode=ParseMode.HTML
    )


@router.message(AdminStates.waiting_api_name)
async def admin_api_name(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("Отменено.")
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminStates.waiting_api_key)
    await message.answer("Введи сам <b>API ключ</b>:", parse_mode=ParseMode.HTML)


@router.message(AdminStates.waiting_api_key)
async def admin_api_key(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("Отменено.")
        return
    await state.update_data(api_key=message.text.strip())
    await state.set_state(AdminStates.waiting_api_model)
    await message.answer(
        "Введи <b>модель</b>:\n\n"
        "Примеры:\n"
        "• <code>llama-3.3-70b-versatile</code>\n"
        "• <code>google/gemini-flash-1.5</code>\n"
        "• <code>gpt-4o-mini</code>",
        parse_mode=ParseMode.HTML
    )


@router.message(AdminStates.waiting_api_model)
async def admin_api_model(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("Отменено.")
        return
    await state.update_data(model=message.text.strip())
    await state.set_state(AdminStates.waiting_api_url)
    await message.answer(
        "Введи <b>Base URL</b>:\n\n"
        "• <code>https://api.groq.com/openai/v1</code>\n"
        "• <code>https://openrouter.ai/api/v1</code>\n"
        "• <code>https://api.openai.com/v1</code>",
        parse_mode=ParseMode.HTML
    )


@router.message(AdminStates.waiting_api_url)
async def admin_api_url(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("Отменено.")
        return
    await state.update_data(base_url=message.text.strip())
    await state.set_state(AdminStates.waiting_api_limit)
    await message.answer(
        "Введи <b>дневной лимит</b> запросов (число):\nНапример: <code>1000</code>",
        parse_mode=ParseMode.HTML
    )


@router.message(AdminStates.waiting_api_limit)
async def admin_api_limit(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("Отменено.")
        return
    try:
        limit = int(message.text.strip())
    except ValueError:
        await message.answer("Введи число.")
        return

    await state.update_data(daily_limit=limit)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🆓 Бесплатный", callback_data="admin_api_free"),
        InlineKeyboardButton(text="💰 Платный", callback_data="admin_api_paid_flag")
    )
    await message.answer("Этот ключ бесплатный или платный?", reply_markup=builder.as_markup())


@router.callback_query(F.data.in_({"admin_api_free", "admin_api_paid_flag"}))
async def admin_api_save(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    data = await state.get_data()
    is_paid = callback.data == "admin_api_paid_flag"

    key_id = await ai_module.add_api_key(
        bot_id=0,
        provider=data["provider"],
        name=data["name"],
        api_key=data["api_key"],
        model=data["model"],
        base_url=data["base_url"],
        is_paid=is_paid,
        daily_limit=data["daily_limit"]
    )

    await state.clear()
    await callback.message.edit_text(
        f"✅ Ключ <b>{data['name']}</b> добавлен (id: {key_id})\n\n"
        f"Провайдер: {data['provider']}\n"
        f"Модель: {data['model']}\n"
        f"Тип: {'платный' if is_paid else 'бесплатный'}\n"
        f"Лимит: {data['daily_limit']}/день",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_api_view:"))
async def admin_api_view(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    key_id = int(callback.data.split(":")[1])
    keys = await ai_module.list_api_keys(0)
    key = next((k for k in keys if k["id"] == key_id), None)
    if not key:
        await callback.answer("Ключ не найден", show_alert=True)
        return

    text = (
        f"🔑 <b>{key['name']}</b>\n\n"
        f"Провайдер: {key['provider']}\n"
        f"Модель: {key['model']}\n"
        f"Тип: {'💰 платный' if key['is_paid'] else '🆓 бесплатный'}\n"
        f"Использовано: {key['used_today']}/{key['daily_limit']}\n"
        f"Статус: {'✅ активен' if key['is_active'] and key['is_alive'] else '🔴 выключен'}"
    )
    await callback.message.edit_text(text, reply_markup=api_view_kb(key_id), parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_api_del:"))
async def admin_api_del(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    key_id = int(callback.data.split(":")[1])
    await ai_module.delete_api_key(key_id, bot_id=0)
    await callback.answer("Удалён")
    keys = await ai_module.list_api_keys(0)
    await callback.message.edit_text(
        "🔑 <b>API ключи</b>\n\nКлюч удалён.",
        reply_markup=apis_kb(keys),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.startswith("admin_api_toggle:"))
async def admin_api_toggle(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    key_id = int(callback.data.split(":")[1])
    await ai_module.toggle_api_key(key_id, bot_id=0)
    await callback.answer("Статус изменён")
    keys = await ai_module.list_api_keys(0)
    key = next((k for k in keys if k["id"] == key_id), None)
    if key:
        text = (
            f"🔑 <b>{key['name']}</b>\n\n"
            f"Статус: {'✅ активен' if key['is_active'] else '🔴 выключен'}"
        )
        await callback.message.edit_text(text, reply_markup=api_view_kb(key_id), parse_mode=ParseMode.HTML)


@router.message(Command("give"))
async def give_balance(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Формат: /give user_id сумма [main/bonus/withdrawable]")
        return

    try:
        user_id = int(parts[1])
        amount = float(parts[2])
        btype = parts[3] if len(parts) > 3 else "main"
    except ValueError:
        await message.answer("Ошибка в параметрах")
        return

    from services.balance import add_balance
    await add_balance(user_id, amount, btype, f"Выдано админом {message.from_user.id}")
    await message.answer(f"Выдано {amount} ₽ ({btype}) пользователю {user_id}")
