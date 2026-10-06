from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import ActivoFijo, Oficina, Responsable, Transferencia, TransferenciaActa, InventarioFisico
from app import db
from datetime import date, datetime

verificacion_bp = Blueprint('verificacion', __name__, url_prefix='/verificacion')

@verificacion_bp.route('/')
@login_required
def listar():
    """Mostrar assets asignados al usuario actual con checkboxes para verificar/transferir"""
    
    # Búsqueda opcional para no cargar todo
    busqueda = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 100
    
    q = ActivoFijo.query
    # Filtrar por usuario si no es admin
    if current_user.rol != 'ADMINISTRADOR':
        q = q.filter_by(responsable_id=current_user.id)
    
    # Búsqueda por código o descripción
    if busqueda:
        q = q.filter(db.or_(
            ActivoFijo.codigo.ilike(f'%{busqueda}%'),
            ActivoFijo.descripcion.ilike(f'%{busqueda}%')
        ))
    
    total = q.count()
    total_pages = (total + per_page - 1) // per_page
    activos = q.order_by(ActivoFijo.codigo).offset((page - 1) * per_page).limit(per_page).all()
    
    # UNA SOLA query para obtener todos los estados de verificación de los activos cargados
    codigos = [a.codigo for a in activos]
    verificados = {}
    if codigos:
        from sqlalchemy import text
        rows = db.session.execute(text("""
            SELECT DISTINCT ON (codigo) codigo, resultado 
            FROM inventario_fisico 
            WHERE codigo = ANY(:codigos)
            ORDER BY codigo, fecha_toma DESC
        """), {'codigos': codigos}).fetchall()
        verificados = {r[0]: (r[1] == 'VERIFICADO') for r in rows}
    
    for activo in activos:
        activo.es_verificado = verificados.get(activo.codigo, False)
    
    return render_template('verificacion/listar.html', 
                         activos=activos, busqueda=busqueda,
                         total=total, page=page, total_pages=total_pages)

