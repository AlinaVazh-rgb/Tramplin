# check_db.py
import sqlite3

conn = sqlite3.connect('tramplin.db')
cursor = conn.cursor()

# Проверяем все вакансии
cursor.execute('SELECT id, title, is_active, is_moderated, type FROM opportunities')
rows = cursor.fetchall()
print(f'Всего записей в opportunities: {len(rows)}')
print('ID | Название | Активна | Одобрена | Тип')
print('-' * 60)
for row in rows:
    print(f"{row[0]} | {row[1][:30]} | {row[2]} | {row[3]} | {row[4]}")

# Проверяем активные и одобренные
cursor.execute('SELECT COUNT(*) FROM opportunities WHERE is_active=1 AND is_moderated=1')
count = cursor.fetchone()[0]
print(f'\nАктивных и одобренных вакансий: {count}')

# Проверяем типы
cursor.execute('SELECT DISTINCT type FROM opportunities')
types = cursor.fetchall()
print(f'Типы записей: {types}')

conn.close()
