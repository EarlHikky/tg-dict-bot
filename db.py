import sqlite3

conn = sqlite3.connect('dictionary.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS dictionary (eng text primary key, ru text,
                            jap text, time text)''')
conn.commit()
