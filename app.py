import os
from flask import Flask, request, jsonify
from flask_cors import CORS # Import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Bot, BotLog
from bot_manager import bot_manager
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ✅ បើក CORS សម្រាប់ Frontend របស់អ្នក
CORS(app, supports_credentials=True, origins=["https://host.anajakcode.site", "http://forest-smp-test.vercel.app"])

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///bots.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# ============================================================
# 🔐 AUTH APIs
# ============================================================
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'message': 'Username exists'}), 400
    
    user = User(username=data['username'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        login_user(user)
        return jsonify({'success': True, 'username': user.username})
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/me')
def api_me():
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'username': current_user.username})
    return jsonify({'authenticated': False})

# ============================================================
# 🤖 BOT APIs
# ============================================================
@app.route('/api/bots', methods=['GET'])
@login_required
def get_bots():
    bots = Bot.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': b.id, 'name': b.name, 'status': b.status
    } for b in bots])

@app.route('/api/bots', methods=['POST'])
@login_required
def create_bot():
    data = request.json
    bot = Bot(name=data['name'], token=data['token'], user_id=current_user.id)
    db.session.add(bot)
    db.session.commit()
    bot_manager.save_bot_code(current_user.id, bot.id, data['code'], data.get('requirements', ''))
    return jsonify({'success': True})

@app.route('/api/bots/<int:bot_id>/start', methods=['POST'])
@login_required
def start_bot(bot_id):
    success, msg = bot_manager.start_bot(bot_id, current_user.id)
    return jsonify({'success': success, 'message': msg})

@app.route('/api/bots/<int:bot_id>/stop', methods=['POST'])
@login_required
def stop_bot(bot_id):
    success, msg = bot_manager.stop_bot(bot_id)
    return jsonify({'success': success, 'message': msg})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
