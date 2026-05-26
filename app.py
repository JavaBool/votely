from flask import Flask
from flask_session import Session
from flask_login import LoginManager
from dotenv import load_dotenv
import os
import json

load_dotenv()

from config import Config
from models import db, Admin
from werkzeug.security import generate_password_hash

login_manager = LoginManager()
login_manager.login_view = 'admin.login'

#app
@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    Session(app)
    db.init_app(app)
    login_manager.init_app(app)
    

    from firebase_setup import initialize_firebase
    initialize_firebase(app)

    @app.context_processor
    def inject_now():
        from utils import get_ist_now
        return {'now': get_ist_now}

    @app.before_request
    def check_election_expiry():
        from models import Election
        from utils import get_ist_now
        
        expired_elections = Election.query.filter(
            Election.status == 'active', 
            Election.end_time <= get_ist_now()
        ).all()
        
        if expired_elections:
            for election in expired_elections:
                election.status = 'completed'
            db.session.commit()




    @app.errorhandler(404)
    def page_not_found(e):
        from flask import render_template
        return render_template('404.html'), 404

    from routes.admin import admin_bp
    from routes.public import public_bp
    from routes.admin import setLimiter
    setLimiter(app=app)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(public_bp, url_prefix='/')
    

    with app.app_context():
        db.create_all()
        
        # Load default users from JSON file if it exists
        default_users_file = os.path.join(os.path.dirname(__file__), 'default-users.json')
        if os.path.exists(default_users_file):
            with open(default_users_file, 'r') as f:
                default_users = json.load(f)
            
            for user_data in default_users:
                username = user_data.get('username')
                existing_user = Admin.query.filter_by(username=username).first()
                
                if not existing_user:
                    hashed_password = generate_password_hash(user_data.get('password'), method='pbkdf2:sha256')
                    new_user = Admin(
                        username=username,
                        email=user_data.get('email'),
                        password_hash=hashed_password,
                        is_super_admin=user_data.get('is_super_admin', False),
                        is_force_change_password=user_data.get('is_force_change_password', False),
                        perm_manage_elections=user_data.get('perm_manage_elections', False),
                        perm_manage_electors=user_data.get('perm_manage_electors', False),
                        perm_manage_admins=user_data.get('perm_manage_admins', False)
                    )
                    db.session.add(new_user)
                    db.session.commit()
                    print(f"Admin created: {username} ({user_data.get('email')})")
                else:
                    # Update is_super_admin status if changed in JSON
                    if existing_user.is_super_admin != user_data.get('is_super_admin', False):
                        existing_user.is_super_admin = user_data.get('is_super_admin', False)
                        db.session.commit()
                        print(f"Admin updated: {username} (is_super_admin set to {existing_user.is_super_admin})")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=False)
