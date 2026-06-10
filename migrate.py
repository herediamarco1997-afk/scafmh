"""
Migration script: Import all data from FoxPro DBF files into the web app SQLite database.
Run this once: python -X utf8 migrate.py
"""
import os, sys
from datetime import datetime, date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import SQLALCHEMY_DATABASE_URI
from dbfread import DBF
from werkzeug.security import generate_password_hash

DBF_PATH = r'D:\sistema de af\dbfs'
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# === Models (EXACT match with app/models.py) ===
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='OPERADOR')

class Gestion(db.Model):
    __tablename__ = 'gestiones'
    id = db.Column(db.Integer, primary_key=True)
    anio = db.Column(db.Integer, unique=True, nullable=False)
    cerrada = db.Column(db.Boolean, default=False)
    fecha_cierre = db.Column(db.DateTime, nullable=True)

class UnidadAdministrativa(db.Model):
    __tablename__ = 'unidades_administrativas'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(5), unique=True, nullable=False)
    descripcion = db.Column(db.String(200), nullable=False)
    ciudad = db.Column(db.String(50))

class Oficina(db.Model):
    __tablename__ = 'oficinas'
    id = db.Column(db.Integer, primary_key=True)
    unidad_id = db.Column(db.Integer, db.ForeignKey('unidades_administrativas.id'), nullable=False)
    codofic = db.Column(db.Integer)
    nombre = db.Column(db.String(200), nullable=False)
    observacion = db.Column(db.Text)
    estado = db.Column(db.String(10), default='ACTIVO')

class Responsable(db.Model):
    __tablename__ = 'responsables'
    id = db.Column(db.Integer, primary_key=True)
    oficina_id = db.Column(db.Integer, db.ForeignKey('oficinas.id'), nullable=False)
    codresp = db.Column(db.Integer)
    nombre = db.Column(db.String(200), nullable=False)
    cargo = db.Column(db.String(100))
    carnet_identidad = db.Column(db.String(30))
    procedencia = db.Column(db.String(100))
    estado = db.Column(db.String(10), default='ACTIVO')

class GrupoContable(db.Model):
    __tablename__ = 'grupos_contables'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10))
    nombre = db.Column(db.String(200), nullable=False)
    vida_util = db.Column(db.Integer)
    depreciar = db.Column(db.Boolean, default=True)
    actualizar = db.Column(db.Boolean, default=True)

class AuxiliarContable(db.Model):
    __tablename__ = 'auxiliares_contables'
    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos_contables.id'), nullable=False)
    denominacion = db.Column(db.String(200), nullable=False)

class ActivoFijo(db.Model):
    __tablename__ = 'activos_fijos'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(15), index=True)
    fecha_incorporacion = db.Column(db.Date)
    descripcion = db.Column(db.Text, nullable=False)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos_contables.id'), nullable=False)
    auxiliar_id = db.Column(db.Integer, db.ForeignKey('auxiliares_contables.id'), nullable=False)
    oficina_id = db.Column(db.Integer, db.ForeignKey('oficinas.id'), nullable=False)
    responsable_id = db.Column(db.Integer, db.ForeignKey('responsables.id'), nullable=False)
    estado_bien = db.Column(db.String(10))
    observaciones = db.Column(db.Text)
    codigo_rube = db.Column(db.String(15))
    organismo_financiador = db.Column(db.String(100))
    numero_convenio = db.Column(db.String(10))
    costo_inicial = db.Column(db.Numeric(15, 2), nullable=False)
    depreciacion_acumulada = db.Column(db.Numeric(15, 2), default=0)
    vida_util = db.Column(db.Integer, default=0)
    revaluado = db.Column(db.Boolean, default=False)
    band_ufv = db.Column(db.Boolean, default=False)
    fecha_ultima_actualizacion = db.Column(db.Date)
    usuario = db.Column(db.String(8))
    codigo_secundario = db.Column(db.String(15))
    banderas = db.Column(db.String(12))
    costo_anterior = db.Column(db.Numeric(15, 2))
    vida_util_anterior = db.Column(db.Integer)
    fecha_anterior = db.Column(db.Date)
    estado = db.Column(db.String(20), nullable=False, default='APROBADO')
    gestion_id = db.Column(db.Integer, db.ForeignKey('gestiones.id'), nullable=True)
    unidad_id = db.Column(db.Integer, db.ForeignKey('unidades_administrativas.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.now)

class Transferencia(db.Model):
    __tablename__ = 'transferencias'
    id = db.Column(db.Integer, primary_key=True)
    activo_id = db.Column(db.Integer, db.ForeignKey('activos_fijos.id'), nullable=True)
    fecha = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    oficina_destino_id = db.Column(db.Integer, db.ForeignKey('oficinas.id'), nullable=True)
    responsable_destino_id = db.Column(db.Integer, db.ForeignKey('responsables.id'), nullable=True)

class OrganismoFinanciador(db.Model):
    __tablename__ = 'organismos_financiadores'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(3))
    descripcion = db.Column(db.String(200))
    sigla = db.Column(db.String(30))

class IndiceUFV(db.Model):
    __tablename__ = 'indices_ufv'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, unique=True, nullable=False)
    valor = db.Column(db.Numeric(10, 6), nullable=False)

