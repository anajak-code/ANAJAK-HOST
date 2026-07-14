import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Bot, BotLog
from bot_manager import bot_manager
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app, supports_credentials=True, origins=["*"])

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

# Serve Frontend
@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')

# Auth APIs
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'សូមបញ្ចូល Username និង Password'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Username នេះមានរួចហើយ'}), 400
    
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'ចុះឈ្មោះជោគជ័យ!'})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        login_user(user)
        return jsonify({'success': True, 'username': user.username})
    
    return jsonify({'success': False, 'message': 'Username ឬ Password មិនត្រឹមត្រូវ'}), 401

@app.route('/api/me')
def api_me():
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'username': current_user.username})
    return jsonify({'authenticated': False})

@app.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({'success': True})

# Bot APIs
@app.route('/api/bots', methods=['GET'])
@login_required
def get_bots():
    bots = Bot.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': b.id,
        'name': b.name,
        'status': b.status,
        'created_at': b.created_at.strftime('%Y-%m-%d %H:%M')
    } for b in bots])

@app.route('/api/bots', methods=['POST'])
@login_required
def create_bot():
    data = request.json
    
    if not data.get('name') or not data.get('token'):
        return jsonify({'success': False, 'message': 'សូមបញ្ចូលឈ្មោះ និង Token'}), 400
    
    bot = Bot(
        name=data['name'],
        token=data['token'],
        user_id=current_user.id
    )
    db.session.add(bot)
    db.session.commit()
    
    bot_manager.save_bot_code(
        current_user.id, 
        bot.id, 
        data.get('code', ''), 
        data.get('requirements', 'python-telegram-bot==21.6')
    )
    
    return jsonify({'success': True, 'message': 'បង្កើត Bot ជោគជ័យ!'})

@app.route('/api/bots/<int:bot_id>/start', methods=['POST'])
@login_required
def start_bot(bot_id):
    bot = Bot.query.get_or_404(bot_id)
    if bot.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'មិនមានសិទធិ'}), 403
    
    success, message = bot_manager.start_bot(bot_id, current_user.id)
    return jsonify({'success': success, 'message': message})

@app.route('/api/bots/<int:bot_id>/stop', methods=['POST'])
@login_required
def stop_bot(bot_id):
    bot = Bot.query.get_or_404(bot_id)
    if bot.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'មិនមានសិទ្ិ'}), 403
    
    success, message = bot_manager.stop_bot(bot_id)
    return jsonify({'success': success, 'message': message})

@app.route('/api/bots/<int:bot_id>/delete', methods=['POST'])
@login_required
def delete_bot(bot_id):
    bot = Bot.query.get_or_404(bot_id)
    if bot.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'មិនមានសិទ្ធិ'}), 403
    
    if bot.status == 'running':
        bot_manager.stop_bot(bot_id)
    
    db.session.delete(bot)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'លុប Bot ជោគជ័យ!'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