@verificacion_bp.route('/transferir', methods=['GET', 'POST'])
@login_required
def transferir():
    """Transferir assets seleccionados a otro responsable con creación de acta"""
    
    if request.method == 'POST':
        activo_ids = request.form.getlist('activo_ids')
        oficina_dest_id = request.form.get('oficina_destino_id', type=int)
        responsable_dest_id = request.form.get('responsable_destino_id', type=int)
        fecha_trans = request.form.get('fecha', str(date.today()))
        
        if not activo_ids:
            flash('Selecciona al menos un activo para transferir', 'danger')
            return redirect(url_for('verificacion.listar'))
        
        if not responsable_dest_id:
            flash('Selecciona un responsable destino', 'danger')
            return redirect(url_for('verificacion.listar'))
        
        # Validar que el responsable destino existe
        responsable_dest = Responsable.query.get(responsable_dest_id)
        if not responsable_dest:
            flash('El responsable destino seleccionado no existe', 'danger')
            return redirect(url_for('verificacion.listar'))
        
        # Convertir fecha de string a date
        fec = datetime.strptime(fecha_trans, '%Y-%m-%d').date()
        
        # Crear acta de transferencia con número correlativo
        gestion = fec.year
        last_acta = db.session.query(func.max(TransferenciaActa.numero)).filter_by(
            gestion=gestion
        ).scalar()
        numero = (last_acta or 0) + 1
        codigo = f'ACTA-{gestion}-{numero:04d}'
        
        # Obtener datos del primer activo (origen)
        primer_activo = ActivoFijo.query.get(int(activo_ids[0]))
        if not primer_activo:
            flash('El activo seleccionado no existe', 'danger')
            return redirect(url_for('verificacion.listar'))
        
        oficina_origen_id = primer_activo.oficina_id
        responsable_origen_id = primer_activo.responsable_id
        
        # Validar que el activo pertenece al usuario (para no ADMINISTRADORES)
        if current_user.rol != 'ADMINISTRADOR' and primer_activo.responsable_id != current_user.id:
            flash('No tienes permiso para transferir este activo', 'danger')
            return redirect(url_for('verificacion.listar'))
        
        # Crear nueva acta
        acta = TransferenciaActa(
            numero=numero,
            gestion=gestion,
            codigo=codigo,
            fecha=fec,
            oficina_origen_id=oficina_origen_id,
            responsable_origen_id=responsable_origen_id,
            oficina_destino_id=oficina_dest_id,
            responsable_destino_id=responsable_dest_id,
            cantidad_activos=len(activo_ids),
            usuario=current_user.username,
            notas='Transferencia iniciada desde módulo de verificación',
            fecha_creacion=datetime.now()
        )
        
        db.session.add(acta)
        db.session.flush()
        
        # Transferir cada activo seleccionado
        transferidos_count = 0
        for activo_id in activo_ids:
            activo = ActivoFijo.query.get(int(activo_id))
            if activo:
                # Validar permisos
                if current_user.rol != 'ADMINISTRADOR' and activo.responsable_id != current_user.id:
                    continue
                
                # Crear registro de transferencia
                t = Transferencia(
                    activo_id=activo.id,
                    fecha=fec,
                    tipo='MISMA_UNIDAD',
                    oficina_origen_id=activo.oficina_id,
                    responsable_origen_id=activo.responsable_id,
                    oficina_destino_id=oficina_dest_id,
                    responsable_destino_id=responsable_dest_id,
                    usuario=current_user.username,
                    acta_id=acta.id,
                    fecha_creacion=datetime.now()
                )
                
                db.session.add(t)
                
                # Actualizar activo
                activo.oficina_id = oficina_dest_id
                activo.responsable_id = responsable_dest_id
                
                transferidos_count += 1
        
        db.session.commit()
        flash(f'{transferidos_count} activo(s) transferido(s) - Acta {codigo}', 'success')
        return redirect(url_for('transferencias.acta_detalle', acta_id=acta.id))
    
    # Manejar GET: Mostrar vista de transferencia con assets seleccionados
    activo_ids = request.args.getlist('activo_ids')
    if not activo_ids:
        flash('No se seleccionaron activos para transferir', 'danger')
        return redirect(url_for('verificacion.listar'))
    
    # Obtener activos seleccionados
    activos = ActivoFijo.query.filter(ActivoFijo.id.in_(activo_ids)).all()
    
    # Obtener oficinas y responsables disponibles para transferencia
    dest_oficinas = Oficina.query.filter_by(estado='ACTIVO').order_by(Oficina.nombre).all()
    dest_responsables = Responsable.query.order_by(Responsable.nombre).all()
    
    return render_template('verificacion/transferir.html', 
                         activos=activos,
                         dest_oficinas=dest_oficinas,
                         dest_responsables=dest_responsables,
                         hoy=date.today())

@verificacion_bp.route('/marcar_verificados', methods=['POST'])
@login_required
def marcar_verificados():
    """Marcar assets seleccionados como verificados en inventario"""
    
    data = request.get_json(force=True) if request.is_json else None
    if not data:
        return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
    
    activo_ids = data.get('activo_ids', [])
    if not activo_ids:
        return jsonify({'success': False, 'message': 'No se seleccionaron activos'}), 400
    
    # Obtener los activos
    activos = ActivoFijo.query.filter(ActivoFijo.id.in_(activo_ids)).all()
    
    # Validar que pertenecen al usuario actual (a menos que sea ADMINISTRADOR)
    if current_user.rol != 'ADMINISTRADOR':
        activos = [a for a in activos if a.responsable_id == current_user.id]
    
    if not activos:
        return jsonify({'success': False, 'message': 'No se encontraron activos válidos'}), 403
    
    # Crear registros en inventario_fisico marcando como VERIFICADO
    for activo in activos:
        inventario = InventarioFisico(
            activo_id=activo.id,
            codigo=activo.codigo,
            resultado='VERIFICADO',
            observacion='Verificado desde módulo de verificación',
            ubicacion_reportada=activo.oficina_rel.nombre if activo.oficina_rel else '',
            responsable_reportado=activo.responsable_rel.nombre if activo.responsable_rel else '',
            foto_url=None,
            usuario=current_user.username,
            dispositivo='web',
            fecha_toma=datetime.now(),
            fecha_sincronizacion=datetime.now()
        )
        
        db.session.add(inventario)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'{len(activos)} activo(s) marcados como verificados',
        'redirect': url_for('verificacion.listar')
    })