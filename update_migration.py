"""
Add missing columns to existing SQLite tables and populate from DBF files.
Run: python update_migration.py
"""
import os, sys
from datetime import datetime, date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import SQLALCHEMY_DATABASE_URI
from dbfread import DBF
import sqlite3

DBF_PATH = r'D:\sistema de af\dbfs'
DB_PATH = r'D:\sistema de af\sistema_activos\activos.db'

def add_columns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Add columns to grupos_contables
    existing = [c[1] for c in cursor.execute('PRAGMA table_info(grupos_contables)').fetchall()]
    if 'depreciar' not in existing:
        cursor.execute('ALTER TABLE grupos_contables ADD COLUMN depreciar BOOLEAN DEFAULT 1')
        cursor.execute('ALTER TABLE grupos_contables ADD COLUMN actualizar BOOLEAN DEFAULT 1')
        print("+ columns added to grupos_contables")
    else:
        print("= grupos_contables already has columns")

    # Add columns to activos_fijos
    existing = [c[1] for c in cursor.execute('PRAGMA table_info(activos_fijos)').fetchall()]
    new_cols = [
        ('depreciacion_acumulada', 'NUMERIC(15,2) DEFAULT 0'),
        ('vida_util', 'INTEGER DEFAULT 0'),
        ('revaluado', 'BOOLEAN DEFAULT 0'),
        ('band_ufv', 'BOOLEAN DEFAULT 0'),
        ('fecha_ultima_actualizacion', 'DATE'),
        ('usuario', 'VARCHAR(8)'),
        ('codigo_secundario', 'VARCHAR(15)'),
        ('banderas', 'VARCHAR(12)'),
        ('costo_anterior', 'NUMERIC(15,2)'),
        ('vida_util_anterior', 'INTEGER'),
        ('fecha_anterior', 'DATE'),
    ]
    for col_name, col_type in new_cols:
        if col_name not in existing:
            cursor.execute(f'ALTER TABLE activos_fijos ADD COLUMN {col_name} {col_type}')
            print(f'+ added {col_name} to activos_fijos')
        else:
            print(f'= {col_name} already exists')
    conn.commit()
    conn.close()
    print("Columns added successfully.\n")

def populate_from_dbf():
    print("=== Populating missing data from DBF ===")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Update grupos_contables with depreciar/actualizar flags
    print("\n1. Updating grupos_contables...")
    dbf = DBF(os.path.join(DBF_PATH, 'CODCONT.DBF'), load=True, encoding='cp1252')
    updated = 0
    for r in dbf.records:
        codcont = r['CODCONT']
        dep = 1 if r.get('DEPRECIAR') else 0
        act = 1 if r.get('ACTUALIZAR') else 0
        cursor.execute(
            'UPDATE grupos_contables SET depreciar = ?, actualizar = ? WHERE codigo = ?',
            (dep, act, str(codcont))
        )
        if cursor.rowcount > 0:
            updated += 1
    conn.commit()
    print(f"  Updated {updated}/{len(dbf.records)} groups")

    # 2. Update activos_fijos with missing fields from ACTUAL.DBF
    print("\n2. Updating activos_fijos...")
    dbf = DBF(os.path.join(DBF_PATH, 'ACTUAL.DBF'), load=True, encoding='cp1252')
    total = len(dbf.records)
    count = 0
    for r in dbf.records:
        codigo = r.get('CODIGO', '')

        def v(val):
            if val is None: return None
            if isinstance(val, str) and val.strip() == '': return None
            return val

        depacu = float(r['DEPACU']) if r['DEPACU'] else 0
        vida = int(r['VIDAUTIL']) if r['VIDAUTIL'] else None
        brev = 1 if r.get('B_REV') else 0
        bufv = 1 if r.get('BAND_UFV') else 0

        feult = None
        raw = r.get('FEULT')
        if isinstance(raw, date):
            feult = raw.isoformat()

        cost_ant = float(r['COSTO_ANT']) if r.get('COSTO_ANT') else None
        vut_ant = int(r['VUT_ANT']) if r.get('VUT_ANT') else None

        fecha_ant = None
        if r.get('DIA_ANT') and r.get('MES_ANT') and r.get('ANO_ANT'):
            try:
                d, mo, y = int(r['DIA_ANT']), int(r['MES_ANT']), int(r['ANO_ANT'])
                if d > 0 and mo > 0 and y > 0:
                    fecha_ant = date(y, mo, d).isoformat()
            except:
                pass

        cursor.execute('''
            UPDATE activos_fijos SET
                depreciacion_acumulada = ?,
                vida_util = ?,
                revaluado = ?,
                band_ufv = ?,
                fecha_ultima_actualizacion = ?,
                usuario = ?,
                codigo_secundario = ?,
                banderas = ?,
                costo_anterior = ?,
                vida_util_anterior = ?,
                fecha_anterior = ?
            WHERE codigo = ?
        ''', (
            depacu, vida, brev, bufv, feult,
            v(r.get('USUAR')), v(r.get('CODIGOSEC')), v(r.get('BANDERAS')),
            cost_ant, vut_ant, fecha_ant,
            codigo
        ))
        count += 1
        if count % 5000 == 0:
            conn.commit()
            print(f"  {count}/{total}...")
    conn.commit()
    print(f"  Updated {count}/{total} assets")

    conn.close()
    print("\n=== Migration update completed ===")

if __name__ == '__main__':
    add_columns()
    populate_from_dbf()
