"""Generate acta PDF for visual comparison."""
import sys; sys.path.insert(0, 'D:\\sistema de af\\sistema_activos')
from app import create_app, db
from app.models import Responsable, Oficina, ActivoFijo, UnidadAdministrativa, AuxiliarContable
from app.pdf_reportes import generar_pdf_acta_transferencia
from datetime import date
app = create_app()
with app.app_context():
    resp = db.session.get(Responsable, 236)
    ofi = db.session.get(Oficina, resp.oficina_id) if resp else None
    uni = db.session.get(UnidadAdministrativa, ofi.unidad_id) if ofi else None
    activos_raw = ActivoFijo.query.filter_by(responsable_id=236).limit(23).all()
    activos = []
    for a in activos_raw:
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
    oficina_data = {'codofic': str(ofi.codofic) if ofi else '', 'nombre': ofi.nombre if ofi else ''}
    pdf = generar_pdf_acta_transferencia(responsable_data, oficina_data, activos, date(2026, 4, 15))
    pdf.output('D:\\sistema de af\\sistema_activos\\test_acta.pdf')
    print('PDF generated with 23 assets')
