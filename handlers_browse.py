from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from storage import storage

router = Router()


async def send_profile_chat(user_obj: types.User, target_user, bot):
    """Отправка анкеты для просмотра"""
    caption = (
        f"👤 {target_user.name}, {target_user.age}\n"
        f"⚧️ {target_user.gender}\n"
        f"🎯 {target_user.goal}\n"
    )

    if target_user.description:
        caption += f"\n📝 {target_user.description}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='❤️ Лайк', callback_data=f'like:{target_user.id}'),
            InlineKeyboardButton(text='❌ Пропустить', callback_data=f'skip:{target_user.id}')
        ],
        [InlineKeyboardButton(text='⛔️ Остановить поиск', callback_data='stop_search')]
    ])

    if target_user.photo_file_id:
        await bot.send_photo(user_obj.id, target_user.photo_file_id, caption=caption, reply_markup=kb)
    else:
        await bot.send_message(user_obj.id, caption, reply_markup=kb)


@router.message(F.text.lower() == "да")
async def start_browsing(message: types.Message):
    user = storage.get_user_by_tg(message.from_user.id)

    if not user or not user.is_active:
        await message.answer(
            'У вас нет активной анкеты.\n'
            'Создайте её: /start -> 📌 Создать анкету'
        )
        return

    candidate = storage.get_next_candidate(user.id)

    if not candidate:
        await message.answer('На данный момент нет новых анкет для просмотра 👀')
        return

    await send_profile_chat(message.from_user, candidate, message.bot)


@router.callback_query(F.data.startswith('like:'))
async def process_like(callback: types.CallbackQuery):
    user = storage.get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer('Сначала создайте анкету: /start')
        return

    to_id = int(callback.data.split(':', 1)[1])

    if to_id == user.id:
        await callback.answer('Нельзя лайкнуть себя.')
        return

    if storage.has_liked(user.id, to_id):
        await callback.answer('Вы уже лайкали этого пользователя.')
        return

    like = storage.add_like(user.id, to_id)

    # ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ ТОМУ, КОГО ЛАЙКНУЛИ
    liked_user = storage.get_user_by_id(to_id)
    if liked_user:
        # Получаем информацию о том, кто лайкнул
        liker = storage.get_user_by_id(user.id)

        # Отправляем уведомление тому, кого лайкнули
        await callback.message.bot.send_message(
            liked_user.tg_id,
            f'❤️ Вам поставил лайк {liker.name}!\n'
            f'Если он вам тоже понравится - будет взаимность!'
        )

    # Проверка на взаимный лайк
    if like.is_mutual:
        u_from = storage.get_user_by_id(user.id)
        u_to = storage.get_user_by_id(to_id)

        # Уведомляем обоих пользователей о совпадении
        await callback.message.bot.send_message(
            u_from.tg_id,
            f'🎉 У вас совпадение с {u_to.name}!'
        )
        await callback.message.bot.send_message(
            u_to.tg_id,
            f'🎉 У вас совпадение с {u_from.name}!'
        )

        # Кнопки для начала диалога
        kb1 = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='💬 Начать диалог', url=f'tg://user?id={u_to.tg_id}')]
        ])
        kb2 = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='💬 Начать диалог', url=f'tg://user?id={u_from.tg_id}')]
        ])

        await callback.message.bot.send_message(u_from.tg_id, 'Начните общение:', reply_markup=kb1)
        await callback.message.bot.send_message(u_to.tg_id, 'Начните общение:', reply_markup=kb2)

    await callback.answer('Лайк сохранён ❤️')

    # Удаляем текущее сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Показываем следующую анкету
    await show_next_profile(user, callback.message.bot)


@router.callback_query(F.data.startswith('skip:'))
async def process_skip(callback: types.CallbackQuery):
    user = storage.get_user_by_tg(callback.from_user.id)

    await callback.answer('Пропущено')

    try:
        await callback.message.delete()
    except:
        pass

    await show_next_profile(user, callback.message.bot)


async def show_next_profile(user, bot):
    candidate = storage.get_next_candidate(user.id)

    if not candidate:
        await bot.send_message(user.tg_id, 'Вы просмотрели все анкеты 👀')
        return

    await send_profile_chat(types.User(id=user.tg_id), candidate, bot)


@router.callback_query(F.data == 'stop_search')
async def stop_search(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📝 Перезаполнить анкету', callback_data='refill'),
         InlineKeyboardButton(text='🔄 Продолжить просмотр', callback_data='continue')]
    ])

    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except:
        user = storage.get_user_by_tg(callback.from_user.id)
        if user:
            await callback.message.bot.send_message(
                user.tg_id,
                'Выберите действие:',
                reply_markup=kb
            )

    await callback.answer()


@router.callback_query(F.data == 'refill')
async def refill_profile(callback: types.CallbackQuery):
    await callback.message.answer(
        'Чтобы перезаполнить анкету, используйте:\n'
        '/start -> 📌 Создать анкету'
    )
    await callback.answer()


@router.callback_query(F.data == 'continue')
async def continue_browsing(callback: types.CallbackQuery):
    user = storage.get_user_by_tg(callback.from_user.id)
    await callback.answer()

    if user:
        candidate = storage.get_next_candidate(user.id)
        if candidate:
            await send_profile_chat(callback.from_user, candidate, callback.message.bot)
        else:
            await callback.message.answer('Нет новых анкет для просмотра 👀')
    else:
        await callback.message.answer('Сначала создайте анкету: /start')