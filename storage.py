from typing import Dict, List, Optional
from dataclasses import dataclass
from database_sqlite import db  # Изменено с database.py на database_sqlite.py


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
    user_id: int
    photo_file_id: str
    status: str  # 'pending', 'approved', 'rejected'

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            user_id=data['user_id'],
            photo_file_id=data['photo_file_id'],
            status=data['status']
        )


class Storage:
    def __init__(self):
        pass

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

    async def has_liked(self, from_uid: int, to_uid: int) -> bool:
        return await db.has_liked(from_uid, to_uid)

    async def get_likes_to_user(self, user_id: int) -> List[Dict]:
        """Получить всех, кто лайкнул пользователя"""
        return await db.get_likes_to_user(user_id)

    async def get_pending_moderation(self) -> Optional[ModerationItem]:
        data = await db.get_pending_moderation()
        if data:
            return ModerationItem.from_dict(data)
        return None

    async def add_moderation(self, user_id: int, photo_file_id: str):
        await db.add_moderation(user_id, photo_file_id)

    async def set_moderation_status(self, user_id: int, status: str):
        data = await db.set_moderation_status(user_id, status)
        if data:
            return ModerationItem.from_dict(data)
        return None

    async def get_user_moderation_status(self, user_id: int) -> Optional[str]:
        return await db.get_user_moderation_status(user_id)

    async def get_next_candidate(self, current_user_id: int) -> Optional[User]:
        data = await db.get_next_candidate(current_user_id)
        if data:
            return User.from_dict(data)
        return None


# Создаем глобальный экземпляр хранилища
storage = Storage()