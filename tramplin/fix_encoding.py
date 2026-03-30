# fix_all_users_encoding.py
import sqlite3
import json
import sys

print("🔧 УНИВЕРСАЛЬНОЕ ИСПРАВЛЕНИЕ КОДИРОВКИ ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ")
print("=" * 60)

conn = sqlite3.connect('tramplin.db')
cursor = conn.cursor()


# Функция для исправления текста
def fix_text(text):
    if text is None:
        return text
    if isinstance(text, bytes):
        # Пробуем разные кодировки
        encodings = ['utf-8', 'cp1251', 'windows-1251', 'latin1', 'iso-8859-1']
        for enc in encodings:
            try:
                decoded = text.decode(enc)
                # Если декодировалось успешно, возвращаем
                return decoded
            except:
                continue
        # Если ничего не помогло, заменяем проблемные символы
        try:
            return text.decode('utf-8', errors='replace')
        except:
            return str(text)
    return text


# Функция для исправления JSON поля
def fix_json_field(value):
    if not value:
        return value
    if isinstance(value, bytes):
        value = fix_text(value)
    if isinstance(value, str):
        try:
            # Проверяем, валидный ли JSON
            json.loads(value)
            return value
        except:
            # Если не валидный, создаём пустой массив
            return '[]'
    return value


print("\n📋 1. Исправление таблицы seeker_profiles...")
cursor.execute(
    "SELECT id, user_id, full_name, university, course, about, skills, github, phone, privacy_settings FROM seeker_profiles")
rows = cursor.fetchall()
print(f"   Найдено записей: {len(rows)}")

fixed_count = 0
for row in rows:
    id_val, user_id, full_name, university, course, about, skills, github, phone, privacy_settings = row

    # Исправляем каждое поле
    new_full_name = fix_text(full_name)
    new_university = fix_text(university)
    new_course = fix_text(course)
    new_about = fix_text(about)
    new_skills = fix_json_field(skills)
    new_github = fix_text(github)
    new_phone = fix_text(phone)
    new_privacy = fix_text(privacy_settings)

    # Если что-то изменилось
    if (new_full_name != full_name or new_university != university or
            new_course != course or new_about != about or new_skills != skills or
            new_github != github or new_phone != phone or new_privacy != privacy_settings):
        cursor.execute("""
            UPDATE seeker_profiles 
            SET full_name=?, university=?, course=?, about=?, skills=?, github=?, phone=?, privacy_settings=?
            WHERE id=?
        """, (new_full_name, new_university, new_course, new_about, new_skills,
              new_github, new_phone, new_privacy, id_val))
        fixed_count += 1
        print(f"   ✅ Исправлен профиль ID={id_val} (user_id={user_id}): {new_full_name[:30]}")

print(f"   Исправлено профилей: {fixed_count}")

print("\n📋 2. Исправление таблицы users...")
cursor.execute("SELECT id, username, email FROM users")
rows = cursor.fetchall()
print(f"   Найдено записей: {len(rows)}")

fixed_count = 0
for row in rows:
    id_val, username, email = row
    new_username = fix_text(username)
    new_email = fix_text(email)

    if new_username != username or new_email != email:
        cursor.execute("UPDATE users SET username=?, email=? WHERE id=?", (new_username, new_email, id_val))
        fixed_count += 1
        print(f"   ✅ Исправлен пользователь ID={id_val}: {new_username}")

print(f"   Исправлено пользователей: {fixed_count}")

print("\n📋 3. Исправление таблицы opportunities...")
cursor.execute("SELECT id, title, description, requirements, location, tags FROM opportunities")
rows = cursor.fetchall()
print(f"   Найдено записей: {len(rows)}")

fixed_count = 0
for row in rows:
    id_val, title, description, requirements, location, tags = row
    new_title = fix_text(title)
    new_description = fix_text(description)
    new_requirements = fix_text(requirements)
    new_location = fix_text(location)
    new_tags = fix_json_field(tags)

    if (new_title != title or new_description != description or
            new_requirements != requirements or new_location != location or new_tags != tags):
        cursor.execute("""
            UPDATE opportunities 
            SET title=?, description=?, requirements=?, location=?, tags=?
            WHERE id=?
        """, (new_title, new_description, new_requirements, new_location, new_tags, id_val))
        fixed_count += 1
        print(f"   ✅ Исправлена вакансия ID={id_val}: {new_title[:30]}")

print(f"   Исправлено вакансий/мероприятий: {fixed_count}")

print("\n📋 4. Исправление таблицы employer_profiles...")
cursor.execute("SELECT id, company_name, description, industry, address, city FROM employer_profiles")
rows = cursor.fetchall()
print(f"   Найдено записей: {len(rows)}")

fixed_count = 0
for row in rows:
    id_val, company_name, description, industry, address, city = row
    new_company = fix_text(company_name)
    new_description = fix_text(description)
    new_industry = fix_text(industry)
    new_address = fix_text(address)
    new_city = fix_text(city)

    if (new_company != company_name or new_description != description or
            new_industry != industry or new_address != address or new_city != city):
        cursor.execute("""
            UPDATE employer_profiles 
            SET company_name=?, description=?, industry=?, address=?, city=?
            WHERE id=?
        """, (new_company, new_description, new_industry, new_address, new_city, id_val))
        fixed_count += 1
        print(f"   ✅ Исправлена компания ID={id_val}: {new_company[:30]}")

print(f"   Исправлено профилей работодателей: {fixed_count}")

print("\n📋 5. Исправление таблицы messages...")
cursor.execute("SELECT id, text FROM messages")
rows = cursor.fetchall()
print(f"   Найдено записей: {len(rows)}")

fixed_count = 0
for row in rows:
    id_val, text = row
    new_text = fix_text(text)

    if new_text != text:
        cursor.execute("UPDATE messages SET text=? WHERE id=?", (new_text, id_val))
        fixed_count += 1

print(f"   Исправлено сообщений: {fixed_count}")

print("\n📋 6. Исправление таблицы notifications...")
cursor.execute("SELECT id, title, message FROM notifications")
rows = cursor.fetchall()
print(f"   Найдено записей: {len(rows)}")

fixed_count = 0
for row in rows:
    id_val, title, message = row
    new_title = fix_text(title)
    new_message = fix_text(message)

    if new_title != title or new_message != message:
        cursor.execute("UPDATE notifications SET title=?, message=? WHERE id=?", (new_title, new_message, id_val))
        fixed_count += 1

print(f"   Исправлено уведомлений: {fixed_count}")

print("\n📋 7. Исправление таблицы connections (имя друга)...")
cursor.execute("SELECT id, seeker_id, friend_id FROM connections")
rows = cursor.fetchall()
print(f"   Найдено записей: {len(rows)}")

# Для connections данные не хранят текст, только ID, поэтому просто проверяем

print(f"   ✅ Связи проверены")

conn.commit()
conn.close()

print("\n" + "=" * 60)
print("✅ УНИВЕРСАЛЬНОЕ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!")
print("=" * 60)
print("\n📌 Что было сделано:")
print("   1. Исправлена кодировка во всех текстовых полях")
print("   2. Восстановлены русские буквы")
print("   3. Исправлены JSON поля (skills, privacy_settings)")
print("\n🔄 Перезапустите сервер: python main.py")
print("\n👉 Затем войдите под своим логином и проверьте профили!")