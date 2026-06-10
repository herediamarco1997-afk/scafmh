from flask import Blueprint, render_template, request, redirect, url_for, session, Response, flash, send_file
from flask_login import login_required, current_user
from app.models import ActivoFijo, Oficina, Responsable, Transferencia, UnidadAdministrativa, AuxiliarContable
from app.dbf_export import export_all
from app.pdf_reportes import generar_pdf_acta_transferencia
from app import db
from datetime import date, datetime
import zipfile, io, os

transferencias_bp = Blueprint('transferencias', __name__, url_prefix='/transferencias')

@transferencias_bp.route('/')
@login_required
def listar():
    unidad_id = session.get('unidad_actual_id')
    q = Transferencia.query
    if unidad_id:
        q = q.join(ActivoFijo).filter(ActivoFijo.unidad_id == unidad_id)
    transfers = q.order_by(Transferencia.id.desc()).all()
    return render_template('transferencias/listar.html', transfers=transfers)

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
            activo_ids = request.form.getlist('activo_ids')
            oficina_dest_id = request.form.get('oficina_destino_id', type=int)
            responsable_dest_id = request.form.get('responsable_destino_id', type=int)
            fecha_trans = request.form.get('fecha', str(date.today()))

            if not activo_ids:
                flash('Seleccione al menos un activo', 'danger')
            elif not responsable_dest_id:
                flash('Seleccione un responsable destino', 'danger')
            else:
                fec = datetime.strptime(fecha_trans, '%Y-%m-%d').date()
                count = 0
                for aid in activo_ids:
                    a = ActivoFijo.query.get(int(aid))
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
                    )
                    db.session.add(t)
                    a.oficina_id = oficina_dest_id or a.oficina_id
                    a.responsable_id = responsable_dest_id
                    count += 1
                db.session.commit()
                flash(f'{count} activo(s) transferido(s) exitosamente', 'success')
                return redirect(url_for('transferencias.acta', responsable_id=responsable_dest_id))

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

    # Get all responsables for the form
    q_resp = Responsable.query
    if unidad_id:
        q_resp = q_resp.join(Oficina).filter(Oficina.unidad_id == unidad_id)
    responsables_lista = q_resp.order_by(Responsable.nombre).all()

    if request.method == 'POST':
        accion = request.form.get('accion', '')

        if accion == 'ver_activos':
            resp_id = request.form.get('responsable_origen_id', type=int)
            if resp_id:
                responsable_origen = Responsable.query.get(resp_id)
                q = ActivoFijo.query.filter_by(responsable_id=resp_id)
                if unidad_id:
                    q = q.filter_by(unidad_id=unidad_id)
                activos = q.order_by(ActivoFijo.codigo).all()

        elif accion == 'transferir_todos':
            resp_origen_id = request.form.get('resp_origen_id', type=int)
            oficina_dest_id = request.form.get('oficina_destino_id', type=int)
            responsable_dest_id = request.form.get('responsable_destino_id', type=int)
            fecha_trans = request.form.get('fecha', str(date.today()))

            if not resp_origen_id:
                flash('Seleccione un responsable de origen', 'danger')
            elif not responsable_dest_id:
                flash('Seleccione un responsable destino', 'danger')
            else:
                responsable_origen = db.session.get(Responsable, resp_origen_id)
                q = ActivoFijo.query.filter_by(responsable_id=resp_origen_id)
                if unidad_id:
                    q = q.filter_by(unidad_id=unidad_id)
                activos_origen = q.all()
                fec = datetime.strptime(fecha_trans, '%Y-%m-%d').date()
                count = 0
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
                    )
                    db.session.add(t)
                    a.oficina_id = oficina_dest_id or a.oficina_id
                    a.responsable_id = responsable_dest_id
                    count += 1
                db.session.commit()
                responsable_dest = db.session.get(Responsable, responsable_dest_id)
                flash(f'{count} activo(s) transferidos masivamente de {responsable_origen.nombre if responsable_origen else "Origen"} a {responsable_dest.nombre if responsable_dest else "Destino"}', 'success')
                return redirect(url_for('transferencias.acta', responsable_id=responsable_dest_id))

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
    if not responsable_id:
        flash('Seleccione un responsable', 'danger')
        return redirect(url_for('transferencias.listar'))

    resp = db.session.get(Responsable, responsable_id)
    if not resp:
        flash('Responsable no encontrado', 'danger')
        return redirect(url_for('transferencias.listar'))

    ofi = db.session.get(Oficina, resp.oficina_id)
    uni = db.session.get(UnidadAdministrativa, ofi.unidad_id) if ofi else None

    # Get assets: if transfer_id specified, get only transferred assets; else all of the responsable
    if transfer_id:
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
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f'acta_asignacion_{resp.nombre[:20].strip()}_{hoy.strftime("%Y%m%d")}.pdf')


@transferencias_bp.route('/exportar_dbf')
@login_required
def exportar_dbf():
    """Generate and download updated DBF files as a zip."""
    try:
        result = export_all()
        # Create zip in memory
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
