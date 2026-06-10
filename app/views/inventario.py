from flask import Blueprint, render_template, request, jsonify, current_app, url_for, redirect, flash
from flask_login import login_required, current_user
from app import db
from app.models import ActivoFijo, InventarioFisico, Oficina, Responsable, ROL_ADMIN, ROL_INVENTARIADOR
from datetime import datetime
from functools import wraps
import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
import json

inventario_bp = Blueprint('inventario', __name__, url_prefix='/inventario')

ROLES_INVENTARIO = [ROL_ADMIN, ROL_INVENTARIADOR]


def inventario_permitido(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith('/inventario/api/'):
                return jsonify({'error': 'autenticacion requerida'}), 401
            return redirect(url_for('main.login'))
        if current_user.rol not in ROLES_INVENTARIO:
            if request.path.startswith('/inventario/api/'):
                return jsonify({'error': 'rol no autorizado'}), 403
            flash('No tienes permisos para acceder a Toma Física', 'danger')
            return redirect(url_for('main.inicio'))
        return f(*args, **kwargs)
    return wrapper


@inventario_bp.route('/')
@inventario_permitido
def lista():
    return render_template('inventario/lista.html')


@inventario_bp.route('/escanear')
@inventario_permitido
def escanear():
    return render_template('inventario/escanear.html')


@inventario_bp.route('/resultados')
@inventario_permitido
def resultados():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    resultados = InventarioFisico.query.order_by(InventarioFisico.fecha_sincronizacion.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('inventario/resultados.html', resultados=resultados)


# ─── API ────────────────────────────────────────────────────────────────

@inventario_bp.route('/api/activos')
@inventario_permitido
def api_activos():
    page = request.args.get('page', 1, type=int)
    per_page = 500
    search = request.args.get('search', '').strip()
    q = ActivoFijo.query.filter(ActivoFijo.estado != 'BAJA')
    if search:
        q = q.filter(ActivoFijo.codigo.contains(search) | ActivoFijo.descripcion.contains(search))
    total = q.count()
    activos = q.order_by(ActivoFijo.codigo).paginate(page=page, per_page=per_page, error_out=False)
    items = []
    for a in activos.items:
        items.append(_serializar_activo(a))
    return jsonify({
        'items': items,
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page,
        'per_page': per_page,
    })


@inventario_bp.route('/api/activos/<codigo>')
@inventario_permitido
def api_activo_detail(codigo):
    a = ActivoFijo.query.filter(ActivoFijo.codigo == codigo).first()
    if not a:
        a = ActivoFijo.query.filter(ActivoFijo.codigo_barras == codigo).first()
    if not a:
        return jsonify({'error': 'Activo no encontrado'}), 404
    return jsonify(_serializar_activo(a))


def _serializar_activo(a):
    return {
        'id': a.id,
        'codigo': a.codigo,
        'codigo_barras': a.codigo_barras or '',
        'descripcion': a.descripcion,
        'fecha_incorporacion': a.fecha_incorporacion.isoformat() if a.fecha_incorporacion else None,
        'grupo': a.grupo.nombre if a.grupo else '',
        'auxiliar': a.auxiliar.denominacion if a.auxiliar else '',
        'costo_inicial': float(a.costo_inicial or 0),
        'depreciacion_acumulada': float(a.depreciacion_acumulada or 0),
        'estado_bien': a.estado_bien or '',
        'oficina_id': a.oficina_id,
        'oficina': a.oficina_rel.nombre if a.oficina_rel else '',
        'responsable_id': a.responsable_id,
        'responsable': a.responsable_rel.nombre if a.responsable_rel else '',
        'responsable_cargo': a.responsable_rel.cargo if a.responsable_rel else '',
        'responsable_ci': a.responsable_rel.carnet_identidad if a.responsable_rel else '',
        'vida_util': a.vida_util or 0,
        'observaciones': a.observaciones or '',
    }


@inventario_bp.route('/api/oficinas')
@inventario_permitido
def api_oficinas():
    oficinas = Oficina.query.filter(Oficina.estado == 'ACTIVO').order_by(Oficina.nombre).all()
    return jsonify([{
        'id': o.id,
        'codofic': o.codofic,
        'nombre': o.nombre,
        'unidad': o.unidad.descripcion if o.unidad else '',
    } for o in oficinas])


@inventario_bp.route('/api/responsables')
@inventario_permitido
def api_responsables():
    oficina_id = request.args.get('oficina_id', type=int)
    q = Responsable.query.filter(Responsable.estado == 'ACTIVO')
    if oficina_id:
        q = q.filter(Responsable.oficina_id == oficina_id)
    responsables = q.order_by(Responsable.nombre).all()
    return jsonify([{
        'id': r.id,
        'codresp': r.codresp,
        'nombre': r.nombre,
        'cargo': r.cargo or '',
        'carnet_identidad': r.carnet_identidad or '',
        'oficina_id': r.oficina_id,
    } for r in responsables])


@inventario_bp.route('/api/activos/<int:activo_id>/registrar-barras', methods=['POST'])
@inventario_permitido
def api_registrar_barras(activo_id):
    data = request.get_json(force=True)
    codigo_barras = data.get('codigo_barras', '').strip()
    if not codigo_barras:
        return jsonify({'error': 'código de barras requerido'}), 400
    existe = ActivoFijo.query.filter(ActivoFijo.codigo_barras == codigo_barras).first()
    if existe:
        return jsonify({'error': 'Ese código de barras ya está asignado a otro activo', 'activo': existe.codigo}), 409
    a = db.session.get(ActivoFijo, activo_id)
    if not a:
        return jsonify({'error': 'Activo no encontrado'}), 404
    a.codigo_barras = codigo_barras
    db.session.commit()
    return jsonify({'ok': True, 'codigo': a.codigo, 'codigo_barras': codigo_barras})


@inventario_bp.route('/api/resultados', methods=['POST'])
@inventario_permitido
def api_subir_resultados():
    data = request.get_json(force=True)
    if not data or not isinstance(data, list):
        return jsonify({'error': 'Se espera un array de resultados'}), 400

    created = 0
    errors = []
    for item in data:
        codigo = item.get('codigo', '').strip()
        if not codigo:
            errors.append({'codigo': codigo, 'error': 'código vacío'})
            continue
        activo = ActivoFijo.query.filter_by(codigo=codigo).first()
        if not activo:
            errors.append({'codigo': codigo, 'error': 'activo no encontrado en BD'})
            continue
        try:
            nueva_oficina_id = item.get('nueva_oficina_id')
            nuevo_responsable_id = item.get('nuevo_responsable_id')
            # Validar que los IDs existan si se enviaron
            if nueva_oficina_id and not db.session.get(Oficina, nueva_oficina_id):
                nueva_oficina_id = None
            if nuevo_responsable_id and not db.session.get(Responsable, nuevo_responsable_id):
                nuevo_responsable_id = None

            rec = InventarioFisico(
                activo_id=activo.id,
                codigo=codigo,
                resultado=item.get('resultado', 'VERIFICADO'),
                observacion=item.get('observacion', ''),
                foto_url=item.get('foto_url', ''),
                ubicacion_reportada=item.get('ubicacion', ''),
                responsable_reportado=item.get('responsable', ''),
                nueva_oficina_id=nueva_oficina_id,
                nuevo_responsable_id=nuevo_responsable_id,
                latitud=item.get('lat'),
                longitud=item.get('lng'),
                usuario=current_user.username,
                dispositivo=item.get('dispositivo', ''),
                fecha_sincronizacion=datetime.now(),
                fecha_toma=datetime.fromisoformat(item['fecha_toma']) if item.get('fecha_toma') else datetime.now(),
            )
            db.session.add(rec)
            created += 1
        except Exception as e:
            errors.append({'codigo': codigo, 'error': str(e)})

    db.session.commit()
    return jsonify({'created': created, 'errors': errors})


@inventario_bp.route('/api/resultados', methods=['GET'])
@inventario_permitido
def api_resultados():
    page = request.args.get('page', 1, type=int)
    per_page = 100
    q = InventarioFisico.query.order_by(InventarioFisico.fecha_sincronizacion.desc())
    total = q.count()
    items = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'items': [{
            'id': r.id,
            'codigo': r.codigo,
            'resultado': r.resultado,
            'observacion': r.observacion,
            'foto_url': r.foto_url,
            'ubicacion': r.ubicacion_reportada,
            'responsable': r.responsable_reportado,
            'oficina_nueva': r.oficina_nueva.nombre if r.oficina_nueva else '',
            'responsable_nuevo': r.responsable_nuevo.nombre if r.responsable_nuevo else '',
            'fecha': r.fecha_sincronizacion.isoformat() if r.fecha_sincronizacion else '',
        } for r in items.items],
        'total': total,
        'page': page,
    })


