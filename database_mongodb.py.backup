import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId


class MongoDB:
    def __init__(self):
        # Получаем строку подключения из переменных окружения или используем локальную
        mongodb_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
        database_name = os.getenv('MONGODB_DATABASE', 'dating_bot')

        # Создаем синхронное подключение для инициализации
        self.sync_client = MongoClient(mongodb_url)
        self.db = self.sync_client[database_name]

        # Создаем асинхронное подключение для операций
        self.async_client = AsyncIOMotorClient(mongodb_url)
        self.async_db = self.async_client[database_name]

        self.init_collections()

    def init_collections(self):
        """Инициализация коллекций и индексов"""
        # Коллекция пользователей
        users = self.db.users
        users.create_index([('tg_id', ASCENDING)], unique=True)
        users.create_index([('is_active', ASCENDING)])

        # Коллекция лайков
        likes = self.db.likes
        likes.create_index([('from_user_id', ASCENDING), ('to_user_id', ASCENDING)], unique=True)
        likes.create_index([('from_user_id', ASCENDING)])
        likes.create_index([('to_user_id', ASCENDING)])
        likes.create_index([('is_mutual', ASCENDING)])

        # Коллекция модерации
        moderation = self.db.moderation
        moderation.create_index([('user_id', ASCENDING)])
        moderation.create_index([('status', ASCENDING)])
        moderation.create_index([('created_at', ASCENDING)])

    # === Пользователи ===

    async def create_or_get_user(self, tg_id: int) -> Dict[str, Any]:
        """Создать или получить пользователя"""
        users = self.async_db.users

        # Пытаемся найти существующего пользователя
        user = await users.find_one({'tg_id': tg_id})

        if user:
            user['id'] = str(user['_id'])
            return user

        # Создаем нового пользователя
        new_user = {
            'tg_id': tg_id,
            'name': '',
            'age': None,
            'gender': '',
            'photo_file_id': None,
            'goal': '',
            'description': '',
            'is_active': False,
            'created_at': datetime.utcnow()
        }

        result = await users.insert_one(new_user)
        new_user['id'] = str(result.inserted_id)
        new_user['_id'] = result.inserted_id
        return new_user

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получить пользователя по ID"""
        try:
            users = self.async_db.users
            user = await users.find_one({'_id': ObjectId(user_id)})
            if user:
                user['id'] = str(user['_id'])
            return user
        except:
            return None

    async def get_user_by_tg(self, tg_id: int) -> Optional[Dict[str, Any]]:
        """Получить пользователя по Telegram ID"""
        users = self.async_db.users
        user = await users.find_one({'tg_id': tg_id})
        if user:
            user['id'] = str(user['_id'])
        return user

    async def update_user(self, user_id: str, **kwargs):
        """Обновить данные пользователя"""
        try:
            users = self.async_db.users
            await users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': kwargs}
            )
            return True
        except:
            return False

    async def get_all_active_users(self) -> List[Dict[str, Any]]:
        """Получить всех активных пользователей"""
        users = self.async_db.users
        cursor = users.find({'is_active': True})
        active_users = await cursor.to_list(length=None)

        for user in active_users:
            user['id'] = str(user['_id'])

        return active_users

    # === Лайки ===

    async def add_like(self, from_user_id: str, to_user_id: str) -> Dict[str, Any]:
        """Добавить лайк"""
        likes = self.async_db.likes

        # Проверяем, существует ли уже такой лайк
        existing_like = await likes.find_one({
            'from_user_id': from_user_id,
            'to_user_id': to_user_id
        })

        if existing_like:
            existing_like['id'] = str(existing_like['_id'])
            return existing_like

        # Создаем новый лайк
        new_like = {
            'from_user_id': from_user_id,
            'to_user_id': to_user_id,
            'is_mutual': False,
            'created_at': datetime.utcnow()
        }

        result = await likes.insert_one(new_like)
        new_like['id'] = str(result.inserted_id)
        new_like['_id'] = result.inserted_id

        # Проверяем на взаимный лайк
        mutual_like = await likes.find_one({
            'from_user_id': to_user_id,
            'to_user_id': from_user_id
        })

        if mutual_like:
            # Обновляем оба лайка как взаимные
            await likes.update_many(
                {
                    '_id': {'$in': [result.inserted_id, mutual_like['_id']]}
                },
                {'$set': {'is_mutual': True}}
            )
            new_like['is_mutual'] = True

        return new_like

    async def has_liked(self, from_user_id: str, to_user_id: str) -> bool:
        """Проверить, лайкал ли пользователь другого пользователя"""
        likes = self.async_db.likes
        like = await likes.find_one({
            'from_user_id': from_user_id,
            'to_user_id': to_user_id
        })
        return like is not None

    async def get_likes_to_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить все лайки, поставленные пользователю"""
        likes = self.async_db.likes
        cursor = likes.aggregate([
            {
                '$match': {'to_user_id': user_id}
            },
            {
                '$lookup': {
                    'from': 'users',
                    'localField': 'from_user_id',
                    'foreignField': '_id',
                    'as': 'from_user'
                }
            },
            {
                '$unwind': '$from_user'
            },
            {
                '$addFields': {
                    'from_user_name': '$from_user.name',
                    'from_user_age': '$from_user.age'
                }
            },
            {
                '$sort': {'created_at': -1}
            }
        ])

        likes_list = await cursor.to_list(length=None)
        for like in likes_list:
            like['id'] = str(like['_id'])
            like['from_user']['id'] = str(like['from_user']['_id'])

        return likes_list

    async def get_mutual_likes(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить взаимные лайки пользователя"""
        likes = self.async_db.likes
        cursor = likes.aggregate([
            {
                '$match': {
                    '$or': [
                        {'from_user_id': user_id},
                        {'to_user_id': user_id}
                    ],
                    'is_mutual': True
                }
            },
            {
                '$lookup': {
                    'from': 'users',
                    'let': {'other_user_id': {
                        '$cond': {
                            'if': {'$eq': ['$from_user_id', user_id]},
                            'then': '$to_user_id',
                            'else': '$from_user_id'
                        }
                    }},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {'$eq': ['$_id', '$$other_user_id']}
                            }
                        }
                    ],
                    'as': 'other_user'
                }
            },
            {
                '$unwind': '$other_user'
            },
            {
                '$addFields': {
                    'other_user_name': '$other_user.name',
                    'other_user_tg_id': '$other_user.tg_id'
                }
            }
        ])

        mutual_likes = await cursor.to_list(length=None)
        for like in mutual_likes:
            like['id'] = str(like['_id'])
            like['other_user']['id'] = str(like['other_user']['_id'])

        return mutual_likes

    # === Модерация ===

    async def add_moderation(self, user_id: str, photo_file_id: str):
        """Добавить фото на модерацию"""
        moderation = self.async_db.moderation
        await moderation.insert_one({
            'user_id': user_id,
            'photo_file_id': photo_file_id,
            'status': 'pending',
            'created_at': datetime.utcnow()
        })

    async def get_pending_moderation(self) -> Optional[Dict[str, Any]]:
        """Получить первый ожидающий модерацию элемент"""
        moderation = self.async_db.moderation
        item = await moderation.find_one(
            {'status': 'pending'},
            sort=[('created_at', 1)]
        )

        if item:
            # Получаем информацию о пользователе
            users = self.async_db.users
            user = await users.find_one({'_id': ObjectId(item['user_id'])})

            if user:
                item['id'] = str(item['_id'])
                item['user_name'] = user.get('name', '')
                item['user_tg_id'] = user.get('tg_id', '')

            return item

        return None

    async def set_moderation_status(self, user_id: str, status: str) -> Optional[Dict[str, Any]]:
        """Установить статус модерации для пользователя"""
        moderation = self.async_db.moderation

        # Находим последнюю ожидающую модерацию запись
        item = await moderation.find_one(
            {
                'user_id': user_id,
                'status': 'pending'
            },
            sort=[('created_at', -1)]
        )

        if item:
            # Обновляем статус
            await moderation.update_one(
                {'_id': item['_id']},
                {'$set': {'status': status}}
            )

            # Получаем обновленную запись
            updated_item = await moderation.find_one({'_id': item['_id']})
            updated_item['id'] = str(updated_item['_id'])

            # Получаем информацию о пользователе
            users = self.async_db.users
            user = await users.find_one({'_id': ObjectId(user_id)})

            if user:
                updated_item['user_name'] = user.get('name', '')
                updated_item['user_tg_id'] = user.get('tg_id', '')

            return updated_item

        return None

    async def get_user_moderation_status(self, user_id: str) -> Optional[str]:
        """Получить статус модерации для пользователя"""
        moderation = self.async_db.moderation
        item = await moderation.find_one(
            {'user_id': user_id},
            sort=[('created_at', -1)]
        )

        return item.get('status') if item else None

    # === Поиск кандидатов ===

    async def get_next_candidate(self, current_user_id: str) -> Optional[Dict[str, Any]]:
        """Получить следующего кандидата для просмотра"""
        users = self.async_db.users
        likes = self.async_db.likes

        # Получаем всех активных пользователей
        all_users = await users.find({'is_active': True}).to_list(length=None)

        for user in all_users:
            user_id_str = str(user['_id'])

            # Пропускаем текущего пользователя
            if user_id_str == current_user_id:
                continue

            # Проверяем, лайкал ли текущий пользователь этого кандидата
            has_liked = await likes.find_one({
                'from_user_id': current_user_id,
                'to_user_id': user_id_str
            })

            # Если еще не лайкал, возвращаем этого кандидата
            if not has_liked:
                user['id'] = user_id_str
                return user

        return None


# Создаем глобальный экземпляр базы данных
db = MongoDB()