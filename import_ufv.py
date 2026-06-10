"""
Import UFV historical data from BCB (Banco Central de Bolivia).
Downloads annual XLS files (old format) and loads into the database.
"""
import os, sys, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import SQLALCHEMY_DATABASE_URI
from datetime import date, datetime
import requests
import xlrd
import warnings
warnings.filterwarnings('ignore', category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class IndiceUFV(db.Model):
    __tablename__ = 'indices_ufv'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, unique=True, nullable=False)
    valor = db.Column(db.Numeric(10, 6), nullable=False)

BASE_URL = 'https://www.bcb.gob.bo/librerias/indicadores/ufv/anualxls.php?gestion='

MONTHS = ['', 'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
          'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']

def import_year(year):
    print(f"  Downloading {year}...")
    url = BASE_URL + str(year)
    try:
        resp = requests.get(url, verify=False, timeout=30)
        if resp.status_code != 200:
            print(f"    HTTP {resp.status_code}")
            return 0

        wb = xlrd.open_workbook(file_contents=resp.content)
        ws = wb.sheet_by_index(0)
        print(f"    Sheet: {ws.name}, rows={ws.nrows}, cols={ws.ncols}")

        # Find header row with month names
        header_row = None
        month_cols = {}  # col_idx -> month_num
        for r in range(ws.nrows):
            for c in range(ws.ncols):
                cell_val = str(ws.cell_value(r, c)).strip().upper()
                for m in range(1, 13):
                    if cell_val == MONTHS[m]:
                        if header_row is None:
                            header_row = r
                        month_cols[c] = m
            if header_row is not None:
                break

        if not month_cols:
            print(f"    Could not find month headers")
            return 0

        print(f"    Header at row {header_row}, months in cols: {month_cols}")

        # Data rows start after header row + possible blank row
        data_start = header_row + 1
        import re

        def parse_ufv_value(raw):
            """Parse UFV value from BCB format. Values look like '↑ 3,04717' or 3.04717"""
            if raw == '' or raw is None:
                return None
            if isinstance(raw, (int, float)):
                return float(raw) if float(raw) > 0 else None
            s = str(raw).strip()
            # Remove arrow and other non-numeric chars except comma/dot/minus
            s = re.sub(r'[^\d,\-\.]', '', s)
            s = s.strip()
            if not s:
                return None
            # Handle European format: comma is decimal separator
            if ',' in s and '.' in s:
                # Mixed format - use last dot/comma as decimal
                if s.rfind(',') > s.rfind('.'):
                    s = s.replace('.', '').replace(',', '.')
                else:
                    s = s.replace(',', '')
            elif ',' in s:
                s = s.replace(',', '.')
            try:
                v = float(s)
                return v if v > 0 else None
            except ValueError:
                return None

        count = 0
        for r in range(data_start, ws.nrows):
            day_val = ws.cell_value(r, 0)
            try:
                day = int(float(day_val))
            except (ValueError, TypeError):
                continue
            if day < 1 or day > 31:
                continue

            for col_idx, month_num in month_cols.items():
                raw = ws.cell_value(r, col_idx)
                val = parse_ufv_value(raw)
                if val is not None:
                    try:
                        d = date(year, month_num, day)
                        existing = db.session.query(IndiceUFV).filter_by(fecha=d).first()
                        if not existing:
                            db.session.add(IndiceUFV(fecha=d, valor=round(val, 6)))
                            count += 1
                    except ValueError:
                        pass

        wb.release_resources()
        if count > 0:
            db.session.commit()
        print(f"    {count} records imported")
        return count
    except Exception as e:
        print(f"    ERROR: {e}")
        return 0

def import_all():
    print("=== Importing UFV historical data from BCB ===")
    total = 0
    for year in range(2001, 2027):
        c = import_year(year)
        total += c
    print(f"\nTotal: {total} records imported")

if __name__ == '__main__':
    with app.app_context():
        import_all()
