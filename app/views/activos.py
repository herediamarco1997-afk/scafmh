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
    mostrar_todas = session.get('mostrar_todas', False)
    query = ActivoFijo.query
    if unidad_id and not mostrar_todas:
        query = query.filter_by(unidad_id=unidad_id)
    estado = request.args.get('estado', '')
    if estado:
        query = query.filter_by(estado=estado)

    # Solo buscar si hay texto o filtro
    q = request.args.get('q', '').strip()
    campo = request.args.get('campo', 'codigo')
    page = request.args.get('page', 1, type=int)
    per_page = 100

    activos = []
    total = 0
    total_pages = 0
    search_applied = bool(q or estado)

    if q:
        if campo == 'codigo':
            query = query.filter(ActivoFijo.codigo.contains(q))
        elif campo == 'descripcion':
            query = query.filter(ActivoFijo.descripcion.contains(q))
        elif campo == 'oficina':
            query = query.join(Oficina).filter(Oficina.nombre.contains(q))
        elif campo == 'responsable':
            query = query.join(Responsable).filter(Responsable.nombre.contains(q))

    if search_applied:
        total = query.count()
        total_pages = (total + per_page - 1) // per_page
        activos = query.order_by(ActivoFijo.codigo).offset((page - 1) * per_page).limit(per_page).all()

    return render_template('activos/listar.html', activos=activos, q=q, campo=campo,
                           mostrar_todas=mostrar_todas, estado_filtro=estado,
                           total=total, page=page, total_pages=total_pages,
                           search_applied=search_applied)

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
    mostrar_todas = session.get('mostrar_todas', False)
    query = ActivoFijo.query
    if unidad_id and not mostrar_todas:
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
    return render_template('activos/listar.html', activos=activos, q=q, campo=campo, mostrar_todas=mostrar_todas)


@activos_bp.route('/trazabilidad')
@login_required
def trazabilidad():
    """Asset traceability: search by code and see full history."""
    codigo = request.args.get('codigo', '').strip()
    activo = None
    historial = []

    if codigo:
        activo = ActivoFijo.query.filter(
            ActivoFijo.codigo.ilike(f'%{codigo}%')
        ).first()

        if activo:
            # Current assignment
            oficina_actual = db.session.get(Oficina, activo.oficina_id) if activo.oficina_id else None
            responsable_actual = db.session.get(Responsable, activo.responsable_id) if activo.responsable_id else None
            unidad_actual = db.session.get(UnidadAdministrativa, activo.unidad_id) if activo.unidad_id else None
            grupo_actual = db.session.get(GrupoContable, activo.grupo_id) if activo.grupo_id else None

            # Initial record (creation)
            historial.append({
                'tipo': 'ASIGNACION_INICIAL',
                'fecha': activo.fecha_incorporacion or activo.fecha_adquisicion or 'N/A',
                'responsable': responsable_actual.nombre if responsable_actual else 'Sin asignar',
                'oficina': oficina_actual.nombre if oficina_actual else 'Sin oficina',
                'unidad': unidad_actual.descripcion if unidad_actual else '',
                'usuario': 'Sistema',
                'nota': 'Registro inicial del activo en el sistema',
                'color': '#28a745',
                'icono': '🟢',
            })

            # All transfers
            transfers = Transferencia.query.filter_by(activo_id=activo.id).order_by(Transferencia.fecha, Transferencia.id).all()
            for t in transfers:
                resp_origen = db.session.get(Responsable, t.responsable_origen_id) if t.responsable_origen_id else None
                resp_dest = db.session.get(Responsable, t.responsable_destino_id) if t.responsable_destino_id else None
                ofi_origen = db.session.get(Oficina, t.oficina_origen_id) if t.oficina_origen_id else None
                ofi_dest = db.session.get(Oficina, t.oficina_destino_id) if t.oficina_destino_id else None

                # Get acta code if available
                acta_code = ''
                if t.acta_id:
                    from app.models import TransferenciaActa
                    acta = db.session.get(TransferenciaActa, t.acta_id)
                    acta_code = acta.codigo if acta else ''

                historial.append({
                    'tipo': 'TRANSFERENCIA',
                    'fecha': t.fecha.strftime('%d/%m/%Y') if t.fecha else 'N/A',
                    'responsable': f'{resp_origen.nombre if resp_origen else "?"} → {resp_dest.nombre if resp_dest else "?"}',
                    'oficina': f'{ofi_origen.nombre if ofi_origen else "?"} → {ofi_dest.nombre if ofi_dest else "?"}',
                    'unidad': '',
                    'usuario': t.usuario or '',
                    'nota': f'Acta: {acta_code}' if acta_code else '',
                    'color': '#2c5f8a',
                    'icono': '🔄',
                })

            # Inventory records
            from app.models import InventarioFisico
            inventarios = InventarioFisico.query.filter_by(activo_id=activo.id).order_by(InventarioFisico.fecha_toma).all()
            for inv in inventarios:
                historial.append({
                    'tipo': 'TOMA_FISICA',
                    'fecha': inv.fecha_toma.strftime('%d/%m/%Y %H:%M') if inv.fecha_toma else 'N/A',
                    'responsable': inv.responsable_reportado or responsable_actual.nombre if responsable_actual else '',
                    'oficina': inv.ubicacion_reportada or oficina_actual.nombre if oficina_actual else '',
                    'unidad': '',
                    'usuario': inv.usuario or '',
                    'nota': f'Resultado: {inv.resultado}',
                    'color': '#ffc107',
                    'icono': '📷',
                })

    return render_template('activos/trazabilidad.html', activo=activo, historial=historial, codigo=codigo)
