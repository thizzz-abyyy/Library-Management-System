import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

def resolve_database_uri(db_type, host, port, user, password, db_name, fallback_sqlite=True):
    # 1. Direct DATABASE_URL or MYSQL_URL takes top priority (standard on Vercel / Cloud Hosts)
    direct_url = os.getenv('DATABASE_URL') or os.getenv('MYSQL_URL')
    if direct_url:
        # Standardize MySQL connection driver for SQLAlchemy 1.4/2.0+
        if direct_url.startswith('mysql://'):
            direct_url = direct_url.replace('mysql://', 'mysql+pymysql://', 1)
        elif direct_url.startswith('postgres://'):
            direct_url = direct_url.replace('postgres://', 'postgresql://', 1)
        print("[DB] Using configured cloud DATABASE_URL")
        return direct_url

    # 2. Discrete MySQL environment parameters
    if db_type == 'mysql':
        try:
            import pymysql
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                connect_timeout=3
            )
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.commit()
            conn.close()
            print(f"[DB] Successfully connected to MySQL at {host}:{port}/{db_name}")
            pw_part = f":{password}" if password else ""
            return f"mysql+pymysql://{user}{pw_part}@{host}:{port}/{db_name}?charset=utf8mb4"
        except Exception as e:
            if fallback_sqlite:
                is_serverless = os.getenv('VERCEL') == '1' or os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None
                sqlite_path = '/tmp/library.db' if is_serverless else (BASE_DIR / 'library.db').as_posix()
                print(f"[DB Notice] MySQL connection failed ({e}).")
                print(f"[DB Notice] Falling back to SQLite database at {sqlite_path} for immediate functionality.")
                return f"sqlite:///{sqlite_path}"
            raise e

    # 3. Default fallback SQLite
    is_serverless = os.getenv('VERCEL') == '1' or os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None
    sqlite_path = '/tmp/library.db' if is_serverless else (BASE_DIR / 'library.db').as_posix()
    return f"sqlite:///{sqlite_path}"


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'library-mgmt-secret-key-2026-prod')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'
    
    # Serverless runtime detection
    IS_SERVERLESS = os.getenv('VERCEL') == '1' or os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None

    # Base & Upload directories
    BASE_DIR = BASE_DIR
    if IS_SERVERLESS:
        UPLOAD_FOLDER = Path('/tmp') / 'uploads'
        REPORTS_FOLDER = Path('/tmp') / 'reports' / 'exports'
    else:
        UPLOAD_FOLDER = BASE_DIR / 'uploads'
        REPORTS_FOLDER = BASE_DIR / 'reports' / 'exports'

    BOOK_COVERS_FOLDER = UPLOAD_FOLDER / 'book_covers'
    EBOOKS_FOLDER = UPLOAD_FOLDER / 'ebooks'
    QR_CODES_FOLDER = UPLOAD_FOLDER / 'qr_codes'
    AVATARS_FOLDER = UPLOAD_FOLDER / 'avatars'

    # Ensure upload subdirectories exist safely
    for folder in [BOOK_COVERS_FOLDER, EBOOKS_FOLDER, QR_CODES_FOLDER, AVATARS_FOLDER, REPORTS_FOLDER]:
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    # Allowed extensions
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
    ALLOWED_EBOOK_EXTENSIONS = {'pdf', 'epub'}
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)) # 16 MB

    # Database parameters
    DB_TYPE = os.getenv('DB_TYPE', 'mysql').lower()
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB = os.getenv('MYSQL_DB', 'library_db')
    FALLBACK_TO_SQLITE = os.getenv('FALLBACK_TO_SQLITE', 'True').lower() in ('true', '1', 'yes')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = resolve_database_uri(
        DB_TYPE, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, FALLBACK_TO_SQLITE
    )

    # Serverless connection pool health
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }
