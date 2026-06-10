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
        from app.models import UnidadAdministrativa
        return {'unidades': UnidadAdministrativa.query.all()}

    with app.app_context():
        db.create_all()
        if not Usuario.query.filter_by(username='admin').first():
            from werkzeug.security import generate_password_hash
            admin = Usuario(username='admin', password=generate_password_hash('admin'), rol='ADMINISTRADOR')
            db.session.add(admin)
            db.session.commit()

    return app
