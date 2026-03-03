import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_db_url():
    url = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'fasttrade.db'))
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url

class Config:
    """Central configuration object for FASTTrade backed by MySQL."""

    # Basic Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', '1') == '1'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = get_db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }

    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'YL6Y6eGXY2vons4yQXerpgJIHa-pV601WX4RDRKR-_U')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # File upload configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    # Domain-specific settings
    ALLOWED_USER_ROLES = ('student', 'faculty', 'admin')
    DEFAULT_USER_ROLE = 'student'
    LISTING_STATUSES = ('available', 'sold', 'removed')
