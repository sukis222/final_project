from aiogram import Router, types,  F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import cfg
from storage import storage

router = Router()


@router.message(Command('moderate'))
async def cmd_moderate(message: types.Message):
    if message.from_user.id not in cfg.admin_ids:
        await message.answer('🚫 У вас нет доступа к модерации.')
        return

    item = storage.get_pending_moderation()

    if not item:
        await message.answer('✅ Нет фото на проверку.')
        return

    user = storage.get_user_by_id(item.user_id)

    if not user:
        await message.answer('Пользователь не найден')
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='✅ Одобрить', callback_data=f'mod:approve:{user.id}'),
            InlineKeyboardButton(text='❌ Отклонить', callback_data=f'mod:reject:{user.id}')
        ]
    ])

    caption = f"👤 Пользователь: {user.name} (ID: {user.id})"

    if item.photo_file_id:
        await message.answer_photo(
            photo=item.photo_file_id,
            caption=caption,
            reply_markup=kb
        )
    else:
        await message.answer('Фото не найдено.')


@router.callback_query(F.data.startswith('mod:'))
async def cb_mod(callback: types.CallbackQuery):
    if callback.from_user.id not in cfg.admin_ids:
        await callback.answer('Нет доступа')
        return

    data = callback.data
    _, action, uid = data.split(':')
    uid = int(uid)

    user = storage.get_user_by_id(uid)

    if action == 'approve':
        storage.set_moderation_status(uid, 'approved')
        await callback.answer('✅ Фото одобрено')

        # Уведомляем пользователя
        if user:
            await callback.message.bot.send_message(
                user.tg_id,
                '✅ Ваше фото одобрено модератором!\n'
                'Продолжайте создание анкеты.'
            )

    elif action == 'reject':
        storage.set_moderation_status(uid, 'rejected')
        await callback.answer('❌ Фото отклонено')

        # Уведомляем пользователя
        if user:
            await callback.message.bot.send_message(
                user.tg_id,
                '❌ Ваше фото не прошло модерацию.\n'
                'Пожалуйста, загрузите другое фото.'
            )

    # Убираем кнопки
    try:
        await callback.message.edit_reply_markup(None)
    except:
        pass

    # Проверяем следующее фото на модерацию
    next_item = storage.get_pending_moderation()
    if next_item:
        next_user = storage.get_user_by_id(next_item.user_id)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text='✅ Одобрить', callback_data=f'mod:approve:{next_user.id}'),
                InlineKeyboardButton(text='❌ Отклонить', callback_data=f'mod:reject:{next_user.id}')
            ]
        ])

        caption = f"👤 Пользователь: {next_user.name} (ID: {next_user.id})"

        await callback.message.answer_photo(
            photo=next_item.photo_file_id,
            caption=caption,
            reply_markup=kb
        )