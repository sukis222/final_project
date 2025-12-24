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
            "⚠️ Фото будет проверено модератором после создания анкеты",
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
        await state.update_data(photo_file_id=user.photo_file_id, photo_on_moderation=False)
    else:
        # Если старого фото нет, сохраняем None
        await state.update_data(photo_file_id=None, photo_on_moderation=False)

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

    # Сохраняем photo_file_id в состоянии, но НЕ отправляем на модерацию сейчас
    await state.update_data(
        photo_file_id=file_id,
        photo_on_moderation=True,  # Фото будет отправлено на модерацию после завершения анкеты
        pending_photo_file_id=file_id,
        photo_moderation_status='pending'
    )

    await message.answer(
        "✅ Фото сохранено!\n"
        "Оно будет отправлено на модерацию после создания анкеты.\n\n"
        "Продолжаем заполнение анкеты..."
    )

    # Продолжаем заполнение анкеты
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
            f"Выбери тип общения (текущий: {user.goal}):",
            reply_markup=goals_kb
        )
    else:
        await message.answer(
            "Теперь выбери тип общения:",
            reply_markup=goals_kb
        )


@router.message(ProfileStates.PHOTO)
async def photo_invalid(message: types.Message, state: FSMContext):
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
    user.goal = data['goal']
    user.description = data.get('description', '')

    # Обрабатываем фото
    photo_file_id = data.get('photo_file_id')
    photo_on_moderation = data.get('photo_on_moderation', False)
    is_editing = data.get('editing', False)

    user_has_new_photo = False

    if photo_file_id and photo_on_moderation:
        # Если есть новое фото для модерации
        user.photo_file_id = photo_file_id
        user.is_active = False  # Деактивируем анкету до одобрения фото
        user_has_new_photo = True

        # Отправляем фото на модерацию ТОЛЬКО СЕЙЧАС
        await storage.add_moderation(user.id, photo_file_id)

    elif photo_file_id and not photo_on_moderation:
        # Если фото есть, но не на модерации (старое фото при редактировании)
        user.photo_file_id = photo_file_id
        user.is_active = True
    else:
        # Если фото нет
        user.photo_file_id = None
        user.is_active = True

    await storage.save_user(user)

    # Формируем текст анкеты
    action_text = "изменена" if is_editing else "создана"

    if user_has_new_photo:
        status_text = "⏳ (ожидает модерации фото)"
    else:
        status_text = "✅ (активна)"

    text = (
        f"✅ Анкета {action_text} {status_text}!\n\n"
        f"👤 Имя: {user.name}\n"
        f"🎂 Возраст: {user.age}\n"
        f"⚧️ Пол: {user.gender}\n"
        f"🎯 Цель: {user.goal}\n"
    )

    if user.description:
        text += f"📝 О себе: {user.description}\n"

    # Отправляем сообщение пользователю
    if user_has_new_photo:
        text += "\n\n⏳ Фото отправлено на модерацию.\n"
        text += "Модератор проверит его в течение нескольких минут.\n"
        text += "Вы получите уведомление, когда фото будет проверено."

        if user.photo_file_id:
            await message.answer_photo(
                photo=user.photo_file_id,
                caption=text,
                reply_markup=get_main_menu()
            )
        else:
            await message.answer(text, reply_markup=get_main_menu())

    else:
        if user.photo_file_id:
            await message.answer_photo(
                photo=user.photo_file_id,
                caption=text,
                reply_markup=get_main_menu()
            )
        else:
            text += "\n⚠️ Фото не загружено"
            await message.answer(text, reply_markup=get_main_menu())

    await state.clear()