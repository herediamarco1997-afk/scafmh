from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Usuario, Gestion, UnidadAdministrativa
from app.forms import LoginForm, CambioPasswordForm
from werkzeug.security import check_password_hash, generate_password_hash
from app import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.inicio'))
    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('main.inicio'))
    return render_template('login.html', form=form)

@main_bp.route('/inicio')
@login_required
def inicio():
    gestion_activa = Gestion.query.filter_by(cerrada=False).first()
    unidades = UnidadAdministrativa.query.all()
    return render_template('inicio.html', gestion=gestion_activa, unidades=unidades)

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main_bp.route('/seguridad', methods=['GET', 'POST'])
@login_required
def seguridad():
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('main.inicio'))
    from app.forms import NuevoUsuarioForm
    form = NuevoUsuarioForm()
    usuarios = Usuario.query.all()
    if form.validate_on_submit():
        if Usuario.query.filter_by(username=form.username.data).first():
            return render_template('seguridad/usuarios.html', form=form, usuarios=usuarios, error='El usuario ya existe')
        user = Usuario(
            username=form.username.data,
            password=generate_password_hash(form.password.data),
            rol=form.rol.data
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('main.seguridad'))
    return render_template('seguridad/usuarios.html', form=form, usuarios=usuarios)

@main_bp.route('/cambiar_password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    form = CambioPasswordForm()
    if form.validate_on_submit():
        if check_password_hash(current_user.password, form.password_actual.data):
            current_user.password = generate_password_hash(form.password_nueva.data)
            db.session.commit()
            return redirect(url_for('main.inicio'))
    return render_template('seguridad/cambiar_password.html', form=form)

@main_bp.route('/seleccionar_unidad', methods=['POST'])
@login_required
def seleccionar_unidad():
    unidad_id = request.form.get('unidad_id')
    if unidad_id:
        from flask import session
        session['unidad_actual_id'] = int(unidad_id)
    return redirect(url_for('main.inicio'))