class BajaActivo(db.Model):
    __tablename__ = 'bajas_activos'
    id = db.Column(db.Integer, primary_key=True)
    activo_id = db.Column(db.Integer, db.ForeignKey('activos_fijos.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    motivo = db.Column(db.Text, nullable=False)
    disposicion_legal = db.Column(db.String(200), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.now)

class RevaluoTecnico(db.Model):
    __tablename__ = 'revaluos_tecnicos'
    id = db.Column(db.Integer, primary_key=True)
    activo_id = db.Column(db.Integer, db.ForeignKey('activos_fijos.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    nuevo_costo = db.Column(db.Numeric(15, 2), nullable=False)
    nueva_vida_util = db.Column(db.Integer, nullable=False)
    disposicion_respaldo = db.Column(db.String(200), nullable=False)
    motivo = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.now)

def safe(val, default=None):
    if val is None: return default
    if isinstance(val, str) and val.strip() == '': return default
    return val

def api_estado_to_estado(val):
    return {0: 'INACTIVO', 1: 'ACTIVO', 3: 'INACTIVO'}.get(val, 'ACTIVO')

def codestado_to_estado_bien(val):
    return {1: 'BUENO', 2: 'REGULAR', 3: 'MALO'}.get(val)

def make_date(d, m, y):
    try:
        if d and m and y and int(d) > 0 and int(m) > 0 and int(y) > 0:
            return date(int(y), int(m), int(d))
    except: pass
    return None

def migrate():
    print("=== MIGRACION DBF -> SQLite ===")
    db.drop_all()
    db.create_all()

    # 1. Gestion
    print("1. Gestiones...")
    db.session.add(Gestion(anio=2025, cerrada=False))
    db.session.commit()
    gestion_id = 1

    # 2. Unidades Administrativas
    print("2. Unidades Administrativas...")
    dbf = DBF(os.path.join(DBF_PATH, 'unidadadmin.DBF'), load=True, encoding='cp1252')
    unidad_map = {}
    for r in dbf.records:
        u = UnidadAdministrativa(codigo=r['UNIDAD'], descripcion=safe(r['DESCRIP'], ''), ciudad=safe(r['CIUDAD'], ''))
        db.session.add(u); db.session.flush(); unidad_map[r['UNIDAD']] = u.id
    db.session.commit()
    print("   -> " + str(len(dbf.records)) + " unidades")

    # 3. Grupos Contables
    print("3. Grupos Contables...")
    dbf = DBF(os.path.join(DBF_PATH, 'CODCONT.DBF'), load=True, encoding='cp1252')
    grupo_map = {}
    for r in dbf.records:
        g = GrupoContable(codigo=str(r['CODCONT']), nombre=safe(r['NOMBRE'], ''),
                          vida_util=safe(r['VIDAUTIL'], 0),
                          depreciar=bool(r['DEPRECIAR']) if r.get('DEPRECIAR') is not None else True,
                          actualizar=bool(r['ACTUALIZAR']) if r.get('ACTUALIZAR') is not None else True)
        db.session.add(g); db.session.flush(); grupo_map[r['CODCONT']] = g.id
    db.session.commit()
    print("   -> " + str(len(dbf.records)) + " grupos")

    # 4. Auxiliares Contables
    print("4. Auxiliares Contables...")
    dbf = DBF(os.path.join(DBF_PATH, 'auxiliar.DBF'), load=True, encoding='cp1252')
    aux_map = {}
    for r in dbf.records:
        gid = grupo_map.get(r['CODCONT'])
        if gid:
            a = AuxiliarContable(grupo_id=gid, denominacion=safe(r['NOMAUX'], ''))
            db.session.add(a); db.session.flush(); aux_map[(r['CODCONT'], r['CODAUX'])] = a.id
    db.session.commit()
    print("   -> " + str(len(dbf.records)) + " auxiliares")

    # 5. Oficinas
    print("5. Oficinas...")
    dbf = DBF(os.path.join(DBF_PATH, 'OFICINA.DBF'), load=True, encoding='cp1252')
    oficina_map = {}; ocount = 0
    for r in dbf.records:
        uid = unidad_map.get(r['UNIDAD'])
        if not uid: continue
        ocount += 1
        o = Oficina(id=ocount, unidad_id=uid, codofic=r['CODOFIC'], nombre=safe(r['NOMOFIC'], ''),
                    observacion=safe(r['OBSERV']), estado=api_estado_to_estado(r.get('API_ESTADO', 1)))
        db.session.add(o); oficina_map[(r['UNIDAD'], r['CODOFIC'])] = ocount
    db.session.commit()
    print("   -> " + str(ocount) + " oficinas")

    # 6. Responsables
    print("6. Responsables...")
    dbf = DBF(os.path.join(DBF_PATH, 'RESP.DBF'), load=True, encoding='cp1252')
    resp_map = {}; rcount = 0
    for r in dbf.records:
        oid = oficina_map.get((r['UNIDAD'], r['CODOFIC']))
        if not oid: continue
        rcount += 1
        resp = Responsable(id=rcount, oficina_id=oid, codresp=r['CODRESP'], nombre=safe(r['NOMRESP'], ''),
                          cargo=safe(r['CARGO'], ''), carnet_identidad=safe(r['CI'], ''),
                          estado=api_estado_to_estado(r.get('API_ESTADO', 1)))
        db.session.add(resp); resp_map[(r['UNIDAD'], r['CODRESP'])] = rcount
    db.session.commit()
    print("   -> " + str(rcount) + " responsables")

    # 7. Activos Fijos
    print("7. Activos Fijos...")
    dbf = DBF(os.path.join(DBF_PATH, 'ACTUAL.DBF'), load=True, encoding='cp1252')
    batch = []; count = 0; total = len(dbf.records)
    for r in dbf.records:
        uid = unidad_map.get(r['UNIDAD']); gid = grupo_map.get(r['CODCONT'])
        aid = aux_map.get((r['CODCONT'], r['CODAUX']))
        oid = oficina_map.get((r['UNIDAD'], r['CODOFIC']))
        rid = resp_map.get((r['UNIDAD'], r['CODRESP']))
        if not all([uid, gid, aid, oid, rid]): continue

        f_inc = make_date(r['DIA'], r['MES'], r['ANO'])
        costo_val = float(r['COSTO']) if r['COSTO'] else 0

        depacu = float(r['DEPACU']) if r['DEPACU'] else 0
        vida = int(r['VIDAUTIL']) if r['VIDAUTIL'] else 0
        brev = bool(r['B_REV']) if r.get('B_REV') is not None else False
        bufv = bool(r['BAND_UFV']) if r.get('BAND_UFV') is not None else False

        feult = r.get('FEULT')
        if isinstance(feult, datetime): feult = feult.date()

        cost_ant = float(r['COSTO_ANT']) if r.get('COSTO_ANT') else None
        vut_ant = int(r['VUT_ANT']) if r.get('VUT_ANT') else None

        fecha_ant = make_date(r['DIA_ANT'], r['MES_ANT'], r['ANO_ANT'])

        a = ActivoFijo(codigo=safe(r['CODIGO'], ''), fecha_incorporacion=f_inc,
                      descripcion=safe(r['DESCRIP'], ''), grupo_id=gid, auxiliar_id=aid,
                      oficina_id=oid, responsable_id=rid, costo_inicial=costo_val,
                      depreciacion_acumulada=depacu, vida_util=vida,
                      revaluado=brev, band_ufv=bufv, fecha_ultima_actualizacion=feult,
                      usuario=safe(r['USUAR']), codigo_secundario=safe(r['CODIGOSEC']),
                      banderas=safe(r['BANDERAS']), costo_anterior=cost_ant,
                      vida_util_anterior=vut_ant, fecha_anterior=fecha_ant,
                      estado_bien=codestado_to_estado_bien(r.get('CODESTADO')),
                      observaciones=safe(r['OBSERV']), codigo_rube=safe(r['COD_RUBE']),
                      organismo_financiador=safe(r['ORG_FIN']), numero_convenio=safe(r['NRO_CONV']),
                      estado='APROBADO', unidad_id=uid, gestion_id=gestion_id)
        batch.append(a); count += 1
        if len(batch) >= 500:
            db.session.add_all(batch); db.session.commit(); batch = []
            print("      " + str(count) + "/" + str(total))
    if batch:
        db.session.add_all(batch); db.session.commit()
    print("   -> " + str(count) + " activos fijos")

    # 8. Transferencias
    print("8. Transferencias...")
    dbf = DBF(os.path.join(DBF_PATH, 'trasfe.DBF'), load=True, encoding='cp1252')
    tcount = 0
    for r in dbf.records:
        oid = oficina_map.get((r['UNIDAD'], r['CODOFIC']))
        if not oid: continue
        fecha = r.get('FEULT')
        if isinstance(fecha, datetime): fecha = fecha.date()
        t = Transferencia(fecha=fecha or date.today(), tipo='MISMA_UNIDAD',
                         oficina_destino_id=oid, responsable_destino_id=resp_map.get((r['UNIDAD'], r['CODRESP'])))
        db.session.add(t); tcount += 1
    db.session.commit()
    print("   -> " + str(tcount) + " transferencias")

    # 9. Organismos Financiadores
    print("9. Organismos Financiadores...")
    dbf = DBF(os.path.join(DBF_PATH, 'organismo_fin.DBF'), load=True, encoding='cp1252')
    for r in dbf.records:
        db.session.add(OrganismoFinanciador(codigo=safe(r['OF'], ''), descripcion=safe(r['DES'], ''), sigla=safe(r['SIGLA'], '')))
    db.session.commit()
    print("   -> " + str(len(dbf.records)) + " organismos")

    # 10. Admin
    print("10. Usuario admin...")
    if not Usuario.query.filter_by(username='admin').first():
        db.session.add(Usuario(username='admin', password=generate_password_hash('admin'), rol='ADMINISTRADOR'))
        db.session.commit()

    print("\n=== MIGRACION COMPLETADA ===")
    for tabla in ['usuarios', 'gestiones', 'unidades_administrativas', 'grupos_contables',
                  'auxiliares_contables', 'oficinas', 'responsables', 'activos_fijos',
                  'transferencias', 'organismos_financiadores']:
        cnt = db.session.execute(f'SELECT COUNT(*) FROM {tabla}').scalar()
        print(f"  {tabla}: {cnt}")

if __name__ == '__main__':
    with app.app_context():
        migrate()
