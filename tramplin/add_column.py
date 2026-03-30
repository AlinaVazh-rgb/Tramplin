# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('tramplin.db')
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE events ADD COLUMN company_id INTEGER')
    print("OK: Column company_id added")
except Exception as e:
    print("Error: " + str(e))

conn.commit()
conn.close()
print("Done! You can restart the server now.")