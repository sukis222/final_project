from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import sqlite3
import asyncio

from ..config import cfg
from ..storage import storage

router = Router()


class AdminDeleteUser(StatesGroup):
    WAITING_FOR_CONFIRMATION = State()
    WAITING_FOR_USER_ID = State()


def get_admin_menu():
    """Меню админа"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="👤 Управление пользователями")],
            [KeyboardButton(text="📸 Модерация фото")],
            [KeyboardButton(text="🗑️ Очистка базы")],
            [KeyboardButton(text="👤 Выйти из режима админа")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )


def get_main_menu_for_admin():
    """Главное меню для админа в обычном режиме"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/admin - Войти в режим админа")]
        ],
        resize_keyboard=True
    )


@router.message(Command('admin'))
async def cmd_admin(message: types.Message):
    """Вход/выход из режима админа и панель администратора"""
    if message.from_user.id not in cfg.admin_ids:
        await message.answer('🚫 У вас нет прав администратора.')
        return

    # Проверяем, есть ли аргументы (если вызывается как /admin moderate)
    args = message.text.split()

    if len(args) > 1:
        # Если есть аргумент "moderate", сразу показываем модерацию
        if args[1].lower() == 'moderate':
            # Входим в режим админа
            cfg.toggle_admin_mode(message.from_user.id)
            await show_moderation_photo(message)
            return

    # Переключаем режим админа
    is_admin_mode = cfg.toggle_admin_mode(message.from_user.id)

    if is_admin_mode:
        await message.answer(
            '🔐 Вы вошли в режим администратора.\n\n'
            'Доступны следующие функции:',
            reply_markup=get_admin_menu()
        )
    else:
        await message.answer(
            '👤 Вы вышли из режима администратора.\n'
            'Возвращаю обычное меню...',
            reply_markup=get_main_menu_for_admin()
        )


async def show_moderation_photo(message: types.Message):
    """Показать фото на модерацию"""
    item = await storage.get_pending_moderation()

    if not item:
        await message.answer('✅ Нет фото на проверку.')
        return

    user = await storage.get_user_by_id(item.user_id)

    if not user:
        await message.answer('Пользователь не найден')
        return

    # Используем ID модерации вместо photo_file_id для callback_data
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='✅ Одобрить', callback_data=f'mod:approve:{item.id}'),
            InlineKeyboardButton(text='❌ Отклонить', callback_data=f'mod:reject:{item.id}')
        ]
    ])

    caption = (
        f"👤 Пользователь: {user.name} (ID: {user.id}, TG ID: {user.tg_id})\n"
        f"📅 Дата загрузки: {item.created_at}"
    )

    if item.photo_file_id:
        try:
            await message.answer_photo(
                photo=item.photo_file_id,
                caption=caption,
                reply_markup=kb
            )
        except Exception as e:
            await message.answer(
                f"Не удалось загрузить фото. Ошибка: {str(e)}\n\n{caption}\n"
                f"📷 ID фото: {item.photo_file_id[:50]}...",
                reply_markup=kb
            )
    else:
        await message.answer(
            f"⚠️ Фото не найдено в базе данных\n\n{caption}",
            reply_markup=kb
        )


@router.message(F.text == "📊 Статистика")
async def admin_stats(message: types.Message):
    """Показать статистику"""
    if not cfg.get_admin_mode(message.from_user.id):
        return

    from ..database.sqlite import db

    def _get_stats():
        with sqlite3.connect(str(db.db_path)) as conn:
            cursor = conn.cursor()

            # Статистика пользователей
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
            active_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users WHERE photo_file_id IS NOT NULL")
            users_with_photo = cursor.fetchone()[0]

            # Статистика лайков
            cursor.execute("SELECT COUNT(*) FROM likes")
            total_likes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM likes WHERE is_mutual = TRUE")
            mutual_likes = cursor.fetchone()[0]

            # Статистика модерации
            cursor.execute("SELECT COUNT(*) FROM moderation")
            total_mod = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM moderation WHERE status = 'pending'")
            pending_mod = cursor.fetchone()[0]

            return {
                'total_users': total_users,
                'active_users': active_users,
                'users_with_photo': users_with_photo,
                'total_likes': total_likes,
                'mutual_likes': mutual_likes,
                'total_mod': total_mod,
                'pending_mod': pending_mod
            }

    stats = await asyncio.get_event_loop().run_in_executor(None, _get_stats)

    stats_text = (
        '📊 Статистика бота:\n\n'
        f'👤 Пользователи:\n'
        f'  • Всего: {stats["total_users"]}\n'
        f'  • Активных: {stats["active_users"]}\n'
        f'  • С фото: {stats["users_with_photo"]}\n\n'
        f'❤️ Лайки:\n'
        f'  • Всего: {stats["total_likes"]}\n'
        f'  • Взаимных: {stats["mutual_likes"]}\n\n'
        f'📸 Модерация:\n'
        f'  • Всего фото: {stats["total_mod"]}\n'
        f'  • Ожидают: {stats["pending_mod"]}\n\n'
        f'Используйте кнопку "📸 Модерация фото" для проверки фото'
    )

    await message.answer(stats_text)


