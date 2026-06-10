"""
SCAFMH Depreciation Calculation Module
Matches the original FoxPro business logic for:
- Straight-line depreciation
- UFV indexation (actualización)
- Revaluation support
"""
from datetime import date, datetime
from app.models import ActivoFijo, GrupoContable, IndiceUFV
from app import db

_ufv_cache = {}

def _load_ufv_cache(force=False):
    """Load all UFV values into memory cache."""
    if _ufv_cache and not force:
        return
    if force:
        _ufv_cache.clear()
    for r in IndiceUFV.query.all():
        _ufv_cache[r.fecha] = float(r.valor)

def get_ufv(fecha):
    """Get UFV value for a given date (exact or nearest previous)."""
    if not fecha:
        return None
    _load_ufv_cache()
    # Exact match
    val = _ufv_cache.get(fecha)
    if val is not None:
        return val
    # Nearest previous
    for f in sorted(_ufv_cache.keys(), reverse=True):
        if f <= fecha:
            return _ufv_cache[f]
    return None

def get_ufv_today():
    """Get latest available UFV value."""
    _load_ufv_cache()
    if _ufv_cache:
        max_date = max(_ufv_cache.keys())
        return _ufv_cache[max_date]
    return 1.0

def calc_factor_ufv(fecha_incorporacion, fecha_hasta=None):
    """Calculate UFV adjustment factor: UFV_hoy / UFV_incorporacion"""
    if not fecha_hasta:
        fecha_hasta = date.today()
    ufv_orig = get_ufv(fecha_incorporacion)
    ufv_now = get_ufv(fecha_hasta)
    if ufv_orig and ufv_now and ufv_orig > 0:
        return ufv_now / ufv_orig
    # If no UFV data for original date, try using earliest available UFV
    _load_ufv_cache()
    if _ufv_cache and ufv_now:
        earliest_val = min(_ufv_cache.values())
        return ufv_now / earliest_val
    return 1.0

def calc_depreciacion_activo(activo, fecha_hasta=None, gestion=2026):
    """
    Calculate full depreciation for a single asset.
    Returns dict with all calculated fields matching SCAFMH report format.
    """
    if not fecha_hasta:
        fecha_hasta = date.today()

    grupo = activo.grupo
    # Use asset-level vida_util if available, otherwise from group
    vida_util = activo.vida_util or (grupo.vida_util if grupo else 0)
    if vida_util <= 0:
        vida_util = 1  # avoid division by zero

    costo = float(activo.costo_inicial) if activo.costo_inicial else 0
    dep_acum_inicial = float(activo.depreciacion_acumulada) if activo.depreciacion_acumulada else 0
    revaluado = activo.revaluado or False
    band_ufv = activo.band_ufv or False
    debe_depreciar = grupo.depreciar if grupo else True
    debe_actualizar = grupo.actualizar if grupo else True

    fec_inc = activo.fecha_incorporacion
    fec_ult_act = activo.fecha_ultima_actualizacion or fec_inc

    # UFV adjustment factor
    # Apply UFV if the group's actualizar flag is True and asset has incorporation date
    factor_ufv = 1.0
    if debe_actualizar and fec_inc:
        factor_ufv = calc_factor_ufv(fec_inc, fecha_hasta)
        if factor_ufv is None or factor_ufv <= 0:
            factor_ufv = 1.0

    # Actualized cost
    costo_actual_inicial = costo * factor_ufv

    # Depreciation percentage (annual rate)
    porc_depr = 100.0 / vida_util if vida_util > 0 else 0

    # Adjust accumulated depreciation by UFV
    dep_acum_ajustada = dep_acum_inicial * factor_ufv if debe_actualizar else dep_acum_inicial

    # Days in current year for this asset
    inicio_gestion = date(gestion, 1, 1)
    fin_gestion = date(gestion, 12, 31)

    if fec_inc and fec_inc > inicio_gestion:
        inicio_dep = fec_inc
    else:
        inicio_dep = inicio_gestion

    if fecha_hasta < fin_gestion:
        fin_dep = fecha_hasta
    else:
        fin_dep = fin_gestion

    dias_gestion = (fin_dep - inicio_dep).days
    if dias_gestion < 0:
        dias_gestion = 0

    # Annual depreciation (in actualized terms)
    dep_anual = costo_actual_inicial / vida_util if debe_depreciar else 0

    # Depreciation for current period (proportional to days)
    dep_gestion = dep_anual * (dias_gestion / 365.0) if dias_gestion > 0 else 0

    # Total accumulated depreciation
    dep_acum_total = dep_acum_ajustada + dep_gestion
    if dep_acum_total > costo_actual_inicial:
        dep_acum_total = costo_actual_inicial

    # Net value
    valor_neto = costo_actual_inicial - dep_acum_total

    # UFV adjustment amount for the year
    actualizacion_gestion = (costo * factor_ufv) - costo if debe_actualizar else 0

    return {
        'codigo': activo.codigo,
        'descripcion': activo.descripcion,
        'fecha_incorporacion': fec_inc,
        'costo': costo,
        'costo_actual_inicial': costo_actual_inicial,
        'dep_acum_inicial': dep_acum_inicial,
        'dep_acum_ajustada': dep_acum_ajustada,
        'residual': 0,
        'factor_ufv': factor_ufv,
        'porc_depr': porc_depr,
        'dias': dias_gestion,
        'dep_anual': dep_anual,
        'dep_gestion': dep_gestion,
        'dep_acum_total': dep_acum_total,
        'valor_neto': valor_neto,
        'vida_util': vida_util,
        'actualizacion_gestion': actualizacion_gestion,
        'revaluado': revaluado,
        'band_ufv': band_ufv,
        'grupo_nombre': grupo.nombre if grupo else '',
        'auxiliar_denom': activo.auxiliar.denominacion if activo.auxiliar else '',
        'oficina_nombre': activo.oficina_rel.nombre if activo.oficina_rel else '',
        'responsable_nombre': activo.responsable_rel.nombre if activo.responsable_rel else '',
        'estado_bien': activo.estado_bien or '',
        'ufv_actual': factor_ufv,  # really UFV value, not factor
        'organismo': activo.organismo_financiador or '',
    }

