from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, DateField, DecimalField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Optional

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])

class UnidadForm(FlaskForm):
    codigo = StringField('Código', validators=[DataRequired()])
    ciudad = StringField('Ciudad', validators=[DataRequired()])
    descripcion = StringField('Descripción', validators=[DataRequired()])

class OficinaForm(FlaskForm):
    nombre = StringField('Nombre de Oficina', validators=[DataRequired()])
    observacion = TextAreaField('Observación')
    estado = SelectField('Estado', choices=[('ACTIVO', 'ACTIVO'), ('INACTIVO', 'INACTIVO')], default='ACTIVO')

class ResponsableForm(FlaskForm):
    nombre = StringField('Nombre del Responsable', validators=[DataRequired()])
    cargo = StringField('Cargo', validators=[DataRequired()])
    carnet_identidad = StringField('Carnet de Identidad', validators=[DataRequired()])
    procedencia = StringField('Procedencia', validators=[DataRequired()])
    estado = SelectField('Estado', choices=[('ACTIVO', 'ACTIVO'), ('INACTIVO', 'INACTIVO')], default='ACTIVO')

class AuxiliarForm(FlaskForm):
    denominacion = StringField('Denominación', validators=[DataRequired()])

class ActivoFijoForm(FlaskForm):
    codigo = StringField('Código del Activo', validators=[DataRequired()])
    fecha_incorporacion = DateField('Fecha de Incorporación', validators=[DataRequired()])
    descripcion = TextAreaField('Descripción del Bien', validators=[DataRequired()])
    grupo_id = SelectField('Grupo Contable', coerce=int, validators=[DataRequired()])
    auxiliar_id = SelectField('Auxiliar Contable', coerce=int, validators=[DataRequired()])
    oficina_id = SelectField('Oficina', coerce=int, validators=[DataRequired()])
    responsable_id = SelectField('Responsable', coerce=int, validators=[DataRequired()])
    estado_bien = SelectField('Estado del Bien', choices=[('', '---'), ('BUENO', 'BUENO'), ('REGULAR', 'REGULAR'), ('MALO', 'MALO')])
    observaciones = TextAreaField('Observaciones')
    codigo_rube = StringField('Código RUBE')
    organismo_financiador = StringField('Organismo Financiador')
    numero_convenio = StringField('N° de Convenio')
    costo_inicial = DecimalField('Costo Inicial (Bs)', places=2, validators=[DataRequired()])

class RevaluoForm(FlaskForm):
    fecha = DateField('Fecha de Revalúo', validators=[DataRequired()])
    nuevo_costo = DecimalField('Nuevo Costo (Bs)', places=2, validators=[DataRequired()])
    nueva_vida_util = IntegerField('Nueva Vida Útil (años)', validators=[DataRequired()])
    disposicion_respaldo = StringField('Disposición de Respaldo', validators=[DataRequired()])
    motivo = TextAreaField('Motivo del Revalúo', validators=[DataRequired()])

class BajaForm(FlaskForm):
    fecha = DateField('Fecha de Baja', validators=[DataRequired()])
    tipo = SelectField('Tipo de Baja', choices=[('DISPOSICION', 'Disposición de Bienes'), ('ERROR_TRANSCRIPCION', 'Error de Transcripción')], validators=[DataRequired()])
    motivo = TextAreaField('Motivo', validators=[DataRequired()])
    disposicion_legal = StringField('Disposición Legal')

class TransferenciaForm(FlaskForm):
    fecha = DateField('Fecha de Transferencia', validators=[DataRequired()])
    tipo = SelectField('Tipo de Transferencia', choices=[('ENTRE_UNIDADES', 'Entre Unidades Administrativas'), ('MISMA_UNIDAD', 'Misma Unidad (Entre Oficinas/Responsables)')], validators=[DataRequired()])
    unidad_destino_id = SelectField('Unidad Destino', coerce=int)
    oficina_destino_id = SelectField('Oficina Destino', coerce=int)
    responsable_destino_id = SelectField('Responsable Destino', coerce=int)

class CambioPasswordForm(FlaskForm):
    password_actual = PasswordField('Contraseña Actual', validators=[DataRequired()])
    password_nueva = PasswordField('Nueva Contraseña', validators=[DataRequired()])

class NuevoUsuarioForm(FlaskForm):
    username = StringField('Nombre de Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    rol = SelectField('Rol', choices=[('OPERADOR', 'OPERADOR'), ('ADMINISTRADOR', 'ADMINISTRADOR')], default='OPERADOR')

class UFVForm(FlaskForm):
    fecha = DateField('Fecha', validators=[DataRequired()])
    valor = DecimalField('Valor UFV', places=6, validators=[DataRequired()])
