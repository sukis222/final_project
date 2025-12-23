import  asyncio
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..config import cfg
from ..storage import storage

router = Router()  # ЭТУ СТРОКУ НУЖНО ДОБАВИТЬ В НАЧАЛО


class AdminDeleteUser(StatesGroup):
    WAITING_FOR_CONFIRMATION = State()
    WAITING_FOR_USER_ID = State()


@router.message(Command('admin'))
async def cmd_admin(message: types.Message):
    """Панель администратора"""
    if message.from_user.id not in cfg.admin_ids:
        await message.answer('🚫 У вас нет доступа к админ-панели.')
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='🗑️ Удалить пользователя', callback_data='admin:delete_user'),
            InlineKeyboardButton(text='📊 Статистика', callback_data='admin:stats')
        ],
        [
            InlineKeyboardButton(text='👁️ Просмотреть пользователя', callback_data='admin:view_user'),
            InlineKeyboardButton(text='🔄 Модерация', callback_data='admin:moderation')
        ]
    ])

    await message.answer(
        '👑 Панель администратора\n\n'
        'Выберите действие:',
        reply_markup=kb
    )


@router.callback_query(F.data == 'admin:delete_user')
async def admin_delete_user(callback: types.CallbackQuery, state: FSMContext):
    """Начать процесс удаления пользователя"""
    if callback.from_user.id not in cfg.admin_ids:
        await callback.answer('Нет доступа')
        return

    await callback.message.answer(
        'Введите Telegram ID пользователя для удаления:\n\n'
        'Пример: 123456789\n\n'
        'Или отправьте /cancel для отмены.'
    )
    await state.set_state(AdminDeleteUser.WAITING_FOR_USER_ID)
    await callback.answer()


@router.message(AdminDeleteUser.WAITING_FOR_USER_ID)
async def admin_get_user_id(message: types.Message, state: FSMContext):
    """Получить ID пользователя для удаления"""
    if message.text == '/cancel':
        await state.clear()
        await message.answer('❌ Удаление отменено.')
        return

    try:
        tg_id = int(message.text)
    except ValueError:
        await message.answer('❌ Пожалуйста, введите корректный числовой ID.')
        return

    # Проверяем, существует ли пользователь
    user = await storage.get_user_by_tg(tg_id)

    if not user:
        await message.answer(f'❌ Пользователь с ID {tg_id} не найден.')
        await state.clear()
        return

    # Сохраняем данные и запрашиваем подтверждение
    await state.update_data(tg_id=tg_id, user_name=user.name)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='✅ Да, удалить', callback_data='admin:confirm_delete'),
            InlineKeyboardButton(text='❌ Нет, отменить', callback_data='admin:cancel_delete')
        ]
    ])

    await message.answer(
        f'⚠️ Вы уверены, что хотите удалить пользователя?\n\n'
        f'👤 Имя: {user.name}\n'
        f'🆔 Telegram ID: {user.tg_id}\n'
        f'🆔 Внутренний ID: {user.id}\n'
        f'📅 Возраст: {user.age}\n'
        f'⚧️ Пол: {user.gender}\n\n'
        f'❗ Это действие удалит:\n'
        f'• Анкету пользователя\n'
        f'• Все лайки этого пользователя\n'
        f'• Все записи модерации\n'
        f'❗ Действие необратимо!',
        reply_markup=kb
    )
    await state.set_state(AdminDeleteUser.WAITING_FOR_CONFIRMATION)