@inventario_bp.route('/api/foto', methods=['POST'])
@inventario_permitido
def api_subir_foto():
    if 'foto' not in request.files:
        return jsonify({'error': 'No se envió archivo'}), 400
    file = request.files['foto']
    if not file.filename:
        return jsonify({'error': 'Archivo vacío'}), 400

    try:
        cfg = current_app.config
        cloudinary.config(
            cloud_name=cfg.get('CLOUDINARY_CLOUD_NAME'),
            api_key=cfg.get('CLOUDINARY_API_KEY'),
            api_secret=cfg.get('CLOUDINARY_API_SECRET'),
        )
        result = cloudinary.uploader.upload(
            file,
            folder='activos_fotos',
            public_id=f"inventario_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
        )
        return jsonify({'url': result['secure_url'], 'public_id': result['public_id']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@inventario_bp.route('/api/estadisticas')
@inventario_permitido
def api_estadisticas():
    total = ActivoFijo.query.filter(ActivoFijo.estado != 'BAJA').count()
    verificados = InventarioFisico.query.filter_by(resultado='VERIFICADO').count()
    con_novedad = InventarioFisico.query.filter_by(resultado='NOVEDAD').count()
    no_encontrados = InventarioFisico.query.filter_by(resultado='NO_ENCONTRADO').count()
    total_escaneados = verificados + con_novedad + no_encontrados
    return jsonify({
        'total_activos': total,
        'total_escaneados': total_escaneados,
        'verificados': verificados,
        'con_novedad': con_novedad,
        'no_encontrados': no_encontrados,
        'pendientes': total - total_escaneados,
        'avance': round(total_escaneados / total * 100, 1) if total else 0,
    })


@inventario_bp.route('/api/cloudinary-config')
@inventario_permitido
def api_cloudinary_config():
    cfg = current_app.config
    return jsonify({
        'cloud_name': cfg.get('CLOUDINARY_CLOUD_NAME', ''),
        'upload_preset': cfg.get('CLOUDINARY_UPLOAD_PRESET', 'activos_fotos'),
    })
