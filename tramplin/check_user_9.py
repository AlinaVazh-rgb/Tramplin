# check_user_9.py
import sqlite3

conn = sqlite3.connect('tramplin.db')
cursor = conn.cursor()

# Проверяем пользователя с id=9
cursor.execute("SELECT id, username, role FROM users WHERE id = 9")
user = cursor.fetchone()
if user:
    print(f"✅ Пользователь найден: ID={user[0]}, Логин={user[1]}, Роль={user[2]}")
    
    # Проверяем, есть ли профиль куратора
    cursor.execute("SELECT id FROM curator_profiles WHERE user_id = 9")
    profile = cursor.fetchone()
    if profile:
        print(f"✅ Профиль куратора существует: ID={profile[0]}")
    else:
        print("❌ Профиль куратора НЕ существует! Нужно создать.")
        
        # Создаем профиль куратора
        cursor.execute("""
            INSERT INTO curator_profiles (user_id, university, position) 
            VALUES (9, 'Администратор', 'Модератор')
        """)
        conn.commit()
        print("✅ Профиль куратора создан!")
else:
    print("❌ Пользователь с id=9 НЕ найден!")

conn.close()