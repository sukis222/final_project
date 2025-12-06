from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class User:
    id: int  # внутренний id
    tg_id: int
    name: str = ''
    age: int | None = None
    gender: str = ''
    photo_file_id: str | None = None
    goal: str = ''
    description: str = ''
    is_active: bool = False


@dataclass
class Like:
    from_user_id: int
    to_user_id: int
    is_mutual: bool = False


@dataclass
class ModerationItem:
    user_id: int
    photo_file_id: str
    status: str  # 'pending', 'approved', 'rejected'


class InMemoryStorage:
    def __init__(self):
        self._next_id = 1
        self.users: Dict[int, User] = {}
        self.tg_to_user: Dict[int, int] = {}  # tg_id -> user.id
        self.likes: List[Like] = []
        self.moderation: List[ModerationItem] = []

    def create_or_get_user(self, tg_id: int) -> User:
        if tg_id in self.tg_to_user:
            return self.users[self.tg_to_user[tg_id]]
        u = User(id=self._next_id, tg_id=tg_id)
        self.users[u.id] = u
        self.tg_to_user[tg_id] = u.id
        self._next_id += 1
        return u

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)

    def get_user_by_tg(self, tg_id: int) -> Optional[User]:
        uid = self.tg_to_user.get(tg_id)
        if uid:
            return self.users.get(uid)
        return None

    def save_user(self, user: User):
        self.users[user.id] = user

    # Likes
    def add_like(self, from_uid: int, to_uid: int) -> Like:
        like = Like(from_user_id=from_uid, to_user_id=to_uid, is_mutual=False)
        self.likes.append(like)
        # check mutual
        for l in self.likes:
            if l.from_user_id == to_uid and l.to_user_id == from_uid:
                l.is_mutual = True
                like.is_mutual = True
                break
        return like

    def has_liked(self, from_uid: int, to_uid: int) -> bool:
        return any(l.from_user_id == from_uid and l.to_user_id == to_uid for l in self.likes)

    def get_pending_moderation(self) -> Optional[ModerationItem]:
        for m in self.moderation:
            if m.status == 'pending':
                return m
        return None

    def add_moderation(self, user_id: int, photo_file_id: str):
        self.moderation.append(ModerationItem(user_id=user_id, photo_file_id=photo_file_id, status='pending'))

    def set_moderation_status(self, user_id: int, status: str):
        for m in self.moderation:
            if m.user_id == user_id and m.status == 'pending':
                m.status = status
                return m
        return None

    def get_user_moderation_status(self, user_id: int) -> Optional[str]:
        for m in self.moderation:
            if m.user_id == user_id:
                return m.status
        return None

    def get_next_candidate(self, current_user_id: int) -> Optional[User]:
        """Получить следующую анкету для просмотра"""
        current_user = self.get_user_by_id(current_user_id)
        if not current_user or not current_user.is_active:
            return None

        for uid, user in self.users.items():
            if (uid != current_user_id and
                    user.is_active and
                    not self.has_liked(current_user_id, uid) and
                    uid != current_user_id):
                return user
        return None


storage = InMemoryStorage()