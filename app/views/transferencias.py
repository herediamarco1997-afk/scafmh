from flask import Blueprint, render_template, request, redirect, url_for, session, Response, flash, send_file
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import ActivoFijo, Oficina, Responsable, Transferencia, TransferenciaActa, UnidadAdministrativa, AuxiliarContable
from app.dbf_export import export_all
from app.pdf_reportes import generar_pdf_acta_transferencia
from app import db
from datetime import date, datetime
import zipfile, io, os

transferencias_bp = Blueprint('transferencias', __name__, url_prefix='/transferencias')


def _crear_acta(activo_ids, oficina_dest_id, responsable_dest_id, fecha_trans):
    """Create an acta grouping multiple transfers. Returns the acta object."""
    gestion = fecha_trans.year
    # Get next sequential number for this year
    last = db.session.query(func.max(TransferenciaActa.numero)).filter_by(gestion=gestion).scalar()
    numero = (last or 0) + 1
    codigo = f'ACTA-{gestion}-{numero:04d}'

    # Get origin data from first asset
    primer_activo = ActivoFijo.query.get(activo_ids[0]) if activo_ids else None
    oficina_origen_id = primer_activo.oficina_id if primer_activo else None
    responsable_origen_id = primer_activo.responsable_id if primer_activo else None

    acta = TransferenciaActa(
        numero=numero,
        gestion=gestion,
        codigo=codigo,
        fecha=fecha_trans,
        oficina_origen_id=oficina_origen_id,
        responsable_origen_id=responsable_origen_id,
        oficina_destino_id=oficina_dest_id,
        responsable_destino_id=responsable_dest_id,
        cantidad_activos=len(activo_ids),
        usuario=current_user.username,
    )
    db.session.add(acta)
    db.session.flush()  # Get acta.id before creating transfers
    return acta


