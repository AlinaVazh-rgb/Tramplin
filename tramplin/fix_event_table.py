# fix_event_table.py - Обновлённая версия для проверки и исправления таблиц
import sqlite3
import os


def fix_database():
    db_file = 'tramplin.db'

    # Проверяем, существует ли база данных
    if not os.path.exists(db_file):
        print(f"❌ База данных {db_file} не найдена!")
        print("   Сначала запустите сервер: python main.py")
        return False

    print(f"🔧 Подключаюсь к {db_file}...")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # ========== 1. Проверяем таблицу event_registrations ==========
    print("\n📋 Проверка таблицы event_registrations...")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='event_registrations'")
    if cursor.fetchone():
        print("   ✅ Таблица event_registrations существует")

        # Проверяем структуру таблицы
        cursor.execute("PRAGMA table_info(event_registrations)")
        columns = cursor.fetchall()
        existing_columns = [col[1] for col in columns]

        # Проверяем, есть ли нужные колонки
        required_columns = ['id', 'event_id', 'user_id', 'status', 'registered_at']
        missing_columns = [col for col in required_columns if col not in existing_columns]

        if missing_columns:
            print(f"   ⚠️ Отсутствуют колонки: {missing_columns}")
            # Добавляем недостающие колонки
            for col in missing_columns:
                if col == 'status':
                    cursor.execute("ALTER TABLE event_registrations ADD COLUMN status VARCHAR DEFAULT 'registered'")
                    print(f"   ✅ Добавлена колонка {col}")
                elif col == 'registered_at':
                    cursor.execute(
                        "ALTER TABLE event_registrations ADD COLUMN registered_at DATETIME DEFAULT CURRENT_TIMESTAMP")
                    print(f"   ✅ Добавлена колонка {col}")
    else:
        print("   ❌ Таблица event_registrations НЕ существует!")
        print("   🔨 Создаю таблицу...")
        cursor.execute('''
        CREATE TABLE event_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status VARCHAR DEFAULT 'registered',
            registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        print("   ✅ Таблица event_registrations создана!")

    # ========== 2. Создаём индексы ==========
    print("\n📋 Создание индексов...")
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_registrations_event_id ON event_registrations(event_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_registrations_user_id ON event_registrations(user_id)")
        print("   ✅ Индексы созданы")
    except Exception as e:
        print(f"   ⚠️ Ошибка создания индексов: {e}")

    # ========== 3. Проверяем мероприятия ==========
    print("\n📋 Проверка мероприятий...")
    cursor.execute("SELECT id, title, type, is_moderated, is_active, event_date FROM opportunities WHERE type='EVENT'")
    events = cursor.fetchall()

    if not events:
        print("   ⚠️ Нет ни одного мероприятия!")
        print("   Создайте мероприятие через личный кабинет работодателя")
    else:
        print(f"   ✅ Найдено мероприятий: {len(events)}")
        for e in events:
            print(f"      ID: {e[0]}, Название: {e[1][:30]}, Модерировано: {e[3]}, Дата: {e[5]}")
            if e[3] == 0:
                print(f"         ⚠️ Мероприятие {e[0]} НЕ ОДОБРЕНО! Войдите как admin и одобрите")
            if e[5] is None:
                print(f"         ⚠️ У мероприятия {e[0]} НЕ УКАЗАНА ДАТА!")

    # ========== 4. Проверяем регистрации ==========
    print("\n📋 Проверка регистраций...")
    cursor.execute("SELECT COUNT(*) FROM event_registrations")
    reg_count = cursor.fetchone()[0]
    print(f"   ✅ Всего регистраций: {reg_count}")

    if reg_count > 0:
        cursor.execute("""
            SELECT er.id, er.event_id, o.title, er.user_id, u.username, er.status 
            FROM event_registrations er
            LEFT JOIN opportunities o ON er.event_id = o.id
            LEFT JOIN users u ON er.user_id = u.id
            LIMIT 10
        """)
        registrations = cursor.fetchall()
        print("   📋 Последние регистрации:")
        for reg in registrations:
            print(
                f"      ID: {reg[0]}, Мероприятие: {reg[2][:20] if reg[2] else '?'}, Пользователь: {reg[4]}, Статус: {reg[5]}")

    # ========== 5. Проверяем внешние ключи ==========
    print("\n📋 Проверка внешних ключей...")
    cursor.execute("PRAGMA foreign_keys")
    fk_status = cursor.fetchone()[0]
    print(f"   Внешние ключи: {'ВКЛЮЧЕНЫ' if fk_status else 'ВЫКЛЮЧЕНЫ'}")

    conn.commit()
    conn.close()

    print("\n" + "=" * 50)
    print("✅ Проверка завершена!")
    print("=" * 50)
    print("\n📌 Что делать, если есть проблемы:")
    print("   1. Если мероприятия не одобрены → войдите как admin/admin123 и одобрите")
    print("   2. Если у мероприятия нет даты → отредактируйте и укажите дату")
    print("   3. Перезапустите сервер: python main.py")

    return True


if __name__ == "__main__":
    fix_database()