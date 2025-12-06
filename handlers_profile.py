from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from storage import storage
from states import ProfileStates
import asyncio

router = Router()


# Главное меню
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📌 Создать анкету")],
        ],
        resize_keyboard=True
    )


@router.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Добро пожаловать в бот для знакомств!\n\n"
        "Давай создадим твою анкету?",
        reply_markup=main_menu()
    )


@router.message(F.text == "📌 Создать анкету")
async def start_profile(message: types.Message, state: FSMContext):
    user = storage.create_or_get_user(message.from_user.id)
    await state.update_data(user_id=user.id)
    await state.set_state(ProfileStates.NAME)
    await message.answer("Как тебя зовут?", reply_markup=ReplyKeyboardRemove())


@router.message(ProfileStates.NAME)
async def name_step(message: types.Message, state: FSMContext):
    if len(message.text) < 2:
        return await message.answer("Имя должно содержать хотя бы 2 символа. Введите снова:")

    await state.update_data(name=message.text)
    await state.set_state(ProfileStates.AGE)
    await message.answer("Сколько тебе лет? (от 18 до 99)")


@router.message(ProfileStates.AGE)
async def age_step(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
        if age < 18 or age > 99:
            return await message.answer("Возраст должен быть от 18 до 99. Введите снова:")
    except:
        return await message.answer("Пожалуйста, введите число от 18 до 99:")

    await state.update_data(age=age)

    gender_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Мужской"), KeyboardButton(text="👩 Женский")]
        ],
        resize_keyboard=True
    )

    await state.set_state(ProfileStates.GENDER)
    await message.answer("Выбери свой пол:", reply_markup=gender_kb)


@router.message(ProfileStates.GENDER, F.text.in_(["👨 Мужской", "👩 Женский"]))
async def gender_step(message: types.Message, state: FSMContext):
    gender = "Мужской" if message.text == "👨 Мужской" else "Женский"
    await state.update_data(gender=gender)
    await state.set_state(ProfileStates.PHOTO)
    await message.answer(
        "📸 Отправь мне своё фото\n"
        "⚠️ Фото будет проверено модератором в течение нескольких секунд",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(ProfileStates.GENDER)
async def gender_wrong(message: types.Message):
    await message.answer("Пожалуйста, выбери пол с помощью кнопок ниже 👇")


@router.message(ProfileStates.PHOTO, F.photo)
async def photo_step(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    user_id = data.get('user_id')

    # Добавляем фото на модерацию
    storage.add_moderation(user_id, file_id)

    await state.update_data(photo_file_id=file_id)
    await state.set_state(ProfileStates.AWAIT_MODERATION)

    # Эмуляция модерации
    await message.answer("⏳ Фото отправлено на проверку...")
    await asyncio.sleep(3)  # Имитация времени модерации

    # Проверяем статус модерации
    mod_status = storage.get_user_moderation_status(user_id)

    if mod_status == 'approved':
        await state.set_state(ProfileStates.GOAL)

        goals_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💼 Деловое")],
                [KeyboardButton(text="👥 Дружеское")],
                [KeyboardButton(text="❤️ Романтическое")]
            ],
            resize_keyboard=True
        )

        await message.answer(
            "✅ Фото одобрено!\n\n"
            "Теперь выбери тип общения:",
            reply_markup=goals_kb
        )
    elif mod_status == 'rejected':
        await message.answer(
            "❌ Фото не прошло модерацию.\n"
            "Пожалуйста, загрузи другое фото:"
        )
        await state.set_state(ProfileStates.PHOTO)
    else:
        # Если модерация еще не завершена (в реальном боте нужно ждать ответа админа)
        await message.answer(
            "⚠️ Модерация затянулась. Продолжим создание анкеты.\n\n"
            "Выбери тип общения:"
        )

        goals_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💼 Деловое")],
                [KeyboardButton(text="👥 Дружеское")],
                [KeyboardButton(text="❤️ Романтическое")]
            ],
            resize_keyboard=True
        )

        await state.set_state(ProfileStates.GOAL)
        await message.answer("Зачем ты здесь?", reply_markup=goals_kb)


@router.message(ProfileStates.PHOTO)
async def photo_invalid(message: types.Message):
    await message.answer("Пожалуйста, отправь фото 📸")


@router.message(ProfileStates.GOAL)
async def goal_step(message: types.Message, state: FSMContext):
    if message.text not in ["💼 Деловое", "👥 Дружеское", "❤️ Романтическое"]:
        return await message.answer("Пожалуйста, выбери вариант с помощью кнопок:")

    await state.update_data(goal=message.text)
    await state.set_state(ProfileStates.DESCRIPTION)

    skip_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Пропустить")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "✍️ Теперь расскажи немного о себе\n"
        "(можно пропустить)",
        reply_markup=skip_kb
    )


@router.message(ProfileStates.DESCRIPTION, F.text == "Пропустить")
async def description_skip(message: types.Message, state: FSMContext):
    await state.update_data(description="")
    await finish_profile(message, state)


@router.message(ProfileStates.DESCRIPTION)
async def description_step(message: types.Message, state: FSMContext):
    if len(message.text) > 500:
        return await message.answer("Описание слишком длинное (максимум 500 символов). Сократите:")

    await state.update_data(description=message.text)
    await finish_profile(message, state)


async def finish_profile(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = storage.get_user_by_id(data['user_id'])

    # Обновляем данные пользователя
    user.name = data['name']
    user.age = data['age']
    user.gender = data['gender']
    user.photo_file_id = data.get('photo_file_id')
    user.goal = data['goal']
    user.description = data.get('description', '')
    user.is_active = True

    storage.save_user(user)

    # Формируем текст анкеты
    text = (
        "✅ Анкета создана!\n\n"
        f"👤 Имя: {user.name}\n"
        f"🎂 Возраст: {user.age}\n"
        f"⚧️ Пол: {user.gender}\n"
        f"🎯 Цель: {user.goal}\n"
    )

    if user.description:
        text += f"📝 О себе: {user.description}\n"

    text += "\nНачать просмотр других анкет?"

    start_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да")]
        ],
        resize_keyboard=True
    )

    await message.answer(text, reply_markup=start_kb)
    await state.clear()