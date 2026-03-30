# update_db_event_format.py
import sqlite3

conn = sqlite3.connect('tramplin.db')
cursor = conn.cursor()

try:
    # Добавляем колонку is_online
    cursor.execute("ALTER TABLE opportunities ADD COLUMN is_online BOOLEAN DEFAULT 0")
    print("✅ Колонка is_online добавлена в таблицу opportunities")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("⚠️ Колонка is_online уже существует")
    else:
        print(f"❌ Ошибка: {e}")

conn.commit()
conn.close()
print("Готово!")