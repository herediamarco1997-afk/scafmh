"""
Migración剩余: solo activos_fijos que faltan.
"""
import os
import sys
import sqlite3

BOOL_COLS = {'cerrada', 'depreciar', 'actualizar', 'revaluado', 'band_ufv'}
INT_COLS = {'id', 'anio', 'unidad_id', 'codofic', 'oficina_id', 'responsable_id', 'codresp',
            'grupo_id', 'auxiliar_id', 'vida_util', 'gestion_id', 'activo_id',
            'nueva_oficina_id', 'nuevo_responsable_id', 'nueva_vida_util'}
FLOAT_COLS = {'costo_inicial', 'depreciacion_acumulada', 'costo_anterior', 'valor', 'nuevo_costo', 'latitud', 'longitud'}

def convert(val, col_name):
    if val is None:
        return None
    if col_name in BOOL_COLS:
        return bool(val)
    if col_name in INT_COLS:
        try: return int(val)
        except: return None
    if col_name in FLOAT_COLS:
        try: return float(val)
        except: return None
    # Sanitize strings
    if isinstance(val, str):
        return val.encode('utf-8', errors='replace').decode('utf-8')
    return val

def migrate():
    pg_url = os.environ.get('DATABASE_URL', '')
    if pg_url.startswith('postgres://'):
        pg_url = pg_url.replace('postgres://', 'postgresql://', 1)

    import psycopg2

    pg_conn = psycopg2.connect(pg_url)
    pg_cur = pg_conn.cursor()

    pg_cur.execute("SELECT MAX(id) FROM activos_fijos")
    max_id = pg_cur.fetchone()[0] or 0
    print(f"Ultimo ID en PostgreSQL: {max_id}")

    pg_cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'activos_fijos' AND table_schema = 'public' ORDER BY ordinal_position
    """)
    pg_cols = [r[0] for r in pg_cur.fetchall()]

    sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'activos.db')
    sq_conn = sqlite3.connect(sqlite_path)
    sq = sq_conn.cursor()

    sq.execute(f'PRAGMA table_info(activos_fijos)')
    sq_col_names = [c[1] for c in sq.fetchall()]
    common_cols = [c for c in pg_cols if c in sq_col_names]

    col_list = ', '.join(common_cols)
    placeholders = ', '.join(['%s'] * len(common_cols))
    insert_sql = f'INSERT INTO activos_fijos ({col_list}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING'

    select_cols = ', '.join([f'"{c}"' for c in common_cols])
    sq.execute(f'SELECT {select_cols} FROM activos_fijos WHERE id > {max_id} ORDER BY id')
    rows = sq.fetchall()

    print(f"Faltan {len(rows)} activos por insertar...")

    BATCH = 200
    migrated = 0
    errors = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        vals_batch = []
        for row in batch:
            vals = [convert(row[j], common_cols[j]) for j in range(len(common_cols))]
            vals_batch.append(vals)
        try:
            pg_cur.executemany(insert_sql, vals_batch)
            pg_conn.commit()
            migrated += len(batch)
            print(f"  {migrated}/{len(rows)} insertados...")
        except Exception as e:
            pg_conn.rollback()
            errors += 1
            print(f"  Lote {i} error: {e}")
            # Reconnect
            try: pg_conn.close()
            except: pass
            pg_conn = psycopg2.connect(pg_url)
            pg_cur = pg_conn.cursor()
            # Insert one by one
            for v in vals_batch:
                try:
                    pg_cur.execute(insert_sql, v)
                    pg_conn.commit()
                    migrated += 1
                except:
                    pg_conn.rollback()
                    errors += 1

    pg_cur.execute("SELECT COUNT(*) FROM activos_fijos")
    total = pg_cur.fetchone()[0]
    print(f"\nTotal en PostgreSQL: {total} activos_fijos")
    print(f"Migrados: {migrated}, Errores: {errors}")

    sq_conn.close()
    pg_cur.close()
    pg_conn.close()

if __name__ == '__main__':
    migrate()
