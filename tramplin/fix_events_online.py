import sqlite3

conn = sqlite3.connect('tramplin.db')
cursor = conn.cursor()

# Посмотрим текущие значения
cursor.execute("SELECT id, title, is_online FROM opportunities WHERE type='EVENT'")
events = cursor.fetchall()
print("Текущие мероприятия:")
for e in events:
    print(f"  ID={e[0]}, Название={e[1]}, is_online={e[2]}")

# Если нужно изменить (например, сделать мероприятие онлайн)
# cursor.execute("UPDATE opportunities SET is_online = 1 WHERE id = 2")
# cursor.execute("UPDATE opportunities SET is_online = 1 WHERE id = 3")

conn.commit()
conn.close()