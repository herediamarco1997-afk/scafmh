"""
Migración de SQLite a PostgreSQL (Neon).
Ejecutar UNA SOLA VEZ desde tu PC local después de crear la BD en Neon.

Uso:
  1. Crea la BD en Neon (ver instrucciones)
  2. Copia la URL de conexión de Neon
  3. Ejecuta: set DATABASE_URL=postgresql://usuario:pass@ep-xxx.neon.tech/scafmh?sslmode=require
  4. Ejecuta: python migrate_to_pg.py
"""
import os
import sys
import sqlite3
from datetime import datetime

def migrate():
    pg_url = os.environ.get('DATABASE_URL', '')
    if not pg_url or not pg_url.startswith('postgres'):
        print("ERROR: Define DATABASE_URL con la URL de Neon primero")
        print("Ejemplo: set DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require")
        sys.exit(1)

    if pg_url.startswith('postgres://'):
        pg_url = pg_url.replace('postgres://', 'postgresql://', 1)

    print(f"Conectando a PostgreSQL...")
    try:
        import psycopg2
        pg_conn = psycopg2.connect(pg_url)
        pg_cur = pg_conn.cursor()
    except Exception as e:
        print(f"Error conectando a PostgreSQL: {e}")
        sys.exit(1)

    print("Creando tablas en PostgreSQL...")
    from app import create_app, db
    app = create_app()
    with app.app_context():
        db.create_all()
    print("Tablas creadas OK")

    # Leer SQLite local
    sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'activos.db')
    if not os.path.exists(sqlite_path):
        print(f"ERROR: No se encuentra {sqlite_path}")
        sys.exit(1)

    print(f"Leyendo SQLite: {sqlite_path}")
    sq_conn = sqlite3.connect(sqlite_path)
    sq_conn.row_factory = sqlite3.Row
    sq = sq_conn.cursor()

    # Migrar tablas en orden (respetando foreign keys)
    tables = [
        ('gestiones', ['id', 'anio', 'cerrada', 'fecha_cierre']),
        ('unidades_administrativas', ['id', 'codigo', 'descripcion', 'ciudad']),
        ('oficinas', ['id', 'unidad_id', 'codofic', 'nombre', 'observacion', 'estado']),
        ('responsables', ['id', 'oficina_id', 'codresp', 'nombre', 'cargo', 'carnet_identidad', 'procedencia', 'estado']),
        ('grupos_contables', ['id', 'codigo', 'nombre', 'vida_util', 'depreciar', 'actualizar']),
        ('auxiliares_contables', ['id', 'grupo_id', 'denominacion']),
        ('organismos_financiadores', ['id', 'codigo', 'descripcion', 'sigla']),
        ('indices_ufv', ['id', 'fecha', 'valor']),
        ('usuarios', ['id', 'username', 'password', 'rol']),
        ('activos_fijos', ['id', 'codigo', 'fecha_incorporacion', 'descripcion', 'grupo_id', 'auxiliar_id',
                           'oficina_id', 'responsable_id', 'estado_bien', 'observaciones', 'codigo_rube',
                           'organismo_financiador', 'numero_convenio', 'costo_inicial', 'depreciacion_acumulada',
                           'vida_util', 'revaluado', 'band_ufv', 'fecha_ultima_actualizacion', 'usuario',
                           'codigo_secundario', 'banderas', 'costo_anterior', 'vida_util_anterior', 'fecha_anterior',
                           'estado', 'gestion_id', 'unidad_id', 'fecha_creacion']),
        ('revaluos_tecnicos', ['id', 'activo_id', 'fecha', 'nuevo_costo', 'nueva_vida_util', 'disposicion_respaldo', 'motivo', 'fecha_creacion']),
        ('bajas_activos', ['id', 'activo_id', 'fecha', 'tipo', 'motivo', 'disposicion_legal', 'fecha_creacion']),
        ('transferencias', ['id', 'activo_id', 'fecha', 'tipo', 'oficina_origen_id', 'responsable_origen_id',
                            'oficina_destino_id', 'responsable_destino_id', 'usuario', 'fecha_creacion']),
        ('inventario_fisico', ['id', 'activo_id', 'codigo', 'resultado', 'observacion', 'foto_url',
                               'ubicacion_reportada', 'responsable_reportado', 'nueva_oficina_id', 'nuevo_responsable_id',
                               'nuevo_estado', 'latitud', 'longitud', 'usuario', 'dispositivo', 'fecha_sincronizacion', 'fecha_toma']),
    ]

    total_migrated = 0
    for table_name, columns in tables:
        try:
            sq.execute(f'SELECT * FROM {table_name}')
            rows = sq.fetchall()
            if not rows:
                print(f"  {table_name}: 0 registros (vacía)")
                continue

            placeholders = ', '.join(['%s'] * len(columns))
            col_names = ', '.join(columns)
            insert_sql = f'INSERT INTO {table_name} ({col_names}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING'

            for row in rows:
                vals = []
                for v in row:
                    vals.append(v)
                pg_cur.execute(insert_sql, vals)

            pg_conn.commit()
            total_migrated += len(rows)
            print(f"  {table_name}: {len(rows)} registros migrados")
        except Exception as e:
            print(f"  {table_name}: ERROR - {e}")
            pg_conn.rollback()

    # Reset sequences
    for table_name, columns in tables:
        if 'id' in columns:
            try:
                pg_cur.execute(f"SELECT setval('{table_name}_id_seq', (SELECT COALESCE(MAX(id), 1) FROM {table_name}))")
                pg_conn.commit()
            except:
                pass

    sq_conn.close()
    pg_cur.close()
    pg_conn.close()

    print(f"\nMigración completa: {total_migrated} registros totales")
    print("Ahora actualiza DATABASE_URL en Render con la URL de Neon")

if __name__ == '__main__':
    migrate()
