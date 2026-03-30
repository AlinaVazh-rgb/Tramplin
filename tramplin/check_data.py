# check_data.py
import sqlite3

conn = sqlite3.connect('tramplin.db')
cursor = conn.cursor()

# Проверяем все записи
cursor.execute("SELECT id, title, type, is_active, is_moderated FROM opportunities")
rows = cursor.fetchall()
print(f"Всего записей: {len(rows)}")
for row in rows:
    print(f"  ID: {row[0]}, Название: {row[1][:30]}, Тип: {row[2]}, Активна: {row[3]}, Одобрена: {row[4]}")

conn.close()