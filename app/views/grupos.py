from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required
from app.models import GrupoContable, AuxiliarContable, ActivoFijo
from app.forms import AuxiliarForm
from app import db

grupos_bp = Blueprint('grupos', __name__)

GRUPOS_PREDEFINIDOS = [
    ('1', 'ACTIVOS CIRCULANTES'),
    ('2', 'ACTIVOS A LARGO PLAZO'),
    ('3', 'ACTIVOS FIJOS TANGIBLES'),
    ('4', 'ACTIVOS FIJOS INTANGIBLES'),
    ('5', 'ACTIVOS FIJOS EN PROCESO'),
    ('6', 'OTROS ACTIVOS'),
]

@grupos_bp.route('/')
@login_required
def listar():
    grupos = GrupoContable.query.all()
    if not grupos:
        for cod, nom in GRUPOS_PREDEFINIDOS:
            db.session.add(GrupoContable(codigo=cod, nombre=nom))
        db.session.commit()
        grupos = GrupoContable.query.all()
    return render_template('grupos/listar.html', grupos=grupos)

@grupos_bp.route('/ver/<int:id>')
@login_required
def ver(id):
    grupo = GrupoContable.query.get_or_404(id)
    auxiliares = AuxiliarContable.query.filter_by(grupo_id=id).all()
    form = AuxiliarForm()
    return render_template('grupos/ver.html', grupo=grupo, auxiliares=auxiliares, form=form)

@grupos_bp.route('/auxiliar/nuevo/<int:grupo_id>', methods=['POST'])
@login_required
def auxiliar_nuevo(grupo_id):
    form = AuxiliarForm()
    if form.validate_on_submit():
        aux = AuxiliarContable(grupo_id=grupo_id, denominacion=form.denominacion.data)
        db.session.add(aux)
        db.session.commit()
    return redirect(url_for('grupos.ver', id=grupo_id))

@grupos_bp.route('/auxiliar/modificar/<int:id>', methods=['POST'])
@login_required
def auxiliar_modificar(id):
    aux = AuxiliarContable.query.get_or_404(id)
    form = AuxiliarForm()
    if form.validate_on_submit():
        aux.denominacion = form.denominacion.data
        db.session.commit()
    return redirect(url_for('grupos.ver', id=aux.grupo_id))

@grupos_bp.route('/auxiliar/eliminar/<int:id>')
@login_required
def auxiliar_eliminar(id):
    aux = AuxiliarContable.query.get_or_404(id)
    if ActivoFijo.query.filter_by(auxiliar_id=id).first():

        return redirect(url_for('grupos.ver', id=aux.grupo_id))
    grupo_id = aux.grupo_id
    db.session.delete(aux)
    db.session.commit()
    return redirect(url_for('grupos.ver', id=grupo_id))
