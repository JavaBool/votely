import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-prod'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///election.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'your-email@gmail.com'
    MAIL_PASSWORD = 'your-password'
    
    # Firebase Web Config
    # Try loading from env var first (for production)
    _firebase_config_str = os.environ.get('FIREBASE_CONFIG_JSON')
    if _firebase_config_str:
        import json
        FIREBASE_CONFIG = json.loads(_firebase_config_str)
    else:
        # Fallback for local dev
        FIREBASE_CONFIG = {
            "apiKey": "AIzaSyDrabDgnOCPTCiJJNL-qnAbLQTUt8NtZaA",
            "authDomain": "electoral-regime.firebaseapp.com",
            "projectId": "electoral-regime",
            "storageBucket": "electoral-regime.firebasestorage.app",
            "messagingSenderId": "866990300546",
            "appId": "1:866990300546:web:0a9c93ace98b9e95a0439b",
            "measurementId": "G-YHD3VNWKTN"
        }
    # Email Configuration (Gmail API)
    # No SMTP passwords here. We use token.json generated via OAuth2.
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
