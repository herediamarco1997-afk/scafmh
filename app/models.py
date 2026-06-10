from app import db
from flask_login import UserMixin
from datetime import datetime

# Roles del sistema
ROL_ADMIN = 'ADMINISTRADOR'
ROL_OPERADOR = 'OPERADOR'
ROL_INVENTARIADOR = 'INVENTARIADOR'
ROLES_VALIDOS = [ROL_ADMIN, ROL_OPERADOR, ROL_INVENTARIADOR]

class Usuario(UserMixin, db.Model):
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
    oficinas = db.relationship('Oficina', backref='unidad', lazy='dynamic')

class Oficina(db.Model):
    __tablename__ = 'oficinas'
    id = db.Column(db.Integer, primary_key=True)
    unidad_id = db.Column(db.Integer, db.ForeignKey('unidades_administrativas.id'), nullable=False)
    codofic = db.Column(db.Integer)
    nombre = db.Column(db.String(200), nullable=False)
    observacion = db.Column(db.Text)
    estado = db.Column(db.String(10), default='ACTIVO')
    responsables = db.relationship('Responsable', backref='oficina', lazy='dynamic')
    activos = db.relationship('ActivoFijo', backref='oficina_rel', lazy='dynamic',
                            foreign_keys='ActivoFijo.oficina_id')

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
    activos = db.relationship('ActivoFijo', backref='responsable_rel', lazy='dynamic',
                            foreign_keys='ActivoFijo.responsable_id')

class GrupoContable(db.Model):
    __tablename__ = 'grupos_contables'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10))
    nombre = db.Column(db.String(200), nullable=False)
    vida_util = db.Column(db.Integer)
    depreciar = db.Column(db.Boolean, default=True)
    actualizar = db.Column(db.Boolean, default=True)
    auxiliares = db.relationship('AuxiliarContable', backref='grupo', lazy='dynamic', cascade='all, delete-orphan')
    activos = db.relationship('ActivoFijo', backref='grupo', lazy='dynamic',
                            foreign_keys='ActivoFijo.grupo_id')

class AuxiliarContable(db.Model):
    __tablename__ = 'auxiliares_contables'
    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos_contables.id'), nullable=False)
    denominacion = db.Column(db.String(200), nullable=False)
    activos = db.relationship('ActivoFijo', backref='auxiliar', lazy='dynamic',
                            foreign_keys='ActivoFijo.auxiliar_id')

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

class BajaActivo(db.Model):
    __tablename__ = 'bajas_activos'
    id = db.Column(db.Integer, primary_key=True)
    activo_id = db.Column(db.Integer, db.ForeignKey('activos_fijos.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    motivo = db.Column(db.Text, nullable=False)
    disposicion_legal = db.Column(db.String(200), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.now)

class Transferencia(db.Model):
    __tablename__ = 'transferencias'
    id = db.Column(db.Integer, primary_key=True)
    activo_id = db.Column(db.Integer, db.ForeignKey('activos_fijos.id'), nullable=True)
    fecha = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    # Origin (before transfer)
    oficina_origen_id = db.Column(db.Integer, db.ForeignKey('oficinas.id'), nullable=True)
    responsable_origen_id = db.Column(db.Integer, db.ForeignKey('responsables.id'), nullable=True)
    # Destination (after transfer)
    oficina_destino_id = db.Column(db.Integer, db.ForeignKey('oficinas.id'), nullable=True)
    responsable_destino_id = db.Column(db.Integer, db.ForeignKey('responsables.id'), nullable=True)
    # Tracking
    usuario = db.Column(db.String(20))
    fecha_creacion = db.Column(db.DateTime, default=datetime.now)
    # Relationships
    activo = db.relationship('ActivoFijo', backref='transferencias')
    oficina_origen = db.relationship('Oficina', foreign_keys=[oficina_origen_id])
    responsable_origen = db.relationship('Responsable', foreign_keys=[responsable_origen_id])
    oficina_dest = db.relationship('Oficina', foreign_keys=[oficina_destino_id])
    responsable_dest = db.relationship('Responsable', foreign_keys=[responsable_destino_id])

class IndiceUFV(db.Model):
    __tablename__ = 'indices_ufv'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, unique=True, nullable=False)
    valor = db.Column(db.Numeric(10, 6), nullable=False)

class OrganismoFinanciador(db.Model):
    __tablename__ = 'organismos_financiadores'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(3))
    descripcion = db.Column(db.String(200))
    sigla = db.Column(db.String(30))


class InventarioFisico(db.Model):
    __tablename__ = 'inventario_fisico'
    id = db.Column(db.Integer, primary_key=True)
    activo_id = db.Column(db.Integer, db.ForeignKey('activos_fijos.id'), nullable=False)
    codigo = db.Column(db.String(15), nullable=False, index=True)
    resultado = db.Column(db.String(20), nullable=False)  # VERIFICADO, NOVEDAD, NO_ENCONTRADO
    observacion = db.Column(db.Text)
    foto_url = db.Column(db.String(500))
    ubicacion_reportada = db.Column(db.String(200))
    responsable_reportado = db.Column(db.String(200))
    # Nuevos campos: cambio de oficina/responsable desde la app móvil
    nueva_oficina_id = db.Column(db.Integer, db.ForeignKey('oficinas.id'), nullable=True)
    nuevo_responsable_id = db.Column(db.Integer, db.ForeignKey('responsables.id'), nullable=True)
    latitud = db.Column(db.Float)
    longitud = db.Column(db.Float)
    usuario = db.Column(db.String(50))
    dispositivo = db.Column(db.String(100))
    fecha_sincronizacion = db.Column(db.DateTime, default=datetime.now)
    fecha_toma = db.Column(db.DateTime, nullable=False)
    activo = db.relationship('ActivoFijo', backref='inventarios')
    oficina_nueva = db.relationship('Oficina', foreign_keys=[nueva_oficina_id])
    responsable_nuevo = db.relationship('Responsable', foreign_keys=[nuevo_responsable_id])
