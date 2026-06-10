"""Processing log for depreciation/UFV reversions.
Supports a stack of processing steps per gestion."""
import json, os, datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'procesos')
os.makedirs(LOG_DIR, exist_ok=True)

def _log_path(gestion):
    return os.path.join(LOG_DIR, f'proceso_{gestion}.json')

def guardar_log(gestion, tipo, data):
    """Append a processing step to the log stack."""
    path = _log_path(gestion)
    log = leer_log(gestion)
    if log is None:
        log = {'gestion': gestion, 'procesos': []}
    log['procesos'].append({
        'tipo': tipo,
        'fecha': datetime.datetime.now().isoformat(),
        'data': data,
    })
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    return path

def leer_log(gestion):
    """Read the full log for a gestion, or None."""
    path = _log_path(gestion)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def pop_ultimo_proceso(gestion):
    """Pop and return the last (tipo, data) from the log stack, or (None, None)."""
    log = leer_log(gestion)
    if not log or not log.get('procesos'):
        return None, None
    entry = log['procesos'].pop()
    if log['procesos']:
        with open(_log_path(gestion), 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    else:
        os.remove(_log_path(gestion))
    return entry['tipo'], entry['data']
