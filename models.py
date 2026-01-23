from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from utils import get_ist_now

db = SQLAlchemy()

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_super_admin = db.Column(db.Boolean, default=False)
    is_force_change_password = db.Column(db.Boolean, default=True)
    otp_secret = db.Column(db.String(10), nullable=True)
    

    perm_manage_elections = db.Column(db.Boolean, default=False)
    perm_manage_electors = db.Column(db.Boolean, default=False)
    perm_manage_admins = db.Column(db.Boolean, default=False)
    
    @property
    def can_manage_elections(self):
        return self.is_super_admin or self.perm_manage_elections

    @property
    def can_manage_electors(self):
        return self.is_super_admin or self.perm_manage_electors

    @property
    def can_manage_admins(self):
        return self.is_super_admin or self.perm_manage_admins

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Election(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    nomination_start = db.Column(db.DateTime, nullable=False)
    nomination_end = db.Column(db.DateTime, nullable=False)
    

    config_age = db.Column(db.Integer, default=1) 
    min_age = db.Column(db.Integer, default=0)
    config_photo = db.Column(db.Integer, default=1)
    
    status = db.Column(db.String(20), default='draft')
    show_results = db.Column(db.Boolean, default=False)
    allow_nota = db.Column(db.Boolean, default=False)
    allow_phone_voting = db.Column(db.Boolean, default=True)
    
    candidates = db.relationship('Candidate', backref='election', lazy=True, cascade="all, delete-orphan")
    electors = db.relationship('Elector', backref='election', lazy=True, cascade="all, delete-orphan")
    votes = db.relationship('Vote', backref='election', lazy=True, cascade="all, delete-orphan")

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    photo_path = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='pending')
    votes = db.relationship('Vote', backref='candidate', lazy=True, cascade="all, delete-orphan")

class Elector(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    otp_secret = db.Column(db.String(10), nullable=True)
    secret_code = db.Column(db.String(6), nullable=False, default='000000')
    status = db.Column(db.String(20), default='approved')
    has_voted = db.Column(db.Boolean, default=False)
    custom_success_msg = db.Column(db.Text, nullable=True)
    
    __table_args__ = (
        db.UniqueConstraint('election_id', 'phone', name='uq_election_phone'),
        db.UniqueConstraint('election_id', 'email', name='uq_election_email'),
    )

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=True)
    # elector_id removed for privacy
    timestamp = db.Column(db.DateTime, default=get_ist_now)