@router.callback_query(F.data == 'admin:confirm_delete', AdminDeleteUser.WAITING_FOR_CONFIRMATION)
async def admin_confirm_delete(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления пользователя"""
    if callback.from_user.id not in cfg.admin_ids:
        await callback.answer('Нет доступа')
        return

    data = await state.get_data()
    tg_id = data['tg_id']
    user_name = data['user_name']

    # Удаляем пользователя
    success = await storage.delete_user_by_tg(tg_id)

    if success:
        await callback.message.answer(
            f'✅ Пользователь "{user_name}" (ID: {tg_id}) успешно удален.'
        )
    else:
        await callback.message.answer(
            f'❌ Не удалось удалить пользователя {user_name} (ID: {tg_id}).'
        )

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == 'admin:cancel_delete')
async def admin_cancel_delete(callback: types.CallbackQuery, state: FSMContext):
    """Отмена удаления пользователя"""
    await state.clear()
    await callback.message.answer('❌ Удаление отменено.')
    await callback.answer()


@router.callback_query(F.data == 'admin:stats')
async def admin_stats(callback: types.CallbackQuery):
    """Статистика системы"""
    if callback.from_user.id not in cfg.admin_ids:
        await callback.answer('Нет доступа')
        return

    from ..database.sqlite import db
    import sqlite3

    def _get_stats():
        with sqlite3.connect(str(db.db_path)) as conn:
            cursor = conn.cursor()

            # Общая статистика
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
            active_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM likes")
            total_likes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM likes WHERE is_mutual = TRUE")
            mutual_likes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM moderation")
            total_moderation = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM moderation WHERE status = 'pending'")
            pending_moderation = cursor.fetchone()[0]

            # Последние регистрации
            cursor.execute("""
                SELECT name, tg_id, created_at 
                FROM users 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            recent_users = cursor.fetchall()

            return {
                'total_users': total_users,
                'active_users': active_users,
                'total_likes': total_likes,
                'mutual_likes': mutual_likes,
                'total_moderation': total_moderation,
                'pending_moderation': pending_moderation,
                'recent_users': recent_users
            }

    stats = await asyncio.get_event_loop().run_in_executor(None, _get_stats)

    stats_text = (
        f'📊 Статистика системы\n\n'
        f'👤 Пользователи:\n'
        f'• Всего: {stats["total_users"]}\n'
        f'• Активных: {stats["active_users"]}\n\n'
        f'❤️ Лайки:\n'
        f'• Всего: {stats["total_likes"]}\n'
        f'• Взаимных: {stats["mutual_likes"]}\n\n'
        f'📷 Модерация:\n'
        f'• Всего записей: {stats["total_moderation"]}\n'
        f'• Ожидают проверки: {stats["pending_moderation"]}\n\n'
        f'🆕 Последние регистрации:\n'
    )

    for user in stats['recent_users']:
        stats_text += f'• {user[0]} (ID: {user[1]}) - {user[2][:10]}\n'

    await callback.message.answer(stats_text)
    await callback.answer()


@router.callback_query(F.data == 'admin:view_user')
async def admin_view_user(callback: types.CallbackQuery, state: FSMContext):
    """Просмотр информации о пользователе"""
    if callback.from_user.id not in cfg.admin_ids:
        await callback.answer('Нет доступа')
        return

    await callback.message.answer(
        'Введите Telegram ID пользователя для просмотра:\n\n'
        'Пример: 123456789\n\n'
        'Или отправьте /cancel для отмены.'
    )
    await callback.answer()


@router.message(Command('viewuser'))
async def cmd_viewuser(message: types.Message):
    """Команда для просмотра информации о пользователе"""
    if message.from_user.id not in cfg.admin_ids:
        await message.answer('🚫 У вас нет доступа.')
        return

    if len(message.text.split()) < 2:
        await message.answer('Использование: /viewuser <telegram_id>')
        return

    try:
        tg_id = int(message.text.split()[1])
    except ValueError:
        await message.answer('❌ Пожалуйста, введите корректный числовой ID.')
        return

    user = await storage.get_user_by_tg(tg_id)

    if not user:
        await message.answer(f'❌ Пользователь с ID {tg_id} не найден.')
        return

    user_info = (
        f'👤 Информация о пользователе:\n\n'
        f'🆔 Внутренний ID: {user.id}\n'
        f'📱 Telegram ID: {user.tg_id}\n'
        f'👤 Имя: {user.name}\n'
        f'🎂 Возраст: {user.age}\n'
        f'⚧️ Пол: {user.gender}\n'
        f'🎯 Цель: {user.goal}\n'
        f'📝 Описание: {user.description[:100]}{"..." if len(user.description) > 100 else ""}\n'
        f'✅ Активен: {"Да" if user.is_active else "Нет"}\n'
        f'📷 Фото: {"Есть" if user.photo_file_id else "Нет"}\n'
    )

    # Получаем статистику лайков
    from ..database.sqlite import db
    import sqlite3

    def _get_likes_stats():
        with sqlite3.connect(str(db.db_path)) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM likes WHERE from_user_id = ?", (user.id,))
            likes_given = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM likes WHERE to_user_id = ?", (user.id,))
            likes_received = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM likes WHERE (from_user_id = ? OR to_user_id = ?) AND is_mutual = TRUE",
                           (user.id, user.id))
            mutual_likes = cursor.fetchone()[0]

            return likes_given, likes_received, mutual_likes

    likes_given, likes_received, mutual_likes = await asyncio.get_event_loop().run_in_executor(None, _get_likes_stats)

    user_info += (
        f'\n❤️ Лайки:\n'
        f'• Отправлено: {likes_given}\n'
        f'• Получено: {likes_received}\n'
        f'• Взаимных: {mutual_likes}\n'
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='🗑️ Удалить пользователя',
                                 callback_data=f'admin:quick_delete:{user.tg_id}')
        ]
    ])

    await message.answer(user_info, reply_markup=kb)


