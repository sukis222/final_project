
import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional


class SQLiteDatabase:
    def __init__(self, db_path: str | Path | None = None):
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.db_path = Path(db_path) if db_path else base_dir / 'dating_bot.db'
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.init_db()



    async def delete_user(self, user_id: int) -> bool:
        """Удалить пользователя по ID"""

        def _delete():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Удаляем пользователя и все связанные данные (каскадное удаление)
                cursor.execute('DELETE FROM likes WHERE from_user_id = ? OR to_user_id = ?',
                               (user_id, user_id))
                cursor.execute('DELETE FROM moderation WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))

                conn.commit()
                return cursor.rowcount > 0

        return await asyncio.get_event_loop().run_in_executor(self.executor, _delete)

    async def delete_user_by_tg_id(self, tg_id: int) -> bool:
        """Удалить пользователя по Telegram ID"""

        def _delete():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Сначала получаем ID пользователя
                cursor.execute('SELECT id FROM users WHERE tg_id = ?', (tg_id,))
                user = cursor.fetchone()

                if not user:
                    return False

                user_id = user[0]

                # Удаляем связанные данные
                cursor.execute('DELETE FROM likes WHERE from_user_id = ? OR to_user_id = ?',
                               (user_id, user_id))
                cursor.execute('DELETE FROM moderation WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM users WHERE tg_id = ?', (tg_id,))

                conn.commit()
                return cursor.rowcount > 0

        return await asyncio.get_event_loop().run_in_executor(self.executor, _delete)




    async def get_moderation_by_id(self, moderation_id: int) -> Optional[Dict[str, Any]]:
        def _get():
            with sqlite3.connect(self.db_path) as conn:
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

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

    async def get_pending_moderation_by_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        def _get():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                        SELECT m.*, u.name as user_name, u.tg_id as user_tg_id
                        FROM moderation m
                        JOIN users u ON m.user_id = u.id
                        WHERE m.user_id = ? AND m.status = 'pending'
                        ORDER BY m.created_at DESC
                        LIMIT 1
                    ''', (user_id,))
                item = cursor.fetchone()
                return dict(item) if item else None

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)



    # В класс SQLiteDatabase добавьте:
    async def get_moderation_by_id(self, moderation_id: int) -> Optional[Dict[str, Any]]:
        def _get():
            with sqlite3.connect(self.db_path) as conn:
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

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

    def init_db(self):
        """Инициализация базы данных и создание таблиц"""

        def _init():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Таблица пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tg_id INTEGER UNIQUE NOT NULL,
                        name TEXT NOT NULL DEFAULT '',
                        age INTEGER,
                        gender TEXT,
                        photo_file_id TEXT,
                        goal TEXT,
                        description TEXT,
                        is_active BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Таблица лайков
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS likes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        from_user_id INTEGER NOT NULL,
                        to_user_id INTEGER NOT NULL,
                        is_mutual BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (from_user_id) REFERENCES users (id),
                        FOREIGN KEY (to_user_id) REFERENCES users (id),
                        UNIQUE(from_user_id, to_user_id)
                    )
                ''')

                # Таблица модерации
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS moderation (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        photo_file_id TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        UNIQUE(user_id, photo_file_id)
                    )
                ''')

                conn.commit()

        loop = asyncio.get_event_loop()
        loop.run_in_executor(self.executor, _init)

    # === Пользователи ===

    async def create_or_get_user(self, tg_id: int) -> Dict[str, Any]:
        def _create_or_get():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Проверяем, существует ли пользователь
                cursor.execute('SELECT * FROM users WHERE tg_id = ?', (tg_id,))
                user = cursor.fetchone()

                if user:
                    return dict(user)
                else:
                    # Создаем нового пользователя
                    cursor.execute('''
                        INSERT INTO users (tg_id, name, is_active)
                        VALUES (?, '', FALSE)
                    ''', (tg_id,))
                    user_id = cursor.lastrowid

                    # Получаем созданного пользователя
                    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
                    new_user = cursor.fetchone()
                    conn.commit()
                    return dict(new_user)

        return await asyncio.get_event_loop().run_in_executor(self.executor, _create_or_get)

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        def _get():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
                user = cursor.fetchone()
                return dict(user) if user else None

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

    async def get_user_by_tg(self, tg_id: int) -> Optional[Dict[str, Any]]:
        def _get():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE tg_id = ?', (tg_id,))
                user = cursor.fetchone()
                return dict(user) if user else None

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

    async def update_user(self, user_id: int, **kwargs):
        def _update():
            if not kwargs:
                return

            set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values())
            values.append(user_id)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE users 
                    SET {set_clause}
                    WHERE id = ?
                ''', values)
                conn.commit()

        await asyncio.get_event_loop().run_in_executor(self.executor, _update)

    async def get_all_active_users(self) -> List[Dict[str, Any]]:
        def _get():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE is_active = TRUE')
                users = cursor.fetchall()
                return [dict(user) for user in users]

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

    # === Лайки ===

    async def add_like(self, from_user_id: int, to_user_id: int) -> Dict[str, Any]:
        def _add():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Проверяем, существует ли уже такой лайк
                cursor.execute('''
                    SELECT * FROM likes 
                    WHERE from_user_id = ? AND to_user_id = ?
                ''', (from_user_id, to_user_id))

                existing_like = cursor.fetchone()

                if existing_like:
                    return dict(existing_like)

                # Создаем новый лайк
                cursor.execute('''
                    INSERT INTO likes (from_user_id, to_user_id, is_mutual)
                    VALUES (?, ?, FALSE)
                ''', (from_user_id, to_user_id))

                like_id = cursor.lastrowid

                # Проверяем на взаимный лайк
                cursor.execute('''
                    SELECT * FROM likes 
                    WHERE from_user_id = ? AND to_user_id = ?
                ''', (to_user_id, from_user_id))

                mutual_like = cursor.fetchone()

                if mutual_like:
                    # Обновляем оба лайка как взаимные
                    cursor.execute('''
                        UPDATE likes 
                        SET is_mutual = TRUE 
                        WHERE id IN (?, ?)
                    ''', (like_id, mutual_like['id']))

                # Получаем созданный лайк
                cursor.execute('SELECT * FROM likes WHERE id = ?', (like_id,))
                new_like = cursor.fetchone()
                conn.commit()
                return dict(new_like)

        return await asyncio.get_event_loop().run_in_executor(self.executor, _add)

    async def has_liked(self, from_user_id: int, to_user_id: int) -> bool:
        def _check():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 1 FROM likes 
                    WHERE from_user_id = ? AND to_user_id = ?
                ''', (from_user_id, to_user_id))
                return cursor.fetchone() is not None

        return await asyncio.get_event_loop().run_in_executor(self.executor, _check)

    async def get_likes_to_user(self, user_id: int) -> List[Dict[str, Any]]:
        def _get():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT l.*, u.name as from_user_name, u.age as from_user_age
                    FROM likes l
                    JOIN users u ON l.from_user_id = u.id
                    WHERE l.to_user_id = ?
                    ORDER BY l.created_at DESC
                ''', (user_id,))

                likes = cursor.fetchall()
                return [dict(like) for like in likes]

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

    # === Модерация ===

    async def add_moderation(self, user_id: int, photo_file_id: str):
        def _add():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Сначала проверяем, есть ли уже такая запись
                cursor.execute('''
                    SELECT 1 FROM moderation 
                    WHERE user_id = ? AND photo_file_id = ? AND status = 'pending'
                ''', (user_id, photo_file_id))

                if cursor.fetchone():
                    return  # Уже есть ожидающая модерации запись

                # Добавляем новую запись
                cursor.execute('''
                    INSERT INTO moderation (user_id, photo_file_id, status)
                    VALUES (?, ?, 'pending')
                ''', (user_id, photo_file_id))
                conn.commit()

        await asyncio.get_event_loop().run_in_executor(self.executor, _add)

    async def get_pending_moderation(self) -> Optional[Dict[str, Any]]:
        def _get():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT m.*, u.name as user_name, u.tg_id as user_tg_id
                    FROM moderation m
                    JOIN users u ON m.user_id = u.id
                    WHERE m.status = 'pending'
                    ORDER BY m.created_at ASC
                    LIMIT 1
                ''')

                item = cursor.fetchone()
                return dict(item) if item else None

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

    async def set_moderation_status(self, user_id: int, photo_file_id: str, status: str) -> Optional[Dict[str, Any]]:
        def _set():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Находим ожидающую модерацию запись для данного фото
                cursor.execute('''
                    SELECT * FROM moderation 
                    WHERE user_id = ? AND photo_file_id = ? AND status = 'pending'
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (user_id, photo_file_id))

                item = cursor.fetchone()

                if item:
                    # Обновляем статус
                    cursor.execute('''
                        UPDATE moderation 
                        SET status = ?
                        WHERE id = ?
                    ''', (status, item['id']))

                    # Получаем обновленную запись
                    cursor.execute('SELECT * FROM moderation WHERE id = ?', (item['id'],))
                    updated_item = cursor.fetchone()
                    conn.commit()
                    return dict(updated_item)

                return None

        return await asyncio.get_event_loop().run_in_executor(self.executor, _set)

    async def get_user_moderation_status(self, user_id: int) -> Optional[str]:
        def _get():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT status FROM moderation 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', (user_id,))

                result = cursor.fetchone()
                return result[0] if result else None

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

    async def get_moderation_by_user_and_photo(self, user_id: int, photo_file_id: str) -> Optional[Dict[str, Any]]:
        def _get():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM moderation 
                    WHERE user_id = ? AND photo_file_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (user_id, photo_file_id))

                item = cursor.fetchone()
                return dict(item) if item else None

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

    async def update_user_photo(self, user_id: int, photo_file_id: str):
        def _update():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET photo_file_id = ?, is_active = TRUE
                    WHERE id = ?
                ''', (photo_file_id, user_id))
                conn.commit()

        await asyncio.get_event_loop().run_in_executor(self.executor, _update)

    async def get_any_candidate(self, current_user_id: int) -> Optional[Dict[str, Any]]:
        """Получить любого активного кандидата"""

        def _get():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Получаем текущего пользователя
                cursor.execute(
                    'SELECT * FROM users WHERE id = ? AND is_active = TRUE',
                    (current_user_id,)
                )
                current_user = cursor.fetchone()

                if not current_user:
                    return None

                current_gender = current_user['gender']

                # Базовый запрос
                query = '''
                    SELECT u.*
                    FROM users u
                    WHERE u.is_active = TRUE
                    AND u.id != ?
                    AND NOT EXISTS (
                        SELECT 1
                        FROM likes l
                        WHERE l.from_user_id = ?
                        AND l.to_user_id = u.id
                    )
                '''

                params = [current_user_id, current_user_id]

                # Фильтр по полу
                if current_gender == 'Мужской':
                    query += ' AND u.gender = ?'
                    params.append('Женский')
                elif current_gender == 'Женский':
                    query += ' AND u.gender = ?'
                    params.append('Мужской')

                query += ' ORDER BY u.created_at DESC LIMIT 1'

                cursor.execute(query, params)
                candidate = cursor.fetchone()

                # Если не нашли с учетом пола, ищем любого
                if not candidate:
                    cursor.execute('''
                        SELECT u.*
                        FROM users u
                        WHERE u.is_active = TRUE
                        AND u.id != ?
                        AND NOT EXISTS (
                            SELECT 1
                            FROM likes l
                            WHERE l.from_user_id = ?
                            AND l.to_user_id = u.id
                        )
                        ORDER BY u.created_at DESC
                        LIMIT 1
                    ''', (current_user_id, current_user_id))
                    candidate = cursor.fetchone()

                return dict(candidate) if candidate else None

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

    # === Поиск кандидатов ===
    # Добавил новый тест (Владимир) уже испрвил
    # === Поиск кандидатов ===
    async def get_next_candidate(self, current_user_id: int) -> Optional[Dict[str, Any]]:
        def _get():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Получаем текущего пользователя
                cursor.execute(
                    'SELECT * FROM users WHERE id = ? AND is_active = TRUE',
                    (current_user_id,)
                )
                current_user = cursor.fetchone()

                if not current_user:
                    return None

                current_gender = current_user['gender']
                current_goal = current_user['goal']

                # Базовый запрос
                query = '''
                    SELECT u.*
                    FROM users u
                    WHERE u.is_active = TRUE
                    AND u.id != ?
                    AND NOT EXISTS (
                        SELECT 1
                        FROM likes l
                        WHERE l.from_user_id = ?
                        AND l.to_user_id = u.id
                    )
                '''

                params = [current_user_id, current_user_id]

                # Фильтр по полу (показываем противоположный пол)
                if current_gender == 'Мужской':
                    query += ' AND u.gender = ?'
                    params.append('Женский')
                elif current_gender == 'Женский':
                    query += ' AND u.gender = ?'
                    params.append('Мужской')

                # Добавляем сортировку по цели
                # Сначала показываем пользователей с той же целью, потом всех остальных
                order_by = '''
                    ORDER BY 
                        CASE 
                            WHEN u.goal = ? THEN 1
                            ELSE 2
                        END,
                        u.created_at DESC
                '''

                if current_goal:
                    params.append(current_goal)
                else:
                    # Если у текущего пользователя нет цели, добавляем заглушку
                    params.append('')

                query += order_by
                query += ' LIMIT 1'

                cursor.execute(query, params)
                candidate = cursor.fetchone()
                return dict(candidate) if candidate else None

        return await asyncio.get_event_loop().run_in_executor(self.executor, _get)

# Создаем глобальный экземпляр базы данных
db = SQLiteDatabase()
