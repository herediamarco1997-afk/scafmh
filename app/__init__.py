from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import SQLALCHEMY_DATABASE_URI, SECRET_KEY

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config')

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    login_manager.login_view = 'main.login'

    from app.models import Usuario
    from app.views.main import main_bp
    from app.views.unidades import unidades_bp
    from app.views.oficinas import oficinas_bp
    from app.views.grupos import grupos_bp
    from app.views.activos import activos_bp
    from app.views.administracion import administracion_bp
    from app.views.reportes import reportes_bp
    from app.views.respaldos import respaldos_bp
    from app.views.transferencias import transferencias_bp
    from app.views.inventario import inventario_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(unidades_bp, url_prefix='/unidades')
    app.register_blueprint(oficinas_bp, url_prefix='/oficinas')
    app.register_blueprint(grupos_bp, url_prefix='/grupos')
    app.register_blueprint(activos_bp, url_prefix='/activos')
    app.register_blueprint(administracion_bp, url_prefix='/admin')
    app.register_blueprint(reportes_bp, url_prefix='/reportes')
    app.register_blueprint(respaldos_bp, url_prefix='/respaldos')
    app.register_blueprint(transferencias_bp)
    app.register_blueprint(inventario_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    @app.context_processor
    def inject_unidades():
        try:
            from app.models import UnidadAdministrativa
            return {'unidades': UnidadAdministrativa.query.all()}
        except Exception:
            return {'unidades': []}

    @app.errorhandler(500)
    def internal_error(e):
        from flask import render_template_string
        return render_template_string('''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SCAFMH - Cargando...</title><style>body{font-family:Segoe UI,Arial,sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f0f2f5;text-align:center;padding:20px}
.box{background:white;padding:40px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);max-width:400px}
h1{color:#1a3a5c;font-size:20px}p{color:#666;font-size:14px}</style></head>
<body><div class="box"><h1>SCAFMH</h1><p>El servidor se está iniciando (cold start).<br><br>Esto tarda ~30 segundos la primera vez.<br><br><strong>Recargá la página en unos segundos.</strong></p><br><a href="/" style="color:#2c5f8a;font-weight:bold">Recargar</a></div></body></html>'''), 500

    @app.errorhandler(502)
    def bad_gateway(e):
        from flask import render_template_string
        return render_template_string('''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SCAFMH - Cargando...</title><style>body{font-family:Segoe UI,Arial,sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f0f2f5;text-align:center;padding:20px}
.box{background:white;padding:40px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);max-width:400px}
h1{color:#1a3a5c;font-size:20px}p{color:#666;font-size:14px}</style></head>
<body><div class="box"><h1>SCAFMH</h1><p>El servidor se está reiniciando.<br><br>Esperá 30 segundos y recargá.</p><br><a href="/" style="color:#2c5f8a;font-weight:bold">Recargar</a></div></body></html>'''), 502

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"DB create_all warning: {e}")

        try:
            if not Usuario.query.filter_by(username='admin').first():
                from werkzeug.security import generate_password_hash
                admin = Usuario(username='admin', password=generate_password_hash('admin'), rol='ADMINISTRADOR')
                db.session.add(admin)
                db.session.commit()
        except Exception:
            pass

        try:
            from sqlalchemy import inspect, text
            insp = inspect(db.engine)
            if insp.has_table('inventario_fisico'):
                cols = [c['name'] for c in insp.get_columns('inventario_fisico')]
                if 'nuevo_estado' not in cols:
                    db.session.execute(text('ALTER TABLE inventario_fisico ADD COLUMN nuevo_estado VARCHAR(10)'))
                    db.session.commit()
        except Exception:
            pass

    return app