@router.callback_query(F.data.startswith('admin:quick_delete:'))
async def admin_quick_delete(callback: types.CallbackQuery):
    """Быстрое удаление пользователя"""
    if callback.from_user.id not in cfg.admin_ids:
        await callback.answer('Нет доступа')
        return

    tg_id = int(callback.data.split(':')[2])

    # Получаем пользователя для отображения имени
    user = await storage.get_user_by_tg(tg_id)

    if not user:
        await callback.answer('Пользователь не найден')
        return

    # Удаляем пользователя
    success = await storage.delete_user_by_tg(tg_id)

    if success:
        await callback.message.answer(
            f'✅ Пользователь "{user.name}" (ID: {tg_id}) успешно удален.'
        )
    else:
        await callback.message.answer(
            f'❌ Не удалось удалить пользователя {user.name} (ID: {tg_id}).'
        )

    await callback.answer()


@router.callback_query(F.data == 'admin:moderation')
async def admin_moderation(callback: types.CallbackQuery):
    """Переход к модерации"""
    if callback.from_user.id not in cfg.admin_ids:
        await callback.answer('Нет доступа')
        return

    await callback.message.answer('Используйте команду /moderate для модерации фото.')
    await callback.answer()


@router.message(Command('deleteuser'))
async def cmd_deleteuser(message: types.Message):
    """Команда для быстрого удаления пользователя"""
    if message.from_user.id not in cfg.admin_ids:
        await message.answer('🚫 У вас нет доступа.')
        return

    if len(message.text.split()) < 2:
        await message.answer('Использование: /deleteuser <telegram_id>')
        return

    try:
        tg_id = int(message.text.split()[1])
    except ValueError:
        await message.answer('❌ Пожалуйста, введите корректный числовой ID.')
        return

    # Получаем пользователя для отображения имени
    user = await storage.get_user_by_tg(tg_id)

    if not user:
        await message.answer(f'❌ Пользователь с ID {tg_id} не найден.')
        return

    # Удаляем пользователя
    success = await storage.delete_user_by_tg(tg_id)

    if success:
        await message.answer(
            f'✅ Пользователь "{user.name}" (ID: {tg_id}) успешно удален.'
        )
    else:
        await message.answer(
            f'❌ Не удалось удалить пользователя {user.name} (ID: {tg_id}).'
        )


