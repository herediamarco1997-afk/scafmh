from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from flask_login import login_required, current_user
from app.models import Gestion, ActivoFijo, IndiceUFV
from app.forms import UFVForm
from app.depreciacion import procesar_actualizacion_ufv, procesar_depreciacion, revertir_procesamiento
from app import db
from datetime import datetime
import json

administracion_bp = Blueprint('administracion', __name__)

@administracion_bp.route('/')
@login_required
def panel():
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('main.inicio'))
    gestion_actual = Gestion.query.filter_by(cerrada=False).first()
    gestiones_cerradas = Gestion.query.filter_by(cerrada=True).all()
    return render_template('administracion/panel.html', gestion_actual=gestion_actual, gestiones_cerradas=gestiones_cerradas)

@administracion_bp.route('/iniciar_gestion', methods=['POST'])
@login_required
def iniciar_gestion():
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('main.inicio'))
    anio = int(request.form.get('anio', datetime.now().year))
    if Gestion.query.filter_by(anio=anio).first():
        return redirect(url_for('administracion.panel'))
    gestion = Gestion(anio=anio, cerrada=False)
    db.session.add(gestion)
    db.session.commit()
    return redirect(url_for('administracion.panel'))

@administracion_bp.route('/cerrar_gestion')
@login_required
def cerrar_gestion():
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('main.inicio'))
    if ActivoFijo.query.filter_by(estado='ELABORADO').first():
        return redirect(url_for('administracion.panel'))
    gestion = Gestion.query.filter_by(cerrada=False).first()
    if gestion:
        gestion.cerrada = True
        gestion.fecha_cierre = datetime.now()
        db.session.commit()
    return redirect(url_for('administracion.panel'))

@administracion_bp.route('/cambiar_gestion/<int:gestion_id>')
@login_required
def cambiar_gestion(gestion_id):
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('main.inicio'))
    gestion = Gestion.query.get_or_404(gestion_id)
    gestion_actual = Gestion.query.filter_by(cerrada=False).first()
    if gestion_actual:
        gestion_actual.cerrada = True
        gestion_actual.fecha_cierre = datetime.now()
    gestion.cerrada = False
    gestion.fecha_cierre = None
    db.session.commit()
    return redirect(url_for('administracion.panel'))

@administracion_bp.route('/ufv', methods=['GET', 'POST'])
@login_required
def ufv():
    form = UFVForm()
    if form.validate_on_submit():
        if IndiceUFV.query.filter_by(fecha=form.fecha.data).first():
            return render_template('administracion/ufv.html', form=form, indices=IndiceUFV.query.order_by(IndiceUFV.fecha.desc()).all(), error='Ya existe un índice para esa fecha')
        indice = IndiceUFV(fecha=form.fecha.data, valor=form.valor.data)
        db.session.add(indice)
        db.session.commit()
        return redirect(url_for('administracion.ufv'))
    indices = IndiceUFV.query.order_by(IndiceUFV.fecha.desc()).all()
    return render_template('administracion/ufv.html', form=form, indices=indices)

@administracion_bp.route('/ufv/eliminar/<int:id>')
@login_required
def ufv_eliminar(id):
    indice = IndiceUFV.query.get_or_404(id)
    db.session.delete(indice)
    db.session.commit()
    return redirect(url_for('administracion.ufv'))

@administracion_bp.route('/procesar_actualizacion')
@login_required
def procesar_actualizacion():
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('main.inicio'))
    gestion = Gestion.query.filter_by(cerrada=False).first()
    if not gestion:
        flash('No hay una gestión vigente', 'danger')
        return redirect(url_for('administracion.panel'))
    try:
        result = procesar_actualizacion_ufv(gestion.anio)
        msg = f'Actualización UFV completada: {result["actualizados"]} activos actualizados'
        if result['errors']:
            msg += f' | {len(result["errors"])} errores'
        flash(msg, 'success')
    except Exception as e:
        flash(f'Error en actualización UFV: {e}', 'danger')
    return redirect(url_for('administracion.panel'))


@administracion_bp.route('/procesar_depreciacion')
@login_required
def procesar_depreciacion_route():
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('main.inicio'))
    gestion = Gestion.query.filter_by(cerrada=False).first()
    if not gestion:
        flash('No hay una gestión vigente', 'danger')
        return redirect(url_for('administracion.panel'))
    try:
        result = procesar_depreciacion(gestion.anio)
        msg = f'Depreciación procesada: {result["procesados"]} activos, Bs. {result["total_depreciacion"]:,.2f}'
        if result['errors']:
            msg += f' | {len(result["errors"])} errores'
        flash(msg, 'success')
    except Exception as e:
        flash(f'Error en depreciación: {e}', 'danger')
    return redirect(url_for('administracion.panel'))


@administracion_bp.route('/revertir_procesamiento')
@login_required
def revertir_procesamiento_route():
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('main.inicio'))
    gestion = Gestion.query.filter_by(cerrada=False).first()
    if not gestion:
        flash('No hay una gestión vigente', 'danger')
        return redirect(url_for('administracion.panel'))
    try:
        result = revertir_procesamiento(gestion.anio)
        if result['revertidos'] == 0:
            flash(result['errors'][0] if result['errors'] else 'No hay procesamiento que revertir', 'warning')
        else:
            msg = f'Reversión de {result.get("tipo_revertido","?")} completada: {result["revertidos"]} activos restaurados'
            if result['errors']:
                msg += f' | {len(result["errors"])} errores'
            flash(msg, 'success')
    except Exception as e:
        flash(f'Error en reversión: {e}', 'danger')
    return redirect(url_for('administracion.panel'))


@administracion_bp.route('/reindexar')
@login_required
def reindexar():
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('main.inicio'))
    activos = ActivoFijo.query.all()
    for i, activo in enumerate(activos):
        pass
    return redirect(url_for('administracion.panel'))

@administracion_bp.route('/exportar/<int:unidad_id>')
@login_required
def exportar(unidad_id):
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('main.inicio'))
    from app.models import UnidadAdministrativa
    unidad = UnidadAdministrativa.query.get_or_404(unidad_id)
    data = {'unidad': {'codigo': unidad.codigo, 'ciudad': unidad.ciudad, 'descripcion': unidad.descripcion}}
    filename = f'export_{unidad.codigo}_{datetime.now().strftime("%Y%m%d")}.json'
    filepath = f'backups/{filename}'
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return redirect(url_for('administracion.panel'))

@administracion_bp.route('/importar', methods=['POST'])
@login_required
def importar():
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('main.inicio'))
    from app.models import UnidadAdministrativa
    file = request.files.get('archivo')
    if file and file.filename.endswith('.json'):
        data = json.load(file)
        u = data.get('unidad', {})
        if not UnidadAdministrativa.query.filter_by(codigo=u.get('codigo')).first():
            unidad = UnidadAdministrativa(codigo=u['codigo'], ciudad=u['ciudad'], descripcion=u['descripcion'])
            db.session.add(unidad)
            db.session.commit()
    return redirect(url_for('administracion.panel'))
