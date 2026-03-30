# reset_all_users.py
import sqlite3
import hashlib
import json
from datetime import datetime


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


print("🔧 ПОЛНОЕ ОБНОВЛЕНИЕ ПОЛЬЗОВАТЕЛЕЙ")
print("=" * 60)
print("⚠️ ВНИМАНИЕ: Это удалит всех существующих соискателей и создаст новых!")
print("   Администратор, работодатели и кураторы останутся.")
print("=" * 60)

confirm = input("Продолжить? (да/нет): ")
if confirm.lower() != 'да':
    print("Отменено.")
    exit()

conn = sqlite3.connect('tramplin.db')
cursor = conn.cursor()

# ========== 1. СОХРАНЯЕМ ВАЖНЫХ ПОЛЬЗОВАТЕЛЕЙ ==========
print("\n📋 Сохраняем администраторов, работодателей и кураторов...")

# Получаем ID пользователей, которых НЕ УДАЛЯЕМ
cursor.execute("SELECT id FROM users WHERE role IN ('admin', 'employer', 'curator')")
keep_users = [row[0] for row in cursor.fetchall()]
print(f"   Сохраняем пользователей: {keep_users}")

# ========== 2. УДАЛЯЕМ ВСЕХ СОИСКАТЕЛЕЙ ==========
print("\n📋 Удаление всех соискателей...")

# Удаляем связи
cursor.execute("DELETE FROM connections WHERE seeker_id IN (SELECT id FROM seeker_profiles)")
cursor.execute("DELETE FROM connections WHERE friend_id IN (SELECT id FROM seeker_profiles)")
print("   ✅ Удалены связи")

# Удаляем отклики
cursor.execute("DELETE FROM responses WHERE seeker_id IN (SELECT id FROM seeker_profiles)")
print("   ✅ Удалены отклики")

# Удаляем избранное
cursor.execute("DELETE FROM favorites WHERE seeker_id IN (SELECT id FROM seeker_profiles)")
print("   ✅ Удалено избранное")

# Удаляем уведомления
cursor.execute("DELETE FROM notifications WHERE user_id IN (SELECT user_id FROM seeker_profiles)")
print("   ✅ Удалены уведомления")

# Удаляем сообщения
cursor.execute("DELETE FROM messages WHERE sender_id IN (SELECT user_id FROM seeker_profiles)")
cursor.execute("DELETE FROM messages WHERE receiver_id IN (SELECT user_id FROM seeker_profiles)")
print("   ✅ Удалены сообщения")

# Удаляем регистрации на мероприятия
cursor.execute("DELETE FROM event_registrations WHERE user_id IN (SELECT user_id FROM seeker_profiles)")
print("   ✅ Удалены регистрации на мероприятия")

# Удаляем профили соискателей
cursor.execute("DELETE FROM seeker_profiles")
print("   ✅ Удалены профили соискателей")

# Удаляем самих пользователей-соискателей
cursor.execute("DELETE FROM users WHERE role='seeker'")
print("   ✅ Удалены пользователи-соискатели")

# ========== 3. СОЗДАЁМ НОВЫХ СОИСКАТЕЛЕЙ ==========
print("\n📋 Создание новых соискателей...")

# Создаём пользователей
users_data = [
    ('alex@test.ru', 'alex', 'Алексей Смирнов', 'МГУ', '4 курс', 2025, 'Люблю программировать на Python',
     ['Python', 'Django', 'SQL']),
    ('maria@test.ru', 'maria', 'Мария Иванова', 'СПбГУ', '3 курс', 2026, 'Интересуюсь веб-разработкой',
     ['JavaScript', 'React', 'HTML/CSS']),
    ('dmitry@test.ru', 'dmitry', 'Дмитрий Петров', 'МФТИ', '2 курс', 2027, 'Машинное обучение и AI',
     ['Python', 'TensorFlow', 'Pandas']),
    ('elena@test.ru', 'elena', 'Елена Соколова', 'ВШЭ', '4 курс', 2025, 'Ищу стажировку в IT',
     ['Java', 'Spring', 'PostgreSQL']),
    ('ivan@test.ru', 'ivan', 'Иван Козлов', 'ИТМО', '3 курс', 2026, 'Frontend разработчик',
     ['JavaScript', 'Vue.js', 'CSS']),
    ('olga@test.ru', 'olga', 'Ольга Новикова', 'КФУ', '1 курс', 2029, 'Начинающий разработчик', ['C++', 'Python']),
]

created_users = []
for email, username, full_name, uni, course, year, about, skills_list in users_data:
    # Создаём пользователя
    user_id = cursor.execute("""
        INSERT INTO users (email, username, password_hash, role, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
    email, username, hash_password('123456'), 'seeker', 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))).lastrowid

    # Создаём профиль
    cursor.execute("""
        INSERT INTO seeker_profiles (user_id, full_name, university, course, graduation_year, about, skills, privacy_settings)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, full_name, uni, course, year, about, json.dumps(skills_list), '{"show_profile": true}'))

    created_users.append((username, full_name, user_id))
    print(f"   ✅ Создан: {username} ({full_name})")

conn.commit()
conn.close()

print("\n" + "=" * 60)
print("✅ ПОЛЬЗОВАТЕЛИ ОБНОВЛЕНЫ!")
print("=" * 60)
print("\n📋 НОВЫЕ СОИСКАТЕЛИ:")
print("   Логин       | Пароль   | Имя")
print("   ------------|----------|------------------")
for username, full_name, uid in created_users:
    print(f"   {username:<12} | 123456   | {full_name}")

print("\n👤 АДМИНИСТРАТОР:")
print("   admin / admin123")

print("\n👔 РАБОТОДАТЕЛЬ:")
print("   testemployer / employer123")

print("\n🛡️ КУРАТОР:")
print("   testcurator / curator123")

print("\n🔄 Перезапустите сервер: python main.py")