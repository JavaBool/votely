import firebase_admin
from firebase_admin import credentials, auth
import os
import json

def initialize_firebase(app):
    # 1. Try env var
    cred_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')
    cred = None

    if cred_json:
        try:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        except Exception as e:
            print(f"Error parsing FIREBASE_CREDENTIALS_JSON: {e}")

    # 2. Try file if no env var or parsing failed
    if not cred:
        cred_path = os.path.join(app.root_path, 'firebase_credentials.json')
        if os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
            except Exception as e:
                print(f"Error loading firebase_credentials.json: {e}")
        else:
            print("WARNING: No Firebase credentials found (Env or File).")
            return

    try:
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized successfully.")
    except ValueError:
        # App already initialized
        pass
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
