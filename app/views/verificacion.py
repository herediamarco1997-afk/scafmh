from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from app.models import ActivoFijo, Oficina, Responsable, Transferencia, TransferenciaActa, InventarioFisico
from app import db
from datetime import date, datetime

verificacion_bp = Blueprint('verificacion', __name__, url_prefix='/verificacion')


@verificacion_bp.route('/')
@login_required
def listar():
    """Search assets by responsable (funcionario) and show verification checkboxes."""
    resp_id = request.args.get('resp_id', type=int)
    activos = []
    responsable = None

    if resp_id:
        responsable = db.session.get(Responsable, resp_id)
        activos = ActivoFijo.query.filter_by(responsable_id=resp_id).order_by(ActivoFijo.codigo).all()

        # Single query to get latest verification status for all these assets
        codigos = [a.codigo for a in activos]
        verificados = {}
        if codigos:
            subq = (
                db.session.query(
                    InventarioFisico.codigo,
                    InventarioFisico.resultado,
                    func.row_number().over(
                        partition_by=InventarioFisico.codigo,
                        order_by=desc(InventarioFisico.fecha_toma)
                    ).label('rn')
                )
                .filter(InventarioFisico.codigo.in_(codigos))
                .subquery()
            )
            rows = db.session.query(subq.c.codigo, subq.c.resultado).filter(subq.c.rn == 1).all()
            verificados = {r[0]: (r[1] == 'VERIFICADO') for r in rows}

        for a in activos:
            a.es_verificado = verificados.get(a.codigo, False)

    # Get responsables with activo count for the dropdown
    q_resp = (
        db.session.query(Responsable, func.count(ActivoFijo.id).label('num'))
        .outerjoin(ActivoFijo, ActivoFijo.responsable_id == Responsable.id)
        .group_by(Responsable.id)
        .order_by(Responsable.nombre)
    )
    responsables_lista = q_resp.all()

    return render_template('verificacion/listar.html',
                         activos=activos,
                         responsable=responsable,
                         responsables_lista=responsables_lista)


@verificacion_bp.route('/transferir', methods=['GET', 'POST'])
@login_required
def transferir():
    """Transfer selected assets to another responsable, creating an acta."""
    if request.method == 'POST':
        activo_ids = request.form.getlist('activo_ids')
        oficina_dest_id = request.form.get('oficina_destino_id', type=int)
        responsable_dest_id = request.form.get('responsable_destino_id', type=int)
        fecha_trans = request.form.get('fecha', str(date.today()))
        resp_origen_id = request.form.get('resp_origen_id', type=int)

        if not activo_ids:
            flash('Selecciona al menos un activo para transferir', 'danger')
            return redirect(url_for('verificacion.listar'))
        if not responsable_dest_id:
            flash('Selecciona un responsable destino', 'danger')
            return redirect(url_for('verificacion.listar', resp_id=resp_origen_id))

        fec = datetime.strptime(fecha_trans, '%Y-%m-%d').date()

        # Create acta
        gestion = fec.year
        last_acta = db.session.query(func.max(TransferenciaActa.numero)).filter_by(gestion=gestion).scalar()
        numero = (last_acta or 0) + 1
        codigo = f'ACTA-{gestion}-{numero:04d}'

        primer_activo = ActivoFijo.query.get(int(activo_ids[0]))
        acta = TransferenciaActa(
            numero=numero, gestion=gestion, codigo=codigo, fecha=fec,
            oficina_origen_id=primer_activo.oficina_id if primer_activo else None,
            responsable_origen_id=primer_activo.responsable_id if primer_activo else None,
            oficina_destino_id=oficina_dest_id,
            responsable_destino_id=responsable_dest_id,
            cantidad_activos=len(activo_ids),
            usuario=current_user.username,
            notas='Transferencia desde módulo de verificación',
        )
        db.session.add(acta)
        db.session.flush()

        count = 0
        for aid in activo_ids:
            a = ActivoFijo.query.get(int(aid))
            if not a:
                continue
            t = Transferencia(
                activo_id=a.id, fecha=fec, tipo='MISMA_UNIDAD',
                oficina_origen_id=a.oficina_id, responsable_origen_id=a.responsable_id,
                oficina_destino_id=oficina_dest_id or a.oficina_id,
                responsable_destino_id=responsable_dest_id,
                usuario=current_user.username, acta_id=acta.id,
            )
            db.session.add(t)
            a.oficina_id = oficina_dest_id or a.oficina_id
            a.responsable_id = responsable_dest_id
            count += 1

        db.session.commit()
        flash(f'{count} activo(s) transferido(s) - Acta {codigo}', 'success')
        return redirect(url_for('transferencias.acta_detalle', acta_id=acta.id))

    # GET: show transfer form
    activo_ids = request.args.getlist('activo_ids')
    resp_origen_id = request.args.get('resp_origen_id', type=int)
    if not activo_ids:
        flash('No se seleccionaron activos', 'danger')
        return redirect(url_for('verificacion.listar'))

    activos = ActivoFijo.query.filter(ActivoFijo.id.in_([int(x) for x in activo_ids])).all()
    dest_oficinas = Oficina.query.filter_by(estado='ACTIVO').order_by(Oficina.nombre).all()
    dest_responsables = Responsable.query.order_by(Responsable.nombre).all()

    return render_template('verificacion/transferir.html',
                         activos=activos, resp_origen_id=resp_origen_id,
                         dest_oficinas=dest_oficinas,
                         dest_responsables=dest_responsables,
                         hoy=date.today())


