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
    

    _firebase_config_str = os.environ.get('FIREBASE_CONFIG_JSON')
    if _firebase_config_str:
        import json
        FIREBASE_CONFIG = json.loads(_firebase_config_str)
    else:
        FIREBASE_CONFIG = {
            "apiKey": "AIzaSyDrabDgnOCPTCiJJNL-qnAbLQTUt8NtZaA",
            "authDomain": "electoral-regime.firebaseapp.com",
            "projectId": "electoral-regime",
            "storageBucket": "electoral-regime.firebasestorage.app",
            "messagingSenderId": "866990300546",
            "appId": "1:866990300546:web:0a9c93ace98b9e95a0439b",
            "measurementId": "G-YHD3VNWKTN"
        }

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
