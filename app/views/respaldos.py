from flask import Blueprint, render_template, redirect, url_for, request, session
from flask_login import login_required, current_user
from app import db
from app.models import ActivoFijo, GrupoContable, AuxiliarContable, Oficina, Responsable, UnidadAdministrativa, Gestion, IndiceUFV, RevaluoTecnico, BajaActivo, Transferencia
from datetime import datetime
import json, os

respaldos_bp = Blueprint('respaldos', __name__)
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups')

def get_backup_list():
    if not os.path.exists(BACKUP_DIR):
        return []
    backups = []
    for f in os.listdir(BACKUP_DIR):
        if f.endswith('.json'):
            fpath = os.path.join(BACKUP_DIR, f)
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            size = os.path.getsize(fpath)
            backups.append({'nombre': f, 'fecha': mtime, 'tamano': size})
    backups.sort(key=lambda x: x['fecha'], reverse=True)
    return backups

def export_full_data():
    data = {
        'fecha': datetime.now().isoformat(),
        'unidades': [{'codigo': u.codigo, 'ciudad': u.ciudad, 'descripcion': u.descripcion} for u in UnidadAdministrativa.query.all()],
        'grupos': [{'codigo': g.codigo, 'nombre': g.nombre, 'auxiliares': [{'denominacion': a.denominacion} for a in g.auxiliares]} for g in GrupoContable.query.all()],
        'gestiones': [{'anio': g.anio, 'cerrada': g.cerrada} for g in Gestion.query.all()],
    }
    return data

@respaldos_bp.route('/')
@login_required
def listar():
    backups = get_backup_list()
    return render_template('respaldos/listar.html', backups=backups)

@respaldos_bp.route('/respaldar')
@login_required
def respaldar():
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('respaldos.listar'))
    data = export_full_data()
    filename = f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    filepath = os.path.join(BACKUP_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return redirect(url_for('respaldos.listar'))

@respaldos_bp.route('/restaurar/<nombre>')
@login_required
def restaurar(nombre):
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('respaldos.listar'))
    filepath = os.path.join(BACKUP_DIR, nombre)
    if not os.path.exists(filepath):
        return redirect(url_for('respaldos.listar'))
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return redirect(url_for('respaldos.listar'))

@respaldos_bp.route('/borrar/<nombre>')
@login_required
def borrar(nombre):
    if current_user.rol != 'ADMINISTRADOR':
        return redirect(url_for('respaldos.listar'))
    filepath = os.path.join(BACKUP_DIR, nombre)
    if os.path.exists(filepath):
        os.remove(filepath)
    return redirect(url_for('respaldos.listar'))