def calc_resumen_grupo(unidad_id=None, gestion=2026, fecha_hasta=None):
    """Calculate summary by group (matches Resumen por Grupo report)."""
    if not fecha_hasta:
        fecha_hasta = date.today()

    query = ActivoFijo.query
    if unidad_id:
        query = query.filter_by(unidad_id=unidad_id)
    activos = query.join(GrupoContable).order_by(GrupoContable.codigo, ActivoFijo.codigo).all()

    from collections import OrderedDict
    resumen = OrderedDict()
    ufv = get_ufv_today()

    for a in activos:
        grupo = a.grupo
        gn = grupo.nombre if grupo else 'SIN GRUPO'
        if gn not in resumen:
            resumen[gn] = {
                'grupo': gn,
                'vida_util': grupo.vida_util if grupo else 0,
                'cantidad': 0,
                'costo_historico': 0,
                'costo_actual_inicial': 0,
                'dep_acum_inicial': 0,
                'valor_neto_inicial': 0,
                'actualizacion_gestion': 0,
                'costo_total_actual': 0,
                'dep_gestion': 0,
                'actualizacion_dep': 0,
                'dep_acum_total': 0,
                'valor_neto': 0,
            }

        r = calc_depreciacion_activo(a, fecha_hasta, gestion)
        g = resumen[gn]
        g['cantidad'] += 1
        g['costo_historico'] += r['costo']
        g['costo_actual_inicial'] += r['costo_actual_inicial']
        g['dep_acum_inicial'] += r['dep_acum_inicial']
        g['valor_neto_inicial'] += r['costo_actual_inicial'] - r['dep_acum_ajustada']
        g['actualizacion_gestion'] += r['actualizacion_gestion']
        g['costo_total_actual'] += r['costo_actual_inicial']
        g['dep_gestion'] += r['dep_gestion']
        g['dep_acum_total'] += r['dep_acum_total']
        g['valor_neto'] += r['valor_neto']

    # Calculate total row
    total = {
        'grupo': 'TOTALES:',
        'vida_util': 0,
        'cantidad': sum(v['cantidad'] for v in resumen.values()),
        'costo_historico': sum(v['costo_historico'] for v in resumen.values()),
        'costo_actual_inicial': sum(v['costo_actual_inicial'] for v in resumen.values()),
        'dep_acum_inicial': sum(v['dep_acum_inicial'] for v in resumen.values()),
        'valor_neto_inicial': sum(v['valor_neto_inicial'] for v in resumen.values()),
        'actualizacion_gestion': sum(v['actualizacion_gestion'] for v in resumen.values()),
        'costo_total_actual': sum(v['costo_total_actual'] for v in resumen.values()),
        'dep_gestion': sum(v['dep_gestion'] for v in resumen.values()),
        'dep_acum_total': sum(v['dep_acum_total'] for v in resumen.values()),
        'valor_neto': sum(v['valor_neto'] for v in resumen.values()),
    }

    return resumen, total, ufv


