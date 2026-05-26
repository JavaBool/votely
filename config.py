import os

class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-prod'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'election.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'your-email@gmail.com'
    MAIL_PASSWORD = 'your-password'
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_SECURE   = True   # HTTPS only
    SESSION_COOKIE_HTTPONLY = True   # No JS access
    SESSION_COOKIE_SAMESITE = 'Lax' # CSRF mitigation
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour timeout


    _firebase_config_str = os.environ.get('FIREBASE_CONFIG_JSON') or 'firebase_config.json'
    if _firebase_config_str:
        import json
        FIREBASE_CONFIG = json.loads(_firebase_config_str)

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
