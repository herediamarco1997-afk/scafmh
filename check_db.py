import sqlite3, os
db = os.path.join(os.path.dirname(__file__), 'activos.db')
conn = sqlite3.connect(db)
c = conn.cursor()
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
for t in tables:
    name = t[0]
    count = c.execute('SELECT COUNT(*) FROM "' + name + '"').fetchone()[0]
    cols = [d[1] for d in c.execute('PRAGMA table_info("' + name + '")').fetchall()]
    print(f'{name:30s} {count:>6d} registros  columnas: {", ".join(cols[:5])}...' if len(cols)>5 else f'{name:30s} {count:>6d} registros  columnas: {", ".join(cols)}')
conn.close()