def procesar_actualizacion_ufv(gestion):
    """Process UFV actualization for all assets in a gestion year.
    Backs up current values and updates fecha_ultima_actualizacion.
    Uses grupo.actualizar flag (matching report logic)."""
    from datetime import date
    from app.procesos_log import guardar_log
    fin_gestion = date(gestion, 12, 31)
    activos = ActivoFijo.query.filter(ActivoFijo.estado != 'BAJA').all()
    count = 0
    errors = []
    backup = []
    for a in activos:
        grupo = a.grupo
        if not grupo or not grupo.actualizar:
            continue
        if not a.fecha_incorporacion:
            continue
        try:
            backup.append({
                'id': a.id, 'codigo': a.codigo,
                'costo_anterior': float(a.costo_inicial or 0),
                'vida_util_anterior': a.vida_util,
                'fecha_anterior': a.fecha_ultima_actualizacion.isoformat() if a.fecha_ultima_actualizacion else None,
            })
            a.costo_anterior = a.costo_inicial
            a.vida_util_anterior = a.vida_util
            a.fecha_anterior = a.fecha_ultima_actualizacion
            a.fecha_ultima_actualizacion = fin_gestion
            count += 1
        except Exception as e:
            errors.append(f'{a.codigo}: {e}')
    db.session.commit()
    guardar_log(gestion, 'actualizacion_ufv', backup)
    return {'actualizados': count, 'errors': errors}


def procesar_depreciacion(gestion):
    """Process depreciation for all assets in a gestion year.
    Calculates and persists depreciation, tracking previous values for reversion."""
    from datetime import date
    from app.procesos_log import guardar_log
    fin_gestion = date(gestion, 12, 31)
    activos = ActivoFijo.query.filter(ActivoFijo.estado != 'BAJA').all()
    count = 0
    errors = []
    total_dep = 0
    backup = []
    for a in activos:
        grupo = a.grupo
        if not grupo or not grupo.depreciar:
            continue
        if not a.fecha_incorporacion:
            continue
        try:
            r = calc_depreciacion_activo(a, fin_gestion, gestion)
            dep_gestion = r['dep_gestion']
            if dep_gestion > 0:
                backup.append({
                    'id': a.id, 'codigo': a.codigo,
                    'dep_acum_anterior': float(a.depreciacion_acumulada or 0),
                    'dep_gestion': dep_gestion,
                })
                a.depreciacion_acumulada = float(a.depreciacion_acumulada or 0) + dep_gestion
                a.fecha_ultima_actualizacion = fin_gestion
                total_dep += dep_gestion
                count += 1
        except Exception as e:
            errors.append(f'{a.codigo}: {e}')
    db.session.commit()
    guardar_log(gestion, 'depreciacion', backup)
    return {'procesados': count, 'total_depreciacion': total_dep, 'errors': errors}


def revertir_procesamiento(gestion):
    """Revert LAST processing step by reading the log and restoring values."""
    from app.procesos_log import pop_ultimo_proceso
    from datetime import datetime as dt
    tipo, data = pop_ultimo_proceso(gestion)
    if tipo is None:
        return {'revertidos': 0, 'errors': ['No hay registro de procesamiento para revertir']}

    count = 0
    errors = []

    for item in data:
        a = db.session.get(ActivoFijo, item['id'])
        if not a:
            continue
        try:
            if tipo == 'actualizacion_ufv':
                a.costo_inicial = item['costo_anterior']
                a.vida_util = item['vida_util_anterior'] or a.vida_util
                fec_str = item.get('fecha_anterior')
                a.fecha_ultima_actualizacion = dt.strptime(fec_str, '%Y-%m-%d').date() if fec_str else None
                a.costo_anterior = None
                a.vida_util_anterior = None
                a.fecha_anterior = None
                count += 1
            elif tipo == 'depreciacion':
                a.depreciacion_acumulada = item['dep_acum_anterior']
                count += 1
        except Exception as e:
            errors.append(f'{item.get("codigo","?")}: {e}')

    db.session.commit()
    return {'revertidos': count, 'errors': errors, 'tipo_revertido': tipo}
