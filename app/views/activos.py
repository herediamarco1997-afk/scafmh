from flask import Blueprint, render_template, redirect, url_for, request, session
from flask_login import login_required
from app.models import (ActivoFijo, GrupoContable, AuxiliarContable, Oficina, Responsable,
                        UnidadAdministrativa, Gestion, RevaluoTecnico, BajaActivo, Transferencia)
from app.forms import ActivoFijoForm, RevaluoForm, BajaForm, TransferenciaForm
from app import db
from datetime import datetime

activos_bp = Blueprint('activos', __name__)

@activos_bp.route('/')
@login_required
def listar():
    unidad_id = session.get('unidad_actual_id')
    query = ActivoFijo.query
    if unidad_id:
        query = query.filter_by(unidad_id=unidad_id)
    estado = request.args.get('estado', '')
    if estado:
        query = query.filter_by(estado=estado)
    activos = query.order_by(ActivoFijo.codigo).all()
    return render_template('activos/listar.html', activos=activos, estado_filtro=estado)

@activos_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    unidad_id = session.get('unidad_actual_id')
    if not unidad_id:
        return redirect(url_for('main.inicio'))
    form = ActivoFijoForm()
    form.grupo_id.choices = [(g.id, f'{g.codigo} - {g.nombre}') for g in GrupoContable.query.all()]
    form.auxiliar_id.choices = [(a.id, a.denominacion) for a in AuxiliarContable.query.all()]
    form.oficina_id.choices = [(o.id, o.nombre) for o in Oficina.query.filter_by(unidad_id=unidad_id, estado='ACTIVO').all()]
    form.responsable_id.choices = [(r.id, f'{r.nombre} - {r.cargo}') for r in Responsable.query.all()]

    if form.validate_on_submit():
        if ActivoFijo.query.filter_by(codigo=form.codigo.data).first():
            return render_template('activos/form.html', form=form, error='El código del activo ya existe')
        gestion = Gestion.query.filter_by(cerrada=False).first()
        if not gestion:
            gestion = Gestion(anio=datetime.now().year, cerrada=False)
            db.session.add(gestion)
            db.session.flush()
        activo = ActivoFijo(
            codigo=form.codigo.data, fecha_incorporacion=form.fecha_incorporacion.data,
            descripcion=form.descripcion.data, grupo_id=form.grupo_id.data,
            auxiliar_id=form.auxiliar_id.data, oficina_id=form.oficina_id.data,
            responsable_id=form.responsable_id.data, estado_bien=form.estado_bien.data or None,
            observaciones=form.observaciones.data, codigo_rube=form.codigo_rube.data or None,
            organismo_financiador=form.organismo_financiador.data, numero_convenio=form.numero_convenio.data,
            costo_inicial=form.costo_inicial.data, estado='ELABORADO', gestion_id=gestion.id,
            unidad_id=unidad_id
        )
        db.session.add(activo)
        db.session.commit()
        return redirect(url_for('activos.listar'))
    return render_template('activos/form.html', form=form)

@activos_bp.route('/ver/<int:id>')
@login_required
def ver(id):
    activo = ActivoFijo.query.get_or_404(id)
    revaluos = RevaluoTecnico.query.filter_by(activo_id=id).all()
    bajas = BajaActivo.query.filter_by(activo_id=id).all()
    transferencias = Transferencia.query.filter_by(activo_id=id).all()
    return render_template('activos/ver.html', activo=activo, revaluos=revaluos, bajas=bajas, transferencias=transferencias)

