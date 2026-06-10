from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required
from app.models import Oficina, Responsable, UnidadAdministrativa, ActivoFijo
from app.forms import OficinaForm, ResponsableForm
from app import db

oficinas_bp = Blueprint('oficinas', __name__)

@oficinas_bp.route('/')
@login_required
def listar():
    from flask import session
    unidad_id = session.get('unidad_actual_id')
    if not unidad_id:
        return redirect(url_for('main.inicio'))
    oficinas = Oficina.query.filter_by(unidad_id=unidad_id).all()
    return render_template('oficinas/listar.html', oficinas=oficinas)

@oficinas_bp.route('/ver/<int:id>')
@login_required
def ver(id):
    oficina = Oficina.query.get_or_404(id)
    responsables = Responsable.query.filter_by(oficina_id=id).all()
    oform = OficinaForm(obj=oficina)
    rform = ResponsableForm()
    oform.estado.data = oficina.estado
    return render_template('oficinas/ver.html', oficina=oficina, responsables=responsables, oform=oform, rform=rform)

@oficinas_bp.route('/nuevo', methods=['POST'])
@login_required
def nuevo():
    from flask import session
    unidad_id = session.get('unidad_actual_id')
    form = OficinaForm()
    if form.validate_on_submit():
        oficina = Oficina(nombre=form.nombre.data, observacion=form.observacion.data, estado=form.estado.data, unidad_id=unidad_id)
        db.session.add(oficina)
        db.session.commit()
    return redirect(url_for('oficinas.listar'))

@oficinas_bp.route('/modificar/<int:id>', methods=['POST'])
@login_required
def modificar(id):
    oficina = Oficina.query.get_or_404(id)
    form = OficinaForm()
    if form.validate_on_submit():
        oficina.nombre = form.nombre.data
        oficina.observacion = form.observacion.data
        oficina.estado = form.estado.data
        db.session.commit()
    return redirect(url_for('oficinas.ver', id=id))

@oficinas_bp.route('/cambiar_estado/<int:id>')
@login_required
def cambiar_estado(id):
    oficina = Oficina.query.get_or_404(id)
    nuevo_estado = 'INACTIVO' if oficina.estado == 'ACTIVO' else 'ACTIVO'
    if nuevo_estado == 'INACTIVO' and ActivoFijo.query.filter_by(oficina_id=id).first():
        return redirect(url_for('oficinas.ver', id=id))
    oficina.estado = nuevo_estado
    db.session.commit()
    return redirect(url_for('oficinas.ver', id=id))

@oficinas_bp.route('/responsable/nuevo/<int:oficina_id>', methods=['POST'])
@login_required
def responsable_nuevo(oficina_id):
    form = ResponsableForm()
    if form.validate_on_submit():
        resp = Responsable(oficina_id=oficina_id, nombre=form.nombre.data, cargo=form.cargo.data, carnet_identidad=form.carnet_identidad.data, procedencia=form.procedencia.data, estado=form.estado.data)
        db.session.add(resp)
        db.session.commit()
    return redirect(url_for('oficinas.ver', id=oficina_id))

@oficinas_bp.route('/responsable/modificar/<int:id>', methods=['POST'])
@login_required
def responsable_modificar(id):
    resp = Responsable.query.get_or_404(id)
    form = ResponsableForm()
    if form.validate_on_submit():
        resp.nombre = form.nombre.data
        resp.cargo = form.cargo.data
        resp.carnet_identidad = form.carnet_identidad.data
        resp.procedencia = form.procedencia.data
        resp.estado = form.estado.data
        db.session.commit()
        return redirect(url_for('oficinas.ver', id=resp.oficina_id))
    return redirect(url_for('oficinas.ver', id=resp.oficina_id))

@oficinas_bp.route('/responsable/cambiar_estado/<int:id>')
@login_required
def responsable_cambiar_estado(id):
    resp = Responsable.query.get_or_404(id)
    nuevo_estado = 'INACTIVO' if resp.estado == 'ACTIVO' else 'ACTIVO'
    if nuevo_estado == 'INACTIVO' and ActivoFijo.query.filter_by(responsable_id=id).first():
        return redirect(url_for('oficinas.ver', id=resp.oficina_id))
    resp.estado = nuevo_estado
    db.session.commit()
    return redirect(url_for('oficinas.ver', id=resp.oficina_id))
