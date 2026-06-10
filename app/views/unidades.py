from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required
from app.models import UnidadAdministrativa
from app.forms import UnidadForm
from app import db

unidades_bp = Blueprint('unidades', __name__)

@unidades_bp.route('/')
@login_required
def listar():
    unidades = UnidadAdministrativa.query.all()
    return render_template('unidades/listar.html', unidades=unidades)

@unidades_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    form = UnidadForm()
    if form.validate_on_submit():
        if UnidadAdministrativa.query.filter_by(codigo=form.codigo.data).first():
            return render_template('unidades/form.html', form=form, error='El código ya existe')
        unidad = UnidadAdministrativa(
            codigo=form.codigo.data,
            ciudad=form.ciudad.data,
            descripcion=form.descripcion.data
        )
        db.session.add(unidad)
        db.session.commit()
        return redirect(url_for('unidades.listar'))
    return render_template('unidades/form.html', form=form)

@unidades_bp.route('/modificar/<int:id>', methods=['GET', 'POST'])
@login_required
def modificar(id):
    unidad = UnidadAdministrativa.query.get_or_404(id)
    form = UnidadForm(obj=unidad)
    if form.validate_on_submit():
        unidad.codigo = form.codigo.data
        unidad.ciudad = form.ciudad.data
        unidad.descripcion = form.descripcion.data
        db.session.commit()
        return redirect(url_for('unidades.listar'))
    return render_template('unidades/form.html', form=form, unidad=unidad)
