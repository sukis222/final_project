import asyncio

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from ..states import ProfileStates
from ..storage import storage

router = Router()


# Главное меню после создания анкеты
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Начать поиск анкет")],
            [KeyboardButton(text="📝 Изменить анкету")],
            [KeyboardButton(text="❤️ Посмотреть мои лайки")],
            [KeyboardButton(text="⏹️ Остановить поиск")]
        ],
        resize_keyboard=True
    )


# Меню при старте
def get_start_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📌 Создать анкету")]
        ],
        resize_keyboard=True
    )


@router.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    # Очищаем состояние если было
    await state.clear()

    user = await storage.get_user_by_tg(message.from_user.id)

    if user and user.is_active:
        # Если анкета уже есть, показываем главное меню
        await message.answer(
            f"👋 С возвращением, {user.name}!\n"
            f"Ваша анкета активна. Что вы хотите сделать?",
            reply_markup=get_main_menu()
        )
    else:
        # Если анкеты нет, показываем стартовое меню
        await message.answer(
            "👋 Привет! Добро пожаловать в бот для знакомств!\n\n"
            "Давай создадим твою анкету?",
            reply_markup=get_start_menu()
        )


@router.message(F.text == "📌 Создать анкету")
async def start_profile(message: types.Message, state: FSMContext):
    user = await storage.create_or_get_user(message.from_user.id)
    await state.update_data(user_id=user.id, editing=False)
    await state.set_state(ProfileStates.NAME)
    await message.answer("Как тебя зовут?", reply_markup=ReplyKeyboardRemove())


@router.message(F.text == "📝 Изменить анкету")
async def edit_profile(message: types.Message, state: FSMContext):
    user = await storage.get_user_by_tg(message.from_user.id)

    if not user or not user.is_active:
        await message.answer(
            'У вас нет активной анкеты.\n'
            'Создайте её: /start -> 📌 Создать анкету'
        )
        return

    # Начинаем пересоздание анкеты
    await state.update_data(user_id=user.id, editing=True)
    await state.set_state(ProfileStates.NAME)
    await message.answer(
        "📝 Начинаем изменение анкеты.\n\n"
        "Как тебя зовут? (текущее: {})".format(user.name),
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(F.text == "⏹️ Остановить поиск")
async def stop_search_command(message: types.Message):
    await message.answer(
        "Поиск анкет остановлен.\n"
        "Если захотите кого-то найти, нажмите кнопку '🔄 Начать поиск анкет'",
        reply_markup=get_main_menu()
    )


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

    data = await state.get_data()
    if data.get('editing'):
        user = await storage.get_user_by_id(data['user_id'])
        await message.answer(
            f"Выбери свой пол (текущий: {user.gender}):",
            reply_markup=gender_kb
        )
    else:
        await message.answer("Выбери свой пол:", reply_markup=gender_kb)


@router.message(ProfileStates.GENDER, F.text.in_(["👨 Мужской", "👩 Женский"]))
async def gender_step(message: types.Message, state: FSMContext):
    gender = "Мужской" if message.text == "👨 Мужской" else "Женский"
    await state.update_data(gender=gender)
    await state.set_state(ProfileStates.PHOTO)

    data = await state.get_data()

    if data.get('editing'):
        # При изменении анкеты показываем кнопку "Пропустить"
        photo_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📸 Отправить фото")],
                [KeyboardButton(text="⏭️ Пропустить фото")]
            ],
            resize_keyboard=True
        )

        await message.answer(
            "📸 Загрузи новое фото для анкеты\n"
            "⚠️ Фото будет проверено модератором\n\n"
            "Можно пропустить и оставить старое фото:",
            reply_markup=photo_kb
        )
    else:
        # При создании новой анкеты
        await message.answer(
            "📸 Отправь мне своё фото\n"
            "⚠️ Фото будет проверено модератором в течение нескольких секунд",
            reply_markup=ReplyKeyboardRemove()
        )


@router.message(ProfileStates.GENDER)
async def gender_wrong(message: types.Message):
    await message.answer("Пожалуйста, выбери пол с помощью кнопок ниже 👇")


@router.message(ProfileStates.PHOTO, F.text == "⏭️ Пропустить фото")
async def skip_photo_button(message: types.Message, state: FSMContext):
    data = await state.get_data()

    if not data.get('editing'):
        # При создании новой анкеты нельзя пропустить фото
        await message.answer("Пожалуйста, отправьте фото для вашей анкеты 📸")
        return

    # Только при изменении анкеты можно пропустить фото
    user = await storage.get_user_by_id(data['user_id'])

    # Используем старое фото если есть
    if user and user.photo_file_id:
        await state.update_data(photo_file_id=user.photo_file_id)

    await state.set_state(ProfileStates.GOAL)

    goals_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💼 Деловое")],
            [KeyboardButton(text="👥 Дружеское")],
            [KeyboardButton(text="❤️ Романтическое")]
        ],
        resize_keyboard=True
    )

    user = await storage.get_user_by_id(data['user_id'])
    await message.answer(
        f"Выбери тип общения (текущий: {user.goal}):",
        reply_markup=goals_kb
    )


