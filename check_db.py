import sqlite3

conn = sqlite3.connect('D:/sistema de af - copia/sistema_activos/activos.db')
c = conn.cursor()
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    count = c.execute(f"SELECT COUNT(*) FROM [{t[0]}]").fetchone()[0]
    print(f"{t[0]}: {count}")
conn.close()
