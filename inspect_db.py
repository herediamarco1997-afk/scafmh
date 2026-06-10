import sqlite3
conn = sqlite3.connect(r'D:\sistema de af\sistema_activos\activos.db')
cursor = conn.cursor()
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
for t in tables:
    name = t[0]
    print(f'=== {name} ===')
    cols = cursor.execute(f'PRAGMA table_info("{name}")').fetchall()
    for c in cols:
        print(f'  {c[1]} ({c[2]})')
    count = cursor.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
    print(f'  -> {count} rows')
    print()
conn.close()