@verificacion_bp.route('/constancia/<int:resp_id>')
@login_required
def constancia(resp_id):
    """Print verification report (constancia) for a responsable."""
    responsable = db.session.get(Responsable, resp_id)
    if not responsable:
        flash('Responsable no encontrado', 'danger')
        return redirect(url_for('verificacion.listar'))

    activos = ActivoFijo.query.filter_by(responsable_id=resp_id).order_by(ActivoFijo.codigo).all()

    # Get latest verification status
    codigos = [a.codigo for a in activos]
    verificados = {}
    if codigos:
        subq = (
            db.session.query(
                InventarioFisico.codigo,
                InventarioFisico.resultado,
                func.row_number().over(
                    partition_by=InventarioFisico.codigo,
                    order_by=desc(InventarioFisico.fecha_toma)
                ).label('rn')
            )
            .filter(InventarioFisico.codigo.in_(codigos))
            .subquery()
        )
        rows = db.session.query(subq.c.codigo, subq.c.resultado).filter(subq.c.rn == 1).all()
        verificados = {r[0]: (r[1] == 'VERIFICADO') for r in rows}

    # Build report data
    reporte = []
    for a in activos:
        estado = 'VERIFICADO' if verificados.get(a.codigo, False) else 'NO VERIFICADO'
        reporte.append({
            'codigo': a.codigo,
            'descripcion': a.descripcion,
            'estado': estado,
            'oficina': a.oficina_rel.nombre if a.oficina_rel else '',
        })

    total = len(reporte)
    n_verificados = sum(1 for r in reporte if r['estado'] == 'VERIFICADO')
    n_no_verificados = total - n_verificados

    oficina = db.session.get(Oficina, responsable.oficina_id) if responsable.oficina_id else None
    unidad = None
    if oficina:
        from app.models import UnidadAdministrativa
        unidad = db.session.get(UnidadAdministrativa, oficina.unidad_id) if oficina.unidad_id else None

    return render_template('verificacion/constancia.html',
                         responsable=responsable,
                         oficina=oficina, unidad=unidad,
                         reporte=reporte,
                         total=total,
                         n_verificados=n_verificados,
                         n_no_verificados=n_no_verificados,
                         fecha_hoy=date.today())