@activos_bp.route('/modificar/<int:id>', methods=['GET', 'POST'])
@login_required
def modificar(id):
    activo = ActivoFijo.query.get_or_404(id)
    unidad_id = session.get('unidad_actual_id')
    form = ActivoFijoForm(obj=activo)
    form.grupo_id.choices = [(g.id, f'{g.codigo} - {g.nombre}') for g in GrupoContable.query.all()]
    form.auxiliar_id.choices = [(a.id, a.denominacion) for a in AuxiliarContable.query.all()]
    form.oficina_id.choices = [(o.id, o.nombre) for o in Oficina.query.filter_by(unidad_id=unidad_id, estado='ACTIVO').all()]
    form.responsable_id.choices = [(r.id, f'{r.nombre} - {r.cargo}') for r in Responsable.query.all()]

    if form.validate_on_submit():
        activo.fecha_incorporacion = form.fecha_incorporacion.data
        activo.descripcion = form.descripcion.data
        activo.grupo_id = form.grupo_id.data
        activo.auxiliar_id = form.auxiliar_id.data
        activo.oficina_id = form.oficina_id.data
        activo.responsable_id = form.responsable_id.data
        activo.estado_bien = form.estado_bien.data or None
        activo.observaciones = form.observaciones.data
        activo.codigo_rube = form.codigo_rube.data or None
        activo.organismo_financiador = form.organismo_financiador.data
        activo.numero_convenio = form.numero_convenio.data
        activo.costo_inicial = form.costo_inicial.data
        if activo.estado == 'APROBADO':
            pass
        db.session.commit()
        return redirect(url_for('activos.ver', id=id))
    return render_template('activos/form.html', form=form, activo=activo)

@activos_bp.route('/aprobar/<int:id>')
@login_required
def aprobar(id):
    activo = ActivoFijo.query.get_or_404(id)
    activo.estado = 'APROBADO'
    db.session.commit()
    return redirect(url_for('activos.ver', id=id))

@activos_bp.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    activo = ActivoFijo.query.get_or_404(id)
    if activo.estado == 'APROBADO':
        return redirect(url_for('activos.ver', id=id))
    db.session.delete(activo)
    db.session.commit()
    return redirect(url_for('activos.listar'))

@activos_bp.route('/duplicar/<int:id>', methods=['GET', 'POST'])
@login_required
def duplicar(id):
    original = ActivoFijo.query.get_or_404(id)
    unidad_id = session.get('unidad_actual_id')
    form = ActivoFijoForm()
    form.grupo_id.choices = [(g.id, f'{g.codigo} - {g.nombre}') for g in GrupoContable.query.all()]
    form.auxiliar_id.choices = [(a.id, a.denominacion) for a in AuxiliarContable.query.all()]
    form.oficina_id.choices = [(o.id, o.nombre) for o in Oficina.query.filter_by(unidad_id=unidad_id, estado='ACTIVO').all()]
    form.responsable_id.choices = [(r.id, f'{r.nombre} - {r.cargo}') for r in Responsable.query.all()]

    if request.method == 'GET':
        form.codigo.data = ''
        form.fecha_incorporacion.data = original.fecha_incorporacion
        form.descripcion.data = original.descripcion
        form.grupo_id.data = original.grupo_id
        form.auxiliar_id.data = original.auxiliar_id
        form.oficina_id.data = original.oficina_id
        form.responsable_id.data = original.responsable_id
        form.estado_bien.data = original.estado_bien
        form.observaciones.data = original.observaciones
        form.codigo_rube.data = original.codigo_rube
        form.organismo_financiador.data = original.organismo_financiador
        form.numero_convenio.data = original.numero_convenio
        form.costo_inicial.data = original.costo_inicial

    if form.validate_on_submit():
        if ActivoFijo.query.filter_by(codigo=form.codigo.data).first():
            return render_template('activos/form.html', form=form, error='El código del activo ya existe', duplicar=True)
        gestion = Gestion.query.filter_by(cerrada=False).first()
        if not gestion:
            gestion = Gestion(anio=datetime.now().year, cerrada=False)
            db.session.add(gestion)
            db.session.flush()
        activo = ActivoFijo(
            codigo=form.codigo.data, fecha_incorporacion=form.fecha_incorporacion.data,
            descripcion=form.descripcion.data, grupo_id=form.grupo_id.data,
            auxiliar_id=form.auxiliar_id.data, oficina_id=form.oficina_id.data,
            responsable_id=form.responsable_id.data, estado_bien=form.estado_bien.data or None,
            observaciones=form.observaciones.data, codigo_rube=form.codigo_rube.data or None,
            organismo_financiador=form.organismo_financiador.data, numero_convenio=form.numero_convenio.data,
            costo_inicial=form.costo_inicial.data, estado='ELABORADO', gestion_id=gestion.id,
            unidad_id=unidad_id
        )
        db.session.add(activo)
        db.session.commit()
        return redirect(url_for('activos.listar'))
    return render_template('activos/form.html', form=form, duplicar=True)

