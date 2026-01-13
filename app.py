from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os

load_dotenv()

from config import Config
from models import db, Admin
from werkzeug.security import generate_password_hash

login_manager = LoginManager()
login_manager.login_view = 'admin.login'


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    
    # Initialize Firebase
    from firebase_setup import initialize_firebase
    initialize_firebase(app)

    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {'now': datetime.now}

    @app.before_request
    def check_election_expiry():
        from models import Election
        from datetime import datetime
        
        # Check for active elections that have passed their end time
        expired_elections = Election.query.filter(
            Election.status == 'active', 
            Election.end_time <= datetime.now()
        ).all()
        
        if expired_elections:
            for election in expired_elections:
                election.status = 'completed'
                # Note: We don't change end_time here as it was set during creation/edit
                # and acts as the trigger.
            db.session.commit()
            # We don't flash here because it might happen on a random request (like fetching an image)
            # or for a random user. The status change is enough.

            # or for a random user. The status change is enough.


    @app.errorhandler(404)
    def page_not_found(e):
        from flask import render_template
        return render_template('404.html'), 404

    from routes.admin import admin_bp
    from routes.public import public_bp
    
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(public_bp, url_prefix='/')
    
    # Create database structure eagerly for this simple app
    with app.app_context():
        db.create_all()
        # Create default super admin if not exists
        if not Admin.query.filter_by(username='admin').first():
            hashed_password = generate_password_hash('admin', method='pbkdf2:sha256')
            default_admin = Admin(
                username='admin', 
                email='praveenkumar051207@gmail.com',
                password_hash=hashed_password,
                is_super_admin=True,
                is_force_change_password=True, # Force change even for default
                perm_manage_elections=True,
                perm_manage_electors=True,
                perm_manage_admins=True
            )
            db.session.add(default_admin)
            db.session.commit()
            print("Default super-admin created: admin/admin (praveenkumar051207@gmail.com)")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
