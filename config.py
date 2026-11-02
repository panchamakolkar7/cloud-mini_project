import os
from pathlib import Path
from dotenv import load_dotenv

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.getenv("SECRET_KEY", "quotacloud_secure_secret_key_change_in_production_2026")
    
    # Database URI (supports SQLite locally or PostgreSQL on Render/Cloud)
    raw_db_url = os.getenv("DATABASE_URL")
    if raw_db_url:
        if raw_db_url.startswith("postgres://"):
            raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = raw_db_url
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'quotacloud.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Storage Backend: 'local' or 'hdfs'
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower().strip()
    
    # Local Storage Directory (outside static/ to prevent unauthorized direct URL access)
    raw_storage_dir = os.getenv("LOCAL_STORAGE_DIR", "storage/data")
    if os.path.isabs(raw_storage_dir):
        LOCAL_STORAGE_DIR = Path(raw_storage_dir)
    else:
        LOCAL_STORAGE_DIR = BASE_DIR / raw_storage_dir
    
    # Hadoop HDFS configuration
    HDFS_NAMENODE_URL = os.getenv("HDFS_NAMENODE_URL", "http://localhost:9870").rstrip("/")
    HDFS_USER = os.getenv("HDFS_USER", "hadoop")
    HDFS_ROOT_DIR = os.getenv("HDFS_ROOT_DIR", "/quotacloud/users").rstrip("/")
    HDFS_TIMEOUT = int(os.getenv("HDFS_TIMEOUT", "5"))
    
    # Quota defaults (51200 MB = 50 GB)
    DEFAULT_USER_QUOTA_MB = int(os.getenv("DEFAULT_USER_QUOTA_MB", "51200"))
    DEFAULT_USER_QUOTA_BYTES = DEFAULT_USER_QUOTA_MB * 1024 * 1024
    
    STORAGE_WARNING_THRESHOLD_PERCENT = float(os.getenv("STORAGE_WARNING_THRESHOLD_PERCENT", "80.0"))
    SYSTEM_STORAGE_CAPACITY_MB = int(os.getenv("SYSTEM_STORAGE_CAPACITY_MB", "512000"))
    SYSTEM_STORAGE_CAPACITY_BYTES = SYSTEM_STORAGE_CAPACITY_MB * 1024 * 1024
    
    # Upload limits (5120 MB = 5 GB)
    MAX_CONTENT_LENGTH_MB = int(os.getenv("MAX_CONTENT_LENGTH_MB", "5120"))
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH_MB * 1024 * 1024
    
    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400  # 1 day

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    STORAGE_BACKEND = "local"
    LOCAL_STORAGE_DIR = BASE_DIR / "storage" / "test_data"
    WTF_CSRF_ENABLED = False
