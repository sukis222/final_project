# доп файл для просмтра БД
# что бы запустить  python view_database.pyпше


import sqlite3
from tabulate import tabulate


def view_database():
    # Подключаемся к базе данных
    conn = sqlite3.connect('dating_bot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 80)
    print("DATABASE CONTENT VIEWER")
    print("=" * 80)

    # 1. Показать таблицы
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\n📊 ТАБЛИЦЫ В БАЗЕ ДАННЫХ:")
    for table in tables:
        print(f"  - {table['name']}")

    print("\n" + "=" * 80)

    # 2. Показать пользователей
    print("\n👥 ПОЛЬЗОВАТЕЛИ:")
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    if users:
        # Преобразуем в список словарей для красивого вывода
        users_data = []
        for user in users:
            users_data.append({
                'ID': user['id'],
                'TG ID': user['tg_id'],
                'Имя': user['name'],
                'Возраст': user['age'],
                'Пол': user['gender'],
                'Цель': user['goal'],
                'Активен': '✅' if user['is_active'] else '❌'
            })

        print(tabulate(users_data, headers='keys', tablefmt='grid'))
    else:
        print("Нет пользователей")

    print("\n" + "=" * 80)

    # 3. Показать лайки
    print("\n❤️ ЛАЙКИ:")
    cursor.execute('''
        SELECT 
            l.id,
            l.from_user_id,
            u1.name as from_user_name,
            l.to_user_id,
            u2.name as to_user_name,
            l.is_mutual,
            l.created_at
        FROM likes l
        LEFT JOIN users u1 ON l.from_user_id = u1.id
        LEFT JOIN users u2 ON l.to_user_id = u2.id
        ORDER BY l.created_at DESC
    ''')
    likes = cursor.fetchall()

    if likes:
        likes_data = []
        for like in likes:
            likes_data.append({
                'ID': like['id'],
                'От': f"{like['from_user_name']} (ID: {like['from_user_id']})",
                'Кому': f"{like['to_user_name']} (ID: {like['to_user_id']})",
                'Взаимный': '✅' if like['is_mutual'] else '❌',
                'Дата': like['created_at']
            })

        print(tabulate(likes_data, headers='keys', tablefmt='grid'))
    else:
        print("Нет лайков")

    print("\n" + "=" * 80)

    # 4. Показать модерацию
    print("\n🖼️ МОДЕРАЦИЯ:")
    cursor.execute('''
        SELECT 
            m.id,
            m.user_id,
            u.name as user_name,
            m.status,
            m.created_at
        FROM moderation m
        LEFT JOIN users u ON m.user_id = u.id
        ORDER BY m.created_at DESC
    ''')
    moderation_items = cursor.fetchall()

    if moderation_items:
        mod_data = []
        for item in moderation_items:
            status_emoji = {
                'pending': '⏳',
                'approved': '✅',
                'rejected': '❌'
            }.get(item['status'], '❓')

            mod_data.append({
                'ID': item['id'],
                'Пользователь': f"{item['user_name']} (ID: {item['user_id']})",
                'Статус': f"{status_emoji} {item['status']}",
                'Дата': item['created_at']
            })

        print(tabulate(mod_data, headers='keys', tablefmt='grid'))
    else:
        print("Нет элементов модерации")

    print("\n" + "=" * 80)

    # 5. Статистика
    print("\n📈 СТАТИСТИКА:")

    # Количество пользователей
    cursor.execute("SELECT COUNT(*) as total_users FROM users")
    total_users = cursor.fetchone()['total_users']

    cursor.execute("SELECT COUNT(*) as active_users FROM users WHERE is_active = TRUE")
    active_users = cursor.fetchone()['active_users']

    cursor.execute("SELECT COUNT(*) as total_likes FROM likes")
    total_likes = cursor.fetchone()['total_likes']

    cursor.execute("SELECT COUNT(*) as mutual_likes FROM likes WHERE is_mutual = TRUE")
    mutual_likes = cursor.fetchone()['mutual_likes']

    print(f"Всего пользователей: {total_users}")
    print(f"Активных анкет: {active_users}")
    print(f"Всего лайков: {total_likes}")
    print(f"Взаимных лайков: {mutual_likes}")

    # Кто кого лайкнул (топ)
    cursor.execute('''
        SELECT 
            u.name as user_name,
            COUNT(l.id) as likes_given
        FROM users u
        LEFT JOIN likes l ON u.id = l.from_user_id
        GROUP BY u.id
        ORDER BY likes_given DESC
        LIMIT 5
    ''')
    top_likers = cursor.fetchall()

    print("\n🏆 ТОП-5 ПО ЛАЙКАМ (кто ставил):")
    for liker in top_likers:
        print(f"  {liker['user_name']}: {liker['likes_given']} лайков")

    cursor.execute('''
        SELECT 
            u.name as user_name,
            COUNT(l.id) as likes_received
        FROM users u
        LEFT JOIN likes l ON u.id = l.to_user_id
        GROUP BY u.id
        ORDER BY likes_received DESC
        LIMIT 5
    ''')
    top_liked = cursor.fetchall()

    print("\n⭐ ТОП-5 ПО ЛАЙКАМ (кого лайкали):")
    for liked in top_liked:
        print(f"  {liked['user_name']}: {liked['likes_received']} лайков")

    conn.close()


if __name__ == "__main__":
    view_database()