@router.message(F.text == "👤 Управление пользователями")
async def admin_users_management(message: types.Message):
    """Управление пользователями"""
    if not cfg.get_admin_mode(message.from_user.id):
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin:list_users"),
            # InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="admin:find_user")
        ],
        [
            InlineKeyboardButton(text="❌ Удалить пользователя", callback_data="admin:delete_user"),
            InlineKeyboardButton(text="🔄 Активировать/деактивировать", callback_data="admin:toggle_active")
        ]
    ])

    await message.answer(
        '👤 Управление пользователями:\n\n'
        'Выберите действие:',
        reply_markup=kb
    )


@router.message(F.text == "📸 Модерация фото")
async def admin_moderation(message: types.Message):
    """Модерация фото"""
    if not cfg.get_admin_mode(message.from_user.id):
        return

    await show_moderation_photo(message)


@router.message(F.text == "🗑️ Очистка базы")
async def admin_cleanup(message: types.Message):
    """Очистка базы данных"""
    if not cfg.get_admin_mode(message.from_user.id):
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🧹 Очистить старые записи", callback_data="admin:clean_old"),
            InlineKeyboardButton(text="❌ Удалить неактивных", callback_data="admin:clean_inactive")
        ],
        [
            InlineKeyboardButton(text="🖼️ Очистить неверные фото", callback_data="admin:clean_photos"),
            InlineKeyboardButton(text="📋 Статистика базы", callback_data="admin:db_stats")
        ]
    ])

    await message.answer(
        '🗑️ Очистка базы данных:\n\n'
        'Выберите действие:',
        reply_markup=kb
    )


@router.message(F.text == "👤 Выйти из режима админа")
async def admin_exit(message: types.Message):
    """Выход из режима админа"""
    if not cfg.get_admin_mode(message.from_user.id):
        return

    # Выходим из режима админа
    cfg.toggle_admin_mode(message.from_user.id)
    await message.answer(
        '👤 Вы вышли из режима администратора.',
        reply_markup=get_main_menu_for_admin()
    )


