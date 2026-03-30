# fix_event_types.py
import sqlite3

conn = sqlite3.connect('tramplin.db')
cursor = conn.cursor()

# Проверяем, какие есть типы
cursor.execute("SELECT DISTINCT type FROM opportunities")
types = cursor.fetchall()
print("Типы в базе данных:", types)

# Исправляем все мероприятия: приводим к единому формату
cursor.execute("""
    UPDATE opportunities 
    SET type = 'EVENT' 
    WHERE type IN ('EVENT', 'Карьерное мероприятие', 'Мероприятие')
""")
updated = cursor.rowcount
print(f"Обновлено записей: {updated}")

# Проверяем результат
cursor.execute("SELECT id, title, type FROM opportunities WHERE type = 'EVENT'")
events = cursor.fetchall()
print(f"\nТеперь мероприятий: {len(events)}")
for event in events[:5]:
    print(f"  ID: {event[0]}, Название: {event[1][:40]}, Type: {event[2]}")

conn.commit()
conn.close()
print("\n✅ Готово!")