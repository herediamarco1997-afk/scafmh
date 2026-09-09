from flask import Blueprint, render_template, request, session, Response, url_for, redirect
from flask_login import login_required
from app.models import (ActivoFijo, GrupoContable, AuxiliarContable, Oficina, Responsable,
                        BajaActivo, RevaluoTecnico, Transferencia, IndiceUFV, UnidadAdministrativa)
from app.depreciacion import calc_depreciacion_activo, calc_resumen_grupo, get_ufv_today
from app import db
from datetime import datetime, date
import csv, io
from collections import OrderedDict, defaultdict

reportes_bp = Blueprint('reportes', __name__)

REPORTES = [
    {'num': 1, 'nombre': 'Inventario Ordenado por Código de Activo'},
    {'num': 2, 'nombre': 'Inventario Ordenado por Grupo Contable'},
    {'num': 3, 'nombre': 'Inventario Ordenado por Grupo y Auxiliar Contable'},
    {'num': 4, 'nombre': 'Inventario Ordenado por Oficina'},
    {'num': 5, 'nombre': 'Inventario Ordenado por Oficina y Responsable'},
    {'num': 6, 'nombre': 'Resumen de Activos Fijos por Grupo'},
    {'num': 7, 'nombre': 'Detalle de Responsables por Oficina'},
    {'num': 8, 'nombre': 'Reporte de Transferencia de Activos'},
    {'num': 9, 'nombre': 'Reporte Histórico de Activos Dados de Baja'},
    {'num': 10, 'nombre': 'Inventario de Activos Fijos por Grupo Contable'},
    {'num': 11, 'nombre': 'Reporte de Índices UFV'},
    {'num': 12, 'nombre': 'Reporte Histórico de Activos Revaluados'},
    {'num': 13, 'nombre': 'Asignación Individual de Bienes'},
    {'num': 14, 'nombre': 'Reporte de Bajas por Error de Transcripción'},
    {'num': 15, 'nombre': 'Resumen de Activos Fijos ordenado por Grupo Contable'},
    {'num': 16, 'nombre': 'Acta de Devolución de Bienes'},
    {'num': 17, 'nombre': 'Inventario Ordenado por Grupo Contable y Organismo'},
]

def get_unidad_info(unidad_id):
    if not unidad_id:
        return {'codigo': '', 'descripcion': ''}
    u = UnidadAdministrativa.query.get(unidad_id)
    return {'codigo': u.codigo if u else '', 'descripcion': u.descripcion if u else ''}

def fmt(n):
    if n is None: return '0.00'
    return f'{float(n):,.2f}'.replace(',', ' ')

def _pdf_response(pdf, filename):
    from io import BytesIO
    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment;filename={filename}.pdf'})

@reportes_bp.route('/')
@login_required
def listar():
    return render_template('reportes/listar.html', reportes=REPORTES)