@activos_bp.route('/revaluo/<int:activo_id>', methods=['GET', 'POST'])
@login_required
def revaluo(activo_id):
    activo = ActivoFijo.query.get_or_404(activo_id)
    form = RevaluoForm()
    if form.validate_on_submit():
        rev = RevaluoTecnico(
            activo_id=activo_id, fecha=form.fecha.data, nuevo_costo=form.nuevo_costo.data,
            nueva_vida_util=form.nueva_vida_util.data, disposicion_respaldo=form.disposicion_respaldo.data,
            motivo=form.motivo.data
        )
        db.session.add(rev)
        db.session.commit()
        return redirect(url_for('activos.ver', id=activo_id))
    return render_template('activos/revaluo.html', form=form, activo=activo)

@activos_bp.route('/baja/<int:activo_id>', methods=['GET', 'POST'])
@login_required
def baja(activo_id):
    activo = ActivoFijo.query.get_or_404(activo_id)
    form = BajaForm()
    if form.validate_on_submit():
        baja = BajaActivo(
            activo_id=activo_id, fecha=form.fecha.data, tipo=form.tipo.data,
            motivo=form.motivo.data, disposicion_legal=form.disposicion_legal.data
        )
        db.session.add(baja)
        activo.estado = 'APROBADO'
        db.session.commit()
        return redirect(url_for('activos.ver', id=activo_id))
    return render_template('activos/baja.html', form=form, activo=activo)

@activos_bp.route('/transferir/<int:activo_id>', methods=['GET', 'POST'])
@login_required
def transferir(activo_id):
    activo = ActivoFijo.query.get_or_404(activo_id)
    form = TransferenciaForm()
    form.unidad_destino_id.choices = [(u.id, u.descripcion) for u in UnidadAdministrativa.query.all()]
    form.oficina_destino_id.choices = [(o.id, o.nombre) for o in Oficina.query.filter_by(estado='ACTIVO').all()]
    form.responsable_destino_id.choices = [(r.id, f'{r.nombre} - {r.cargo}') for r in Responsable.query.all()]

    if form.validate_on_submit():
        tipo = form.tipo.data
        trans = Transferencia(activo_id=activo_id, fecha=form.fecha.data, tipo=tipo)
        if tipo == 'ENTRE_UNIDADES':
            trans.unidad_origen_id = activo.unidad_id
            trans.unidad_destino_id = form.unidad_destino_id.data
        else:
            trans.oficina_origen_id = activo.oficina_id
            trans.oficina_destino_id = form.oficina_destino_id.data
            trans.responsable_origen_id = activo.responsable_id
            trans.responsable_destino_id = form.responsable_destino_id.data
        db.session.add(trans)
        if tipo == 'MISMA_UNIDAD':
            activo.oficina_id = form.oficina_destino_id.data
            activo.responsable_id = form.responsable_destino_id.data
        db.session.commit()
        return redirect(url_for('activos.ver', id=activo_id))
    return render_template('activos/transferir.html', form=form, activo=activo)

@activos_bp.route('/buscar')
@login_required
def buscar():
    q = request.args.get('q', '')
    campo = request.args.get('campo', 'codigo')
    unidad_id = session.get('unidad_actual_id')
    query = ActivoFijo.query
    if unidad_id:
        query = query.filter_by(unidad_id=unidad_id)
    if q:
        if campo == 'codigo':
            query = query.filter(ActivoFijo.codigo.contains(q))
        elif campo == 'descripcion':
            query = query.filter(ActivoFijo.descripcion.contains(q))
        elif campo == 'oficina':
            query = query.join(Oficina).filter(Oficina.nombre.contains(q))
        elif campo == 'responsable':
            query = query.join(Responsable).filter(Responsable.nombre.contains(q))
    activos = query.order_by(ActivoFijo.codigo).all()
    return render_template('activos/listar.html', activos=activos, q=q, campo=campo)
