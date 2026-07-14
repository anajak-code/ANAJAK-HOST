from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# ============================================================
# 👤 USER MODEL
# ============================================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ទំនាក់ទំនងជាមួយ Bot (មួយ User មាន Bot ច្រើន)
    bots = db.relationship('Bot', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ============================================================
# 🤖 BOT MODEL
# ============================================================
class Bot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    token = db.Column(db.String(255), nullable=False, unique=True)
    status = db.Column(db.String(20), default='stopped')  # running, stopped, error
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_started = db.Column(db.DateTime)
    pid = db.Column(db.Integer)  # Process ID
    
    # ទំនាក់ទំនងជាមួយ Log (មួយ Bot មាន Log ច្រើន)
    logs = db.relationship('BotLog', backref='bot', lazy=True, cascade='all, delete-orphan')


# ============================================================
# 📋 BOT LOG MODEL (បានបន្ថែមថ្មី)
# ============================================================
class BotLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    log_type = db.Column(db.String(20), default='info')  # info, success, warning, error
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
