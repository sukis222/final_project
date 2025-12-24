
from typing import Dict, List, Optional
from dataclasses import dataclass
from .database.sqlite import db  # Изменено с database.py на database_sqlite.py


@dataclass
class User:
    id: int  # SQLite ID
    tg_id: int
    name: str = ''
    age: int | None = None
    gender: str = ''
    photo_file_id: str | None = None
    goal: str = ''
    description: str = ''
    is_active: bool = False

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data['id'],
            tg_id=data['tg_id'],
            name=data['name'],
            age=data['age'],
            gender=data['gender'],
            photo_file_id=data['photo_file_id'],
            goal=data['goal'],
            description=data['description'],
            is_active=bool(data['is_active'])
        )


@dataclass
class Like:
    from_user_id: int
    to_user_id: int
    is_mutual: bool = False

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            from_user_id=data['from_user_id'],
            to_user_id=data['to_user_id'],
            is_mutual=bool(data['is_mutual'])
        )


@dataclass
class ModerationItem:
    id: int
    user_id: int
    photo_file_id: str
    status: str  # 'pending', 'approved', 'rejected'
    created_at: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data['id'],
            user_id=data['user_id'],
            photo_file_id=data['photo_file_id'],
            status=data['status'],
            created_at=data['created_at']
        )


class Storage:
    def __init__(self):
        pass

    async def delete_user(self, user_id: int) -> bool:
        """Удалить пользователя по ID"""
        return await db.delete_user(user_id)

    async def delete_user_by_tg(self, tg_id: int) -> bool:
        """Удалить пользователя по Telegram ID"""
        return await db.delete_user_by_tg_id(tg_id)

    async def get_moderation_by_id(self, moderation_id: int) -> Optional[ModerationItem]:
        """Получить запись модерации по ID"""
        data = await db.get_moderation_by_id(moderation_id)
        if data:
            return ModerationItem.from_dict(data)
        return None

    async def get_pending_moderation_by_user(self, user_id: int) -> Optional[ModerationItem]:
        """Получить ожидающую модерацию запись для пользователя"""
        data = await db.get_pending_moderation_by_user(user_id)
        if data:
            return ModerationItem.from_dict(data)
        return None

    async def get_any_candidate(self, current_user_id: int) -> Optional[User]:
        """Получить любого кандидата, даже если цели не совпадают"""
        data = await db.get_any_candidate(current_user_id)
        if data:
            return User.from_dict(data)
        return None



    async def get_moderation_by_id(self, moderation_id: int) -> Optional[ModerationItem]:
        """Получить запись модерации по ID"""
        data = await db.get_moderation_by_id(moderation_id)
        if data:
            return ModerationItem.from_dict(data)
        return None

    async def create_or_get_user(self, tg_id: int) -> User:
        data = await db.create_or_get_user(tg_id)
        return User.from_dict(data)

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        data = await db.get_user_by_id(user_id)
        if data:
            return User.from_dict(data)
        return None

    async def get_user_by_tg(self, tg_id: int) -> Optional[User]:
        data = await db.get_user_by_tg(tg_id)
        if data:
            return User.from_dict(data)
        return None

    async def save_user(self, user: User):
        """Сохранить или обновить пользователя"""
        await db.update_user(
            user.id,
            name=user.name,
            age=user.age,
            gender=user.gender,
            photo_file_id=user.photo_file_id,
            goal=user.goal,
            description=user.description,
            is_active=user.is_active
        )

    async def add_like(self, from_uid: int, to_uid: int) -> Like:
        data = await db.add_like(from_uid, to_uid)
        return Like.from_dict(data)

    async def add_skip(self, from_uid: int, to_uid: int) -> None:
        await db.add_skip(from_uid, to_uid)

    async def has_liked(self, from_uid: int, to_uid: int) -> bool:
        return await db.has_liked(from_uid, to_uid)

    async def get_likes_to_user(self, user_id: int) -> List[Dict]:
        """Получить всех, кто лайкнул пользователя"""
        return await db.get_likes_to_user(user_id)

    async def get_pending_moderation(self) -> Optional[ModerationItem]:
        """Получить первую фотографию на модерацию со статусом pending"""
        data = await db.get_pending_moderation()
        if data:
            return ModerationItem.from_dict(data)
        return None

    async def add_moderation(self, user_id: int, photo_file_id: str):
        """Добавить фото на модерацию"""
        await db.add_moderation(user_id, photo_file_id)

    async def set_moderation_status(self, user_id: int, photo_file_id: str, status: str) -> Optional[ModerationItem]:
        """Установить статус модерации для конкретного фото пользователя"""
        data = await db.set_moderation_status(user_id, photo_file_id, status)
        if data:
            return ModerationItem.from_dict(data)
        return None

    async def get_user_moderation_status(self, user_id: int) -> Optional[str]:
        """Получить статус модерации последней фотографии пользователя"""
        return await db.get_user_moderation_status(user_id)

    async def get_next_candidate(self, current_user_id: int) -> Optional[User]:
        data = await db.get_next_candidate(current_user_id)
        if data:
            return User.from_dict(data)
        return None

    async def get_moderation_by_user_and_photo(self, user_id: int, photo_file_id: str) -> Optional[ModerationItem]:
        """Получить запись модерации по user_id и photo_file_id"""
        data = await db.get_moderation_by_user_and_photo(user_id, photo_file_id)
        if data:
            return ModerationItem.from_dict(data)
        return None

    async def update_user_photo(self, user_id: int, photo_file_id: str):
        """Обновить фото пользователя после одобрения модерации"""
        await db.update_user_photo(user_id, photo_file_id)


# Создаем глобальный экземпляр хранилища
storage = Storage()
