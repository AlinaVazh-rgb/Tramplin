import sqlite3

conn = sqlite3.connect('tramplin.db')
cursor = conn.cursor()

# Проверяем структуру таблицы
cursor.execute("PRAGMA table_info(opportunities)")
columns = cursor.fetchall()
print("Структура таблицы opportunities:")
for col in columns:
    print(f"  {col[1]} - {col[2]}")

# Проверяем мероприятия
cursor.execute("SELECT id, title, is_online FROM opportunities WHERE type='EVENT'")
events = cursor.fetchall()
print(f"\nМероприятия ({len(events)} шт.):")
for e in events:
    print(f"  ID={e[0]}, Название={e[1]}, is_online={e[2]}")

conn.close()