@reportes_bp.route('/generar/<int:num>')
@login_required
def generar(num):
    unidad_id = session.get('unidad_actual_id')
    mostrar_todas = session.get('mostrar_todas', False)
    unidad = get_unidad_info(unidad_id) if not mostrar_todas else None
    hoy = date.today()
    gestion = hoy.year
    ufv = get_ufv_today()

    fmt_local = fmt
    output_format = request.args.get('formato', 'html')

    def base_query():
        q = ActivoFijo.query
        if unidad_id and not mostrar_todas:
            q = q.filter_by(unidad_id=unidad_id)
        return q

    if output_format == 'pdf':
        from app.pdf_reportes import (generar_pdf_inv_codigo, generar_pdf_inv_grupo_detalle,
                                       generar_pdf_resumen_grupo, generar_pdf_ufv,
                                       generar_pdf_activos_simple, generar_pdf_asignacion)

    if num == 1:
        data = base_query().order_by(ActivoFijo.codigo).all()
        rows = [calc_depreciacion_activo(a, hoy, gestion) for a in data]
        if output_format == 'pdf':
            pdf = generar_pdf_inv_codigo(rows, unidad, ufv, hoy)
            return _pdf_response(pdf, f'reporte_{num}')
        return render_template('reportes/inv_codigo.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             rows=rows, unidad=unidad, ufv=ufv, hoy=hoy, fmt=fmt_local)

    elif num == 2:
        data = base_query().join(GrupoContable).order_by(GrupoContable.codigo, ActivoFijo.codigo).all()
        rows = [calc_depreciacion_activo(a, hoy, gestion) for a in data]
        if output_format == 'pdf':
            hdrs = ['CODIGO', 'DESCRIPCION', 'FECHA', 'COSTO', 'COSTO ACTUAL',
                    'DEP. ACUM.', 'DEP. GESTION', 'VALOR NETO', 'GRUPO']
            cw = [18, 50, 14, 18, 20, 20, 18, 20, 30]
            pdf = generar_pdf_activos_simple(rows, unidad, ufv, hoy, REPORTES[num-1]['nombre'],
                                             hdrs, cw)
            return _pdf_response(pdf, f'reporte_{num}')
        return render_template('reportes/inv_grupo.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             rows=rows, unidad=unidad, ufv=ufv, hoy=hoy, fmt=fmt_local)

    elif num == 3:
        data = base_query().join(GrupoContable).join(AuxiliarContable).order_by(
            GrupoContable.codigo, AuxiliarContable.id, ActivoFijo.codigo).all()
        rows = [calc_depreciacion_activo(a, hoy, gestion) for a in data]
        if output_format == 'pdf':
            hdrs = ['CODIGO', 'DESCRIPCION', 'COSTO', 'COSTO ACT.', 'DEP. ACUM.', 'VALOR NETO']
            cw = [18, 60, 22, 24, 24, 24]
            pdf = generar_pdf_activos_simple(rows, unidad, ufv, hoy, REPORTES[num-1]['nombre'],
                                             hdrs, cw)
            return _pdf_response(pdf, f'reporte_{num}')
        return render_template('reportes/inv_grupo_aux.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             rows=rows, unidad=unidad, ufv=ufv, hoy=hoy, fmt=fmt_local)

    elif num == 4:
        data = base_query().join(Oficina).order_by(Oficina.nombre, ActivoFijo.codigo).all()
        rows = [calc_depreciacion_activo(a, hoy, gestion) for a in data]
        if output_format == 'pdf':
            hdrs = ['CODIGO', 'DESCRIPCION', 'OFICINA', 'COSTO', 'COSTO ACT.',
                    'DEP. ACUM.', 'VALOR NETO']
            cw = [16, 40, 28, 20, 20, 20, 22]
            pdf = generar_pdf_activos_simple(rows, unidad, ufv, hoy, REPORTES[num-1]['nombre'],
                                             hdrs, cw)
            return _pdf_response(pdf, f'reporte_{num}')
        return render_template('reportes/inv_oficina.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             rows=rows, unidad=unidad, ufv=ufv, hoy=hoy, fmt=fmt_local)

    elif num == 5:
        data = base_query().join(Oficina).join(Responsable).order_by(
            Oficina.nombre, Responsable.nombre, ActivoFijo.codigo).all()
        rows = [calc_depreciacion_activo(a, hoy, gestion) for a in data]
        if output_format == 'pdf':
            hdrs = ['OFICINA', 'RESPONSABLE', 'CODIGO', 'DESCRIPCION', 'COSTO', 'VALOR NETO']
            cw = [25, 25, 16, 40, 20, 20]
            pdf = generar_pdf_activos_simple(rows, unidad, ufv, hoy, REPORTES[num-1]['nombre'],
                                             hdrs, cw)
            return _pdf_response(pdf, f'reporte_{num}')
        return render_template('reportes/inv_oficina_resp.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             rows=rows, unidad=unidad, ufv=ufv, hoy=hoy, fmt=fmt_local)

    elif num == 6:
        resumen, total, ufv_val = calc_resumen_grupo(unidad_id, gestion, hoy)
        if output_format == 'pdf':
            pdf = generar_pdf_resumen_grupo(resumen, total, unidad, ufv_val, hoy)
            return _pdf_response(pdf, f'reporte_{num}')
        return render_template('reportes/resumen_grupo.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             resumen=resumen, total=total, unidad=unidad, ufv=ufv_val, hoy=hoy, fmt=fmt_local)

    elif num == 7:
        data = Responsable.query.join(Oficina).order_by(Oficina.nombre, Responsable.nombre).all()
        return render_template('reportes/responsables_oficina.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             data=data, unidad=unidad)

    elif num == 8:
        q = Transferencia.query
        data = q.order_by(Transferencia.fecha.desc()).all()
        return render_template('reportes/transferencias.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             data=data, unidad=unidad, hoy=hoy)

    elif num == 9:
        q = BajaActivo.query
        data = q.order_by(BajaActivo.fecha.desc()).all()
        return render_template('reportes/bajas_historicas.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             data=data, unidad=unidad, hoy=hoy)

    elif num == 10:
        data = base_query().join(GrupoContable).order_by(GrupoContable.codigo, ActivoFijo.codigo).all()
        rows = [calc_depreciacion_activo(a, hoy, gestion) for a in data]
        if output_format == 'pdf':
            pdf = generar_pdf_inv_grupo_detalle(rows, unidad, ufv, hoy)
            return _pdf_response(pdf, f'reporte_{num}')
        return render_template('reportes/inv_grupo_detalle.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             rows=rows, unidad=unidad, ufv=ufv, hoy=hoy, fmt=fmt_local)

    elif num == 11:
        data = IndiceUFV.query.order_by(IndiceUFV.fecha.desc()).all()
        if output_format == 'pdf':
            pdf = generar_pdf_ufv(data, unidad, hoy)
            return _pdf_response(pdf, f'reporte_{num}')
        return render_template('reportes/ufv.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             data=data, unidad=unidad, hoy=hoy)

    elif num == 12:
        data = RevaluoTecnico.query.order_by(RevaluoTecnico.fecha.desc()).all()
        return render_template('reportes/revaluos.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             data=data, unidad=unidad, hoy=hoy)

    elif num == 13:
        data = base_query().filter(ActivoFijo.estado == 'APROBADO').order_by(ActivoFijo.codigo).all()
        rows = [calc_depreciacion_activo(a, hoy, gestion) for a in data]
        if output_format == 'pdf':
            pdf = generar_pdf_asignacion(rows, unidad, hoy)
            return _pdf_response(pdf, f'reporte_{num}')
        return render_template('reportes/asignacion.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             rows=rows, unidad=unidad, hoy=hoy, fmt=fmt_local)

    elif num == 14:
        data = BajaActivo.query.filter_by(tipo='ERROR_TRANSCRIPCION').order_by(BajaActivo.fecha.desc()).all()
        return render_template('reportes/bajas_historicas.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             data=data, unidad=unidad, hoy=hoy)

    elif num == 15:
        resumen, total, ufv_val = calc_resumen_grupo(unidad_id, gestion, hoy)
        if output_format == 'pdf':
            pdf = generar_pdf_resumen_grupo(resumen, total, unidad, ufv_val, hoy)
            pdf.report_title = REPORTES[num-1]['nombre']
            return _pdf_response(pdf, f'reporte_{num}')
        return render_template('reportes/resumen_grupo_mov.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             resumen=resumen, total=total, unidad=unidad, ufv=ufv_val, hoy=hoy, fmt=fmt_local)

    elif num == 16:
        filtro_activo = request.args.get('activo_id', '')
        activo = None
        if filtro_activo:
            activo = ActivoFijo.query.get(int(filtro_activo))
        return render_template('reportes/acta_devolucion.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             activo=activo, unidad=unidad, hoy=hoy)

    elif num == 17:
        data = base_query().join(GrupoContable).order_by(
            GrupoContable.codigo, ActivoFijo.organismo_financiador, ActivoFijo.codigo).all()
        rows = [calc_depreciacion_activo(a, hoy, gestion) for a in data]
        if output_format == 'pdf':
            hdrs = ['GRUPO', 'ORGANISMO', 'CODIGO', 'DESCRIPCION', 'COSTO', 'COSTO ACT.',
                    'DEP. GEST.', 'DEP. TOTAL', 'VALOR NETO']
            cw = [22, 22, 16, 40, 18, 18, 16, 18, 18]
            pdf = generar_pdf_activos_simple(rows, unidad, ufv, hoy, REPORTES[num-1]['nombre'],
                                             hdrs, cw)
            return _pdf_response(pdf, f'reporte_{num}')
        return render_template('reportes/inv_grupo_organismo.html', num=num, nombre=REPORTES[num-1]['nombre'],
                             rows=rows, unidad=unidad, ufv=ufv, hoy=hoy, fmt=fmt_local)

    return redirect(url_for('reportes.listar'))

@reportes_bp.route('/exportar_csv/<int:num>')
@login_required
def exportar_csv(num):
    unidad_id = session.get('unidad_actual_id')
    q = ActivoFijo.query
    if unidad_id: q = q.filter_by(unidad_id=unidad_id)
    data = q.order_by(ActivoFijo.codigo).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Código', 'Fecha', 'Descripción', 'Grupo', 'Auxiliar', 'Oficina', 'Responsable', 'Costo Inicial', 'Estado'])
    for a in data:
        writer.writerow([a.codigo, a.fecha_incorporacion, a.descripcion[:50],
                        a.grupo.nombre if a.grupo else '', a.auxiliar.denominacion if a.auxiliar else '',
                        a.oficina_rel.nombre if a.oficina_rel else '', a.responsable_rel.nombre if a.responsable_rel else '',
                        float(a.costo_inicial), a.estado])

    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment;filename=reporte_{num}.csv'})
