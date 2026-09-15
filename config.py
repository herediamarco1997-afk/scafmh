import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db_url = os.getenv('DATABASE_URL', '')
if db_url and db_url.startswith('postgres'):
    # Neon/Render PostgreSQL: ensure proper prefix for SQLAlchemy
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = db_url
else:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'activos.db')

SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = os.getenv('SECRET_KEY', 'scafmh-secret-key-2026')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'backups')

# Cloudinary
CLOUDINARY_URL = os.getenv('CLOUDINARY_URL', '')
# Si CLOUDINARY_URL está vacía, extraer de variables individuales
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')
CLOUDINARY_UPLOAD_PRESET = os.getenv('CLOUDINARY_UPLOAD_PRESET', 'activos_fotos')