@transferencias_bp.route('/')
@login_required
def listar():
    """List actas (grouped transfers) instead of individual transfers for performance."""
    unidad_id = session.get('unidad_actual_id')
    mostrar_todas = session.get('mostrar_todas', False)
    page = request.args.get('page', 1, type=int)
    per_page = 20

    q = TransferenciaActa.query
    # Filter by unit if needed
    if unidad_id and not mostrar_todas:
        q = q.join(Oficina, TransferenciaActa.oficina_destino_id == Oficina.id).filter(Oficina.unidad_id == unidad_id)

    total = q.count()
    total_pages = (total + per_page - 1) // per_page
    actas = q.order_by(TransferenciaActa.id.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return render_template('transferencias/listar.html', actas=actas, page=page, total=total, total_pages=total_pages)


@transferencias_bp.route('/acta_detalle/<int:acta_id>')
@login_required
def acta_detalle(acta_id):
    """Show detail of a specific acta with all its transfers."""
    acta = db.session.get(TransferenciaActa, acta_id)
    if not acta:
        flash('Acta no encontrada', 'danger')
        return redirect(url_for('transferencias.listar'))

    transfers = Transferencia.query.filter_by(acta_id=acta_id).order_by(Transferencia.id).all()
    return render_template('transferencias/acta_detalle.html', acta=acta, transfers=transfers)


@transferencias_bp.route('/individual', methods=['GET', 'POST'])
@login_required
def individual():
    """Transfer individual assets: search by code/description, select destination."""
    unidad_id = session.get('unidad_actual_id')
    activos = []
    busqueda = ''
    dest_oficinas = Oficina.query.filter_by(estado='ACTIVO').order_by(Oficina.nombre).all()
    dest_responsables = Responsable.query.order_by(Responsable.nombre).all()

    if request.method == 'POST':
        accion = request.form.get('accion', '')

        if accion == 'buscar':
            busqueda = request.form.get('busqueda', '')
            q = ActivoFijo.query
            if unidad_id:
                q = q.filter_by(unidad_id=unidad_id)
            q = q.filter(
                db.or_(
                    ActivoFijo.codigo.ilike(f'%{busqueda}%'),
                    ActivoFijo.descripcion.ilike(f'%{busqueda}%')
                )
            ).order_by(ActivoFijo.codigo).limit(50)
            activos = q.all()

        elif accion == 'transferir':
            activo_ids_raw = request.form.get('activo_ids', '')
            oficina_dest_id = request.form.get('oficina_destino_id', type=int)
            responsable_dest_id = request.form.get('responsable_destino_id', type=int)
            fecha_trans = request.form.get('fecha', str(date.today()))

            # Parse comma-separated IDs
            activo_ids = [int(x.strip()) for x in activo_ids_raw.split(',') if x.strip().isdigit()]

            if not activo_ids:
                flash('Seleccione al menos un activo', 'danger')
            elif not responsable_dest_id:
                flash('Seleccione un responsable destino', 'danger')
            else:
                fec = datetime.strptime(fecha_trans, '%Y-%m-%d').date()

                # Create acta
                acta = _crear_acta(activo_ids, oficina_dest_id, responsable_dest_id, fec)

                for aid in activo_ids:
                    a = ActivoFijo.query.get(aid)
                    if not a:
                        continue
                    t = Transferencia(
                        activo_id=a.id,
                        fecha=fec,
                        tipo='MISMA_UNIDAD',
                        oficina_origen_id=a.oficina_id,
                        responsable_origen_id=a.responsable_id,
                        oficina_destino_id=oficina_dest_id or a.oficina_id,
                        responsable_destino_id=responsable_dest_id,
                        usuario=current_user.username,
                        acta_id=acta.id,
                    )
                    db.session.add(t)
                    a.oficina_id = oficina_dest_id or a.oficina_id
                    a.responsable_id = responsable_dest_id

                db.session.commit()
                flash(f'{len(activo_ids)} activo(s) transferido(s) - {acta.codigo}', 'success')
                return redirect(url_for('transferencias.acta_detalle', acta_id=acta.id))

    return render_template('transferencias/individual.html',
                         activos=activos, busqueda=busqueda,
                         dest_oficinas=dest_oficinas,
                         dest_responsables=dest_responsables,
                         hoy=date.today())


@transferencias_bp.route('/masiva', methods=['GET', 'POST'])
@login_required
def masiva():
    """Massive transfer: select a source responsible, see all their assets, transfer all."""
    unidad_id = session.get('unidad_actual_id')
    activos = []
    responsable_origen = None
    dest_oficinas = Oficina.query.filter_by(estado='ACTIVO').order_by(Oficina.nombre).all()
    dest_responsables = Responsable.query.order_by(Responsable.nombre).all()

    # Get all responsables with activo count for the form (sin filtro de unidad)
    q_resp = db.session.query(
        Responsable,
        func.count(ActivoFijo.id).label('num_activos')
    ).outerjoin(ActivoFijo, ActivoFijo.responsable_id == Responsable.id)
    responsables_lista = q_resp.group_by(Responsable.id).order_by(Responsable.nombre).all()

    if request.method == 'POST':
        accion = request.form.get('accion', '')

        if accion == 'ver_activos':
            resp_id = request.form.get('responsable_origen_id', type=int)
            if resp_id:
                responsable_origen = Responsable.query.get(resp_id)
                activos = ActivoFijo.query.filter_by(responsable_id=resp_id).order_by(ActivoFijo.codigo).all()

        elif accion == 'transferir_todos':
            resp_origen_id = request.form.get('resp_origen_id', type=int)
            oficina_dest_id = request.form.get('oficina_destino_id', type=int)
            responsable_dest_id = request.form.get('responsable_destino_id', type=int)
            fecha_trans = request.form.get('fecha', str(date.today()))
            activo_ids = request.form.getlist('activo_ids')

            if not resp_origen_id:
                flash('Seleccione un responsable de origen', 'danger')
            elif not responsable_dest_id:
                flash('Seleccione un responsable destino', 'danger')
            elif not activo_ids:
                flash('Seleccione al menos un activo para transferir', 'danger')
            else:
                responsable_origen = db.session.get(Responsable, resp_origen_id)
                int_ids = [int(x) for x in activo_ids]
                activos_origen = ActivoFijo.query.filter(ActivoFijo.id.in_(int_ids)).all()
                fec = datetime.strptime(fecha_trans, '%Y-%m-%d').date()

                # Create acta
                acta = _crear_acta(int_ids, oficina_dest_id, responsable_dest_id, fec)

                for a in activos_origen:
                    t = Transferencia(
                        activo_id=a.id,
                        fecha=fec,
                        tipo='MISMA_UNIDAD',
                        oficina_origen_id=a.oficina_id,
                        responsable_origen_id=a.responsable_id,
                        oficina_destino_id=oficina_dest_id or a.oficina_id,
                        responsable_destino_id=responsable_dest_id,
                        usuario=current_user.username,
                        acta_id=acta.id,
                    )
                    db.session.add(t)
                    a.oficina_id = oficina_dest_id or a.oficina_id
                    a.responsable_id = responsable_dest_id

                db.session.commit()
                responsable_dest = db.session.get(Responsable, responsable_dest_id)
                flash(f'{len(int_ids)} activo(s) transferidos - {acta.codigo}', 'success')
                return redirect(url_for('transferencias.acta_detalle', acta_id=acta.id))

    return render_template('transferencias/masiva.html',
                         activos=activos,
                         responsable_origen=responsable_origen,
                         responsables_lista=responsables_lista,
                         dest_oficinas=dest_oficinas,
                         dest_responsables=dest_responsables,
                         hoy=date.today())


@transferencias_bp.route('/acta')
@login_required
def acta():
    """Generate 'Acta de Asignacion Individual de Bienes' in PDF format."""
    responsable_id = request.args.get('responsable_id', type=int)
    transfer_id = request.args.get('transfer_id', type=int)
    acta_id = request.args.get('acta_id', type=int)

    if acta_id:
        # PDF from acta: get transfers from acta
        acta_obj = db.session.get(TransferenciaActa, acta_id)
        if not acta_obj:
            flash('Acta no encontrada', 'danger')
            return redirect(url_for('transferencias.listar'))
        responsable_id = acta_obj.responsable_destino_id

    if not responsable_id:
        flash('Seleccione un responsable', 'danger')
        return redirect(url_for('transferencias.listar'))

    resp = db.session.get(Responsable, responsable_id)
    if not resp:
        flash('Responsable no encontrado', 'danger')
        return redirect(url_for('transferencias.listar'))

    ofi = db.session.get(Oficina, resp.oficina_id)
    uni = db.session.get(UnidadAdministrativa, ofi.unidad_id) if ofi else None

    # Get assets: if acta_id, use acta transfers; else all of the responsable
    if acta_id:
        transfers = Transferencia.query.filter_by(acta_id=acta_id).all()
        activos_raw = [db.session.get(ActivoFijo, t.activo_id) for t in transfers]
    elif transfer_id:
        t = db.session.get(Transferencia, transfer_id)
        if t and t.responsable_destino_id == responsable_id:
            activos_raw = [db.session.get(ActivoFijo, t.activo_id)] if t.activo_id else []
        else:
            activos_raw = ActivoFijo.query.filter_by(responsable_id=responsable_id).all()
    else:
        activos_raw = ActivoFijo.query.filter_by(responsable_id=responsable_id).all()

    activos = []
    for a in activos_raw:
        if not a:
            continue
        aux = db.session.get(AuxiliarContable, a.auxiliar_id) if a.auxiliar_id else None
        aux_name = ('%s - %s' % (aux.id, aux.denominacion[:25])) if aux else ''
        activos.append({
            'codigo': a.codigo or '',
            'auxiliar': aux_name,
            'descripcion': a.descripcion or '',
            'estado_bien': a.estado_bien or 'BUENO',
        })

    responsable_data = {
        'nombre': resp.nombre or '',
        'cargo': resp.cargo or '',
        'carnet_identidad': resp.carnet_identidad or '',
        'unidad_codigo': uni.codigo if uni else '',
        'unidad_desc': uni.descripcion if uni else '',
    }
    oficina_data = {
        'codofic': str(ofi.codofic) if ofi else '',
        'nombre': ofi.nombre if ofi else '',
    }

    hoy = request.args.get('fecha')
    if hoy:
        from datetime import datetime as dt
        hoy = dt.strptime(hoy, '%Y-%m-%d').date()
    else:
        from datetime import date as d
        hoy = d.today()

    pdf = generar_pdf_acta_transferencia(responsable_data, oficina_data, activos, hoy)
    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)

    # Name the file with acta code if available
    acta_code = acta_obj.codigo if acta_id and acta_obj else ''
    filename = f'{acta_code}_{resp.nombre[:20].strip()}_{hoy.strftime("%Y%m%d")}.pdf' if acta_code else f'acta_asignacion_{resp.nombre[:20].strip()}_{hoy.strftime("%Y%m%d")}.pdf'

    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=filename)


@transferencias_bp.route('/exportar_dbf')
@login_required
def exportar_dbf():
    """Generate and download updated DBF files as a zip."""
    try:
        result = export_all()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(result['output_dir']):
                fpath = os.path.join(result['output_dir'], fname)
                if os.path.isfile(fpath):
                    zf.write(fpath, fname)
        buf.seek(0)
        return Response(
            buf.getvalue(),
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment;filename=scafmh_dbf_export_{date.today().strftime("%Y%m%d")}.zip'}
        )
    except Exception as e:
        flash(f'Error al exportar DBF: {str(e)}', 'danger')
        return redirect(url_for('transferencias.listar'))
