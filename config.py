import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
basedir = Path(__file__).resolve().parent
load_dotenv(basedir / ".env")


class Config:
    """Base configuration loaded from environment variables."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Environment
    ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = ENV == "development"
    TESTING = False
    
    # Ensure instance and exports directories exist
    instance_dir = basedir / "instance"
    instance_dir.mkdir(parents=True, exist_ok=True)

    # Database selection
    db_uri = os.getenv("SQLALCHEMY_DATABASE_URI")
    db_engine = os.getenv("DB_ENGINE", "sqlite").lower()
    
    if db_uri and not db_uri.endswith("instance/attendance.db"):
        SQLALCHEMY_DATABASE_URI = db_uri
    elif db_engine == "mysql":
        db_user = os.getenv("DB_USER", "admin")
        db_pass = os.getenv("DB_PASSWORD", "")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "3306")
        db_name = os.getenv("DB_NAME", "attendance_system")
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
        )
    else:
        # Default local SQLite file with normalized posix path
        db_file = (instance_dir / "attendance.db").as_posix()
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_file}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    if "mysql" in SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_recycle": 280,
            "pool_pre_ping": True,
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {}

    # Security & Session Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    # AWS S3 Settings
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    S3_PRESIGNED_EXPIRATION = int(os.getenv("S3_PRESIGNED_EXPIRATION", "3600"))

    # Local export directory for offline/local CSV downloads
    LOCAL_EXPORTS_DIR = basedir / "exports"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