@router.callback_query(F.data.startswith('admin:'))
async def admin_callback_handler(callback: types.CallbackQuery):
    if not cfg.get_admin_mode(callback.from_user.id):
        await callback.answer('Нет доступа')
        return

    action = callback.data.split(':')[1]

    if action == 'list_users':
        from ..database.sqlite import db

        def _get_users():
            with sqlite3.connect(str(db.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tg_id, name, age, is_active, created_at 
                    FROM users 
                    ORDER BY created_at DESC 
                    LIMIT 20
                ''')
                users = cursor.fetchall()
                return [dict(user) for user in users]

        users = await asyncio.get_event_loop().run_in_executor(None, _get_users)

        if not users:
            await callback.answer('Нет пользователей')
            await callback.message.answer('В базе нет пользователей.')
            return

        text = "📋 Последние 20 пользователей:\n\n"
        for user in users:
            status = "✅" if user['is_active'] else "❌"
            text += f"{status} {user['name']} (ID: {user['id']}, TG: {user['tg_id']})\n"

        await callback.message.answer(text)
        await callback.answer()

    elif action == 'clean_photos':
        # Очистка неверных photo_file_id
        from ..database.sqlite import db

        def _clean_photos():
            with sqlite3.connect(str(db.db_path)) as conn:
                cursor = conn.cursor()
                # Обновляем записи с неверными photo_file_id
                cursor.execute("""
                    UPDATE users 
                    SET photo_file_id = NULL 
                    WHERE photo_file_id LIKE '%#%' 
                       OR photo_file_id LIKE 'http%'
                       OR LENGTH(photo_file_id) < 10
                """)
                cleaned = cursor.rowcount
                conn.commit()
                return cleaned

        cleaned = await asyncio.get_event_loop().run_in_executor(None, _clean_photos)
        await callback.message.answer(f'✅ Очищено {cleaned} неверных photo_file_id')
        await callback.answer()


@router.callback_query(F.data.startswith('mod:'))
async def cb_mod(callback: types.CallbackQuery):
    if callback.from_user.id not in cfg.admin_ids:
        await callback.answer('Нет доступа')
        return

    data = callback.data
    _, action, moderation_id = data.split(':')
    moderation_id = int(moderation_id)

    # Получаем запись модерации по ID
    moderation_item = await get_moderation_by_id(moderation_id)

    if not moderation_item:
        await callback.answer('Запись модерации не найдена')
        return

    user_id = moderation_item['user_id']
    photo_file_id = moderation_item['photo_file_id']

    # Обновляем статус модерации
    result = await storage.set_moderation_status(user_id, photo_file_id, action)

    if not result:
        await callback.answer('Ошибка при обновлении статуса модерации')
        return

    user = await storage.get_user_by_id(user_id)

    if action == 'approve':
        # Обновляем фото пользователя
        await storage.update_user_photo(user_id, photo_file_id)

        # Активируем анкету пользователя
        if user:
            user.is_active = True
            user.photo_file_id = photo_file_id
            await storage.save_user(user)

        await callback.answer('✅ Фото одобрено')

        # Уведомляем пользователя
        if user:
            try:
                await callback.message.bot.send_message(
                    user.tg_id,
                    '✅ Ваше фото одобрено модератором!\n'
                    'Ваша анкета теперь активна и видна другим пользователям.'
                )
            except Exception as e:
                print(f"Не удалось отправить уведомление пользователю {user.tg_id}: {e}")

    elif action == 'reject':
        await callback.answer('❌ Фото отклонено')

        # Уведомляем пользователя
        if user:
            try:
                await callback.message.bot.send_message(
                    user.tg_id,
                    '❌ Ваше фото не прошло модерацию.\n'
                    'Пожалуйста,используйте /start,чтобы создать новую анкету .\n\n'
                    # 'создать новую анкету '
                )
            except Exception as e:
                print(f"Не удалось отправить уведомление пользователю {user.tg_id}: {e}")

    # Убираем кнопки с текущего сообщения
    try:
        await callback.message.edit_reply_markup(None)
        action_text = "одобрено" if action == 'approve' else "отклонено"
        user_name = user.name if user else f"ID {user_id}"
        await callback.message.answer(f"✅ Фото {action_text} для пользователя {user_name}")
    except Exception as e:
        print(f"Ошибка при редактировании сообщения: {e}")

    # Проверяем следующее фото на модерацию
    await check_next_moderation(callback.message)


async def get_moderation_by_id(moderation_id: int):
    """Вспомогательная функция для получения записи модерации по ID"""
    from ..database.sqlite import db

    def _get():
        with sqlite3.connect(str(db.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.*, u.name as user_name, u.tg_id as user_tg_id
                FROM moderation m
                JOIN users u ON m.user_id = u.id
                WHERE m.id = ?
            ''', (moderation_id,))
            item = cursor.fetchone()
            return dict(item) if item else None

    return await asyncio.get_event_loop().run_in_executor(None, _get)


async def check_next_moderation(message: types.Message):
    """Проверить и отправить следующее фото на модерацию"""
    next_item = await storage.get_pending_moderation()

    if next_item:
        next_user = await storage.get_user_by_id(next_item.user_id)

        if next_user:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text='✅ Одобрить', callback_data=f'mod:approve:{next_item.id}'),
                    InlineKeyboardButton(text='❌ Отклонить', callback_data=f'mod:reject:{next_item.id}')
                ]
            ])

            caption = (
                f"👤 Пользователь: {next_user.name} (ID: {next_user.id}, TG ID: {next_user.tg_id})\n"
                f"📅 Дата загрузки: {next_item.created_at}"
            )

            try:
                await message.answer_photo(
                    photo=next_item.photo_file_id,
                    caption=caption,
                    reply_markup=kb
                )
            except Exception as e:
                await message.answer(
                    f"Не удалось загрузить следующее фото. Ошибка: {str(e)}\n\n{caption}\n"
                    f"📷 ID фото: {next_item.photo_file_id[:50]}...",
                    reply_markup=kb
                )
        else:
            await message.answer(f"⚠️ Не найден пользователь для модерации ID: {next_item.user_id}")


# Добавим команды для просмотра и удаления пользователей
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


# Обработчик для быстрого удаления через callback
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


# Добавим команду для получения справки по админ-командам
@router.message(Command('adminhelp'))
async def cmd_adminhelp(message: types.Message):
    """Справка по админ-командам"""
    if message.from_user.id not in cfg.admin_ids:
        await message.answer('🚫 У вас нет доступа к админ-панели.')
        return

    help_text = (
        '📋 Команды администратора:\n\n'
        '/admin - Войти/выйти из режима администратора\n'
        '/admin moderate - Быстрый переход к модерации фото\n'
        '/viewuser <telegram_id> - Просмотреть информацию о пользователе\n'
        '/deleteuser <telegram_id> - Удалить пользователя\n'
        '/adminhelp - Эта справка\n\n'

        '🔧 Функции в режиме админа:\n'
        '• 📊 Статистика - Общая статистика бота\n'
        '• 👤 Управление пользователями - Управление пользователями\n'
        '• 📸 Модерация фото - Проверка и одобрение фото\n'
        '• 🗑️ Очистка базы - Очистка базы данных\n'
        '• 👤 Выйти из режима админа - Выход из админ-панели\n\n'

        '⚠️ В режиме администратора нельзя искать анкеты.'
    )

    await message.answer(help_text)