@router.message(ProfileStates.PHOTO, F.text == "📸 Отправить фото")
async def ready_for_photo(message: types.Message, state: FSMContext):
    await message.answer(
        "Отправьте ваше фото 📸",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(ProfileStates.PHOTO, F.photo)
async def photo_step(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    user_id = data.get('user_id')

    # Добавляем фото на модерацию
    await storage.add_moderation(user_id, file_id)

    await state.update_data(photo_file_id=file_id)
    await state.set_state(ProfileStates.AWAIT_MODERATION)

    # Эмуляция модерации
    await message.answer("⏳ Фото отправлено на проверку...")
    await asyncio.sleep(3)  # Имитация времени модерации

    # Проверяем статус модерации
    mod_status = await storage.get_user_moderation_status(user_id)

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

        if data.get('editing'):
            user = await storage.get_user_by_id(user_id)
            await message.answer(
                "✅ Фото одобрено!\n\n"
                f"Выбери тип общения (текущий: {user.goal}):",
                reply_markup=goals_kb
            )
        else:
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
        # Если модерация еще не завершена
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
    data = await state.get_data()

    if data.get('editing'):
        photo_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📸 Отправить фото")],
                [KeyboardButton(text="⏭️ Пропустить фото")]
            ],
            resize_keyboard=True
        )

        await message.answer(
            "Пожалуйста, отправьте фото 📸 или нажмите '⏭️ Пропустить фото'",
            reply_markup=photo_kb
        )
    else:
        await message.answer("Пожалуйста, отправьте фото 📸")


@router.message(ProfileStates.GOAL)
async def goal_step(message: types.Message, state: FSMContext):
    if message.text not in ["💼 Деловое", "👥 Дружеское", "❤️ Романтическое"]:
        return await message.answer("Пожалуйста, выбери вариант с помощью кнопок:")

    await state.update_data(goal=message.text)
    await state.set_state(ProfileStates.DESCRIPTION)

    skip_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭️ Пропустить описание")]
        ],
        resize_keyboard=True
    )

    data = await state.get_data()
    if data.get('editing'):
        user = await storage.get_user_by_id(data['user_id'])
        current_desc = user.description if user.description else "(пусто)"
        await message.answer(
            f"✍️ Теперь расскажи немного о себе\n"
            f"(текущее: {current_desc})\n\n"
            "Можно пропустить чтобы оставить как есть:",
            reply_markup=skip_kb
        )
    else:
        await message.answer(
            "✍️ Теперь расскажи немного о себе\n"
            "(можно пропустить):",
            reply_markup=skip_kb
        )


@router.message(ProfileStates.DESCRIPTION, F.text == "⏭️ Пропустить описание")
async def description_skip(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get('editing'):
        # Если редактируем и пропускаем, оставляем старое описание
        user = await storage.get_user_by_id(data['user_id'])
        await state.update_data(description=user.description)
    else:
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
    user = await storage.get_user_by_id(data['user_id'])

    # Обновляем данные пользователя
    user.name = data['name']
    user.age = data['age']
    user.gender = data['gender']

    # Обновляем фото только если было загружено новое
    if 'photo_file_id' in data and data['photo_file_id']:
        user.photo_file_id = data['photo_file_id']

    user.goal = data['goal']
    user.description = data.get('description', '')
    user.is_active = True

    await storage.save_user(user)

    # Формируем текст анкеты
    action_text = "изменена" if data.get('editing') else "создана"
    text = (
        f"✅ Анкета {action_text}!\n\n"
        f"👤 Имя: {user.name}\n"
        f"🎂 Возраст: {user.age}\n"
        f"⚧️ Пол: {user.gender}\n"
        f"🎯 Цель: {user.goal}\n"
    )

    if user.description:
        text += f"📝 О себе: {user.description}\n"

    # Отправляем фото если есть
    if user.photo_file_id:
        await message.answer_photo(
            photo=user.photo_file_id,
            caption=text,
            reply_markup=get_main_menu()
        )
    else:
        await message.answer(
            text + "\n⚠️ Фото не загружено",
            reply_markup=get_main_menu()
        )

    await state.clear()
