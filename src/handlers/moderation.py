
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import sqlite3
import asyncio

from ..config import cfg
from ..storage import storage

router = Router()


@router.message(Command('moderate'))
async def cmd_moderate(message: types.Message):
    if message.from_user.id not in cfg.admin_ids:
        await message.answer('🚫 У вас нет доступа к модерации.')
        return

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
                    'Пожалуйста, загрузите другое фото, чтобы активировать анкету.\n\n'
                    'Используйте кнопку "📝 Изменить анкету" для загрузки нового фото.'
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
        # Используем str(db.db_path) для получения пути к файлу
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


@router.message(Command('modstats'))
async def cmd_modstats(message: types.Message):
    """Статистика модерации"""
    if message.from_user.id not in cfg.admin_ids:
        await message.answer('🚫 У вас нет доступа к модерации.')
        return

    # Получаем статистику из базы данных
    from ..database.sqlite import db

    def _get_stats():
        # Используем str(db.db_path) для получения пути к файлу
        with sqlite3.connect(str(db.db_path)) as conn:
            cursor = conn.cursor()

            # Общее количество
            cursor.execute("SELECT COUNT(*) FROM moderation")
            total = cursor.fetchone()[0]

            # Ожидающие
            cursor.execute("SELECT COUNT(*) FROM moderation WHERE status = 'pending'")
            pending = cursor.fetchone()[0]

            # Одобренные
            cursor.execute("SELECT COUNT(*) FROM moderation WHERE status = 'approved'")
            approved = cursor.fetchone()[0]

            # Отклоненные
            cursor.execute("SELECT COUNT(*) FROM moderation WHERE status = 'rejected'")
            rejected = cursor.fetchone()[0]

            return total, pending, approved, rejected

    total, pending, approved, rejected = await asyncio.get_event_loop().run_in_executor(None, _get_stats)

    await message.answer(
        f'📊 Статистика модерации:\n\n'
        f'📁 Всего: {total}\n'
        f'⏳ Ожидают: {pending}\n'
        f'✅ Одобрено: {approved}\n'
        f'❌ Отклонено: {rejected}\n\n'
        f'Используйте /moderate для проверки фото\n'
        f'Используйте /modhelp для справки'
    )


@router.message(Command('modhelp'))
async def cmd_modhelp(message: types.Message):
    """Справка по модерации"""
    if message.from_user.id not in cfg.admin_ids:
        await message.answer('🚫 У вас нет доступа к модерации.')
        return

    await message.answer(
        '📋 Команды модератора:\n\n'
        '/moderate - Проверить следующее фото на модерацию\n'
        '/modstats - Статистика модерации\n'
        '/modhelp - Эта справка\n\n'
        '⚡ Фото появляются автоматически после нажатия кнопок "Одобрить" или "Отклонить"\n\n'
        '📌 Инструкция:\n'
        '1. Нажмите /moderate\n'
        '2. Просмотрите фото пользователя\n'
        '3. Нажмите "✅ Одобрить" или "❌ Отклонить"\n'
        '4. Следующее фото появится автоматически'
    )


# Команда для очистки ошибочных записей модерации
@router.message(Command('modclean'))
async def cmd_modclean(message: types.Message):
    """Очистка старых записей модерации"""
    if message.from_user.id not in cfg.admin_ids:
        await message.answer('🚫 У вас нет доступа.')
        return

    def _clean_old():
        from ..database.sqlite import db
        with sqlite3.connect(str(db.db_path)) as conn:
            cursor = conn.cursor()
            # Удаляем записи старше 30 дней
            cursor.execute("""
                DELETE FROM moderation 
                WHERE created_at < datetime('now', '-30 days')
                AND status != 'pending'
            """)
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    deleted = await asyncio.get_event_loop().run_in_executor(None, _clean_old)

    await message.answer(f'✅ Удалено {deleted} старых записей модерации.')


