"""DBF Export Module for SCAFMH transfers."""
import os, shutil, datetime
import dbf
from app.models import ActivoFijo, Oficina, Responsable, Transferencia, UnidadAdministrativa, GrupoContable, AuxiliarContable
from app import db

DBF_DIR = r'D:\sistema de af\dbfs'
OUTPUT_DIR = r'D:\sistema de af\dbfs_export'

def _build_cache():
    """Preload all lookup tables into memory (avoids 23k+ individual SQL queries)."""
    oficinas = {o.id: o.codofic for o in Oficina.query.all()}
    responsables = {r.id: r.codresp for r in Responsable.query.all()}
    activos = {}
    for a in ActivoFijo.query.all():
        activos[a.codigo] = a
    grupos = {g.id: int(g.codigo) if g and g.codigo else 0 for g in GrupoContable.query.all()}
    auxiliares = {a.id: a.id for a in AuxiliarContable.query.all()}
    unidades = {u.id: u.codigo for u in UnidadAdministrativa.query.all()}
    return oficinas, responsables, activos, grupos, auxiliares, unidades

def _codofic(oficina_id, cache):
    return cache.get(oficina_id, 0)

def _codresp(responsable_id, cache):
    return cache.get(responsable_id, 0)

def export_actual_dbf(cache):
    """Generate updated ACTUAL.DBF with current office/responsable from SQLite."""
    src = os.path.join(DBF_DIR, 'ACTUAL.DBF')
    fpt_src = os.path.join(DBF_DIR, 'ACTUAL.FPT')
    cdx_src = os.path.join(DBF_DIR, 'ACTUAL.CDX')
    if not os.path.exists(src):
        raise FileNotFoundError('ACTUAL.DBF not found')

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    dst = os.path.join(OUTPUT_DIR, 'ACTUAL.DBF')
    fpt_dst = os.path.join(OUTPUT_DIR, 'ACTUAL.FPT')
    cdx_dst = os.path.join(OUTPUT_DIR, 'ACTUAL.CDX')

    shutil.copy2(src, dst)
    if os.path.exists(fpt_src):
        shutil.copy2(fpt_src, fpt_dst)
    if os.path.exists(cdx_src):
        shutil.copy2(cdx_src, cdx_dst)

    ofi_cache, resp_cache, activos_cache = cache[0], cache[1], cache[2]

    table = dbf.Table(dst, codepage='cp1252')
    table.open(dbf.READ_WRITE)
    today = datetime.date.today()
    updated = 0
    for record in table:
        codigo = str(record.CODIGO).strip() if record.CODIGO is not None else ''
        if not codigo:
            continue
        activo = activos_cache.get(codigo)
        if not activo:
            continue
        with record as r:
            r.CODOFIC = _codofic(activo.oficina_id, ofi_cache)
            r.CODRESP = _codresp(activo.responsable_id, resp_cache)
            r.FEULT = today
            r.USUAR = 'admin'
        updated += 1
    table.close()
    return dst

def export_trasfe_dbf(cache):
    """Generate TRASFE.DBF adding all transfer records from SQLite."""
    src = os.path.join(DBF_DIR, 'trasfe.dbf')
    if not os.path.exists(src):
        raise FileNotFoundError('trasfe.dbf not found')

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    dst = os.path.join(OUTPUT_DIR, 'trasfe.dbf')
    shutil.copy2(src, dst)

    transfers = Transferencia.query.order_by(Transferencia.id).all()
    today = datetime.date.today()

    ofi_cache, resp_cache, activos_cache, _, _, unidades_cache = cache
    activos_full = {a.id: a for a in ActivoFijo.query.all()}

    table = dbf.Table(dst, codepage='cp1252')
    table.open(dbf.READ_WRITE)
    existing_count = len(table)
    added = 0
    for t in transfers:
        activo = activos_full.get(t.activo_id)
        if not activo:
            continue
        uni = unidades_cache.get(activo.unidad_id, '')

        dest_ofic = _codofic(t.oficina_destino_id or activo.oficina_id, ofi_cache)
        dest_resp = _codresp(t.responsable_destino_id or activo.responsable_id, resp_cache)
        fec = t.fecha if t.fecha else today

        table.append({
            'ENTIDAD': '670',
            'UNIDAD': uni,
            'CODIGO': str(activo.codigo),
            'CODOFIC': dest_ofic,
            'CODRESP': dest_resp,
            'FEULT': fec,
            'USUAR': str(t.usuario or 'admin'),
            'UNIDADINI': uni,
        })
        added += 1
    table.close()
    return dst

def export_all():
    """Export all DBF files for SCAFMH sync."""
    cache = _build_cache()
    actual = export_actual_dbf(cache)
    trasfe = export_trasfe_dbf(cache)
    return {
        'actual_dbf': actual,
        'trasfe_dbf': trasfe,
        'output_dir': OUTPUT_DIR,
    }
