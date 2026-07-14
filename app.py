import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from models import db, User, Bot, BotLog
from bot_manager import bot_manager
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='../frontend', static_url_path='')

# ✅ កំណត់ CORS សម្រាប់ Vercel
CORS(app, supports_credentials=True, origins=["https://forest-smp-test.vercel.app", "http://localhost:3000"])

app.config['JWT_SECRET_KEY'] = os.getenv('SECRET_KEY', 'super-secret-key')
jwt = JWTManager(app)

database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///bots.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# Serve Frontend
@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')

# --- AUTH APIS (Using JWT) ---
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
    
    # បង្កើត Token ភ្លាមៗបន្ទាប់ពី Register
    access_token = create_access_token(identity=user.id)
    return jsonify({'success': True, 'token': access_token, 'username': user.username})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        # ✅ បង្កើត Access Token
        access_token = create_access_token(identity=user.id)
        return jsonify({
            'success': True, 
            'token': access_token, 
            'username': user.username
        })
    
    return jsonify({'success': False, 'message': 'Username ឬ Password មិនត្រឹមត្រូវ'}), 401

# --- PROTECTED ROUTES (Using Token) ---
@app.route('/api/me')
@jwt_required()
def api_me():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user:
        return jsonify({'authenticated': True, 'username': user.username})
    return jsonify({'authenticated': False}), 401

@app.route('/api/bots', methods=['GET'])
@jwt_required()
def get_bots():
    current_user_id = get_jwt_identity()
    bots = Bot.query.filter_by(user_id=current_user_id).all()
    return jsonify([{
        'id': b.id, 'name': b.name, 'status': b.status,
        'created_at': b.created_at.strftime('%Y-%m-%d %H:%M')
    } for b in bots])

@app.route('/api/bots', methods=['POST'])
@jwt_required()
def create_bot():
    current_user_id = get_jwt_identity()
    data = request.json
    
    if not data.get('name') or not data.get('token'):
        return jsonify({'success': False, 'message': 'សូមបញ្ចូលឈ្មោះ និង Token'}), 400
    
    bot = Bot(name=data['name'], token=data['token'], user_id=current_user_id)
    db.session.add(bot)
    db.session.commit()
    
    bot_manager.save_bot_code(current_user_id, bot.id, data.get('code', ''), data.get('requirements', 'python-telegram-bot==21.6'))
    return jsonify({'success': True, 'message': 'បង្កើត Bot ជោគជ័យ!'})

@app.route('/api/bots/<int:bot_id>/start', methods=['POST'])
@jwt_required()
def start_bot(bot_id):
    current_user_id = get_jwt_identity()
    bot = Bot.query.get_or_404(bot_id)
    if bot.user_id != current_user_id:
        return jsonify({'success': False, 'message': 'មិនមានសិទធិ'}), 403
    
    success, message = bot_manager.start_bot(bot_id, current_user_id)
    return jsonify({'success': success, 'message': message})

@app.route('/api/bots/<int:bot_id>/stop', methods=['POST'])
@jwt_required()
def stop_bot(bot_id):
    current_user_id = get_jwt_identity()
    bot = Bot.query.get_or_404(bot_id)
    if bot.user_id != current_user_id:
        return jsonify({'success': False, 'message': 'មិនមានសិទ្ធិ'}), 403
    
    success, message = bot_manager.stop_bot(bot_id)
    return jsonify({'success': success, 'message': message})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
