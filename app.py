import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from models import db, User, Bot, BotLog
from bot_manager import bot_manager
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

load_dotenv()

app = Flask(__name__, static_folder='../frontend', static_url_path='')

# CORS Configuration
CORS(app, 
     supports_credentials=True, 
     origins=["https://forest-smp-test.vercel.app", "http://localhost:3000", "http://localhost:5500"])

app.config['JWT_SECRET_KEY'] = os.getenv('SECRET_KEY', 'super-secret-key-change-this')
jwt = JWTManager(app)

# Database Configuration
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///bots.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

# Welcome Route
@app.route('/')
def welcome():
    return jsonify({
        "status": "online",
        "message": "Anajak Bot Host API is running!",
        "frontend": "https://forest-smp-test.vercel.app"
    })

# Health Check
@app.route('/api/health')
def health():
    return jsonify({"status": "healthy", "database": "connected"})

# Register
@app.route('/api/register', methods=['POST'])
def api_register():
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'សូមបញ្ចូល Username និង Password'}), 400
        
        if len(username) < 3:
            return jsonify({'success': False, 'message': 'Username តរូវតែមានយ៉ាងតិច ៣តួ'}), 400
        
        if len(password) < 4:
            return jsonify({'success': False, 'message': 'Password ត្ូវតែមានយ៉ាងតិច ៤តួ'}), 400
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username នេះមានរួចហើយ'}), 400
        
        # Create user
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Create token
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'success': True, 
            'token': access_token, 
            'username': user.username,
            'message': 'ចុះឈ្មោះជោគជ័យ!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Login
@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'សូមបញ្ចូល Username និង Password'}), 400
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            access_token = create_access_token(identity=user.id)
            return jsonify({
                'success': True, 
                'token': access_token, 
                'username': user.username,
                'message': 'Login ជោគជ័យ!'
            })
        
        return jsonify({'success': False, 'message': 'Username ឬ Password មិនត្រឹមត្រូវ'}), 401
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Get Current User
@app.route('/api/me')
@jwt_required()
def api_me():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if user:
            return jsonify({'authenticated': True, 'username': user.username})
        return jsonify({'authenticated': False}), 401
    except Exception as e:
        return jsonify({'authenticated': False, 'error': str(e)}), 500

# Get Bots
@app.route('/api/bots', methods=['GET'])
@jwt_required()
def get_bots():
    try:
        current_user_id = get_jwt_identity()
        bots = Bot.query.filter_by(user_id=current_user_id).all()
        
        bots_list = [{
            'id': b.id,
            'name': b.name,
            'status': b.status,
            'created_at': b.created_at.strftime('%Y-%m-%d %H:%M')
        } for b in bots]
        
        return jsonify(bots_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Create Bot
@app.route('/api/bots', methods=['POST'])
@jwt_required()
def create_bot():
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        name = data.get('name', '').strip()
        token = data.get('token', '').strip()
        code = data.get('code', '')
        requirements = data.get('requirements', 'python-telegram-bot==21.6')
        
        if not name:
            return jsonify({'success': False, 'message': 'សូមបញ្ចូល្មោះ Bot'}), 400
        
        if not token:
            return jsonify({'success': False, 'message': 'សូមបញ្ចូល Telegram Token'}), 400
        
        # Check if token already exists
        existing_bot = Bot.query.filter_by(token=token).first()
        if existing_bot:
            return jsonify({'success': False, 'message': 'Token នេះត្រូវបានប្រើរួចហើយ! សូមប្រើ Token ផ្សេង'}), 400
        
        # Create bot
        bot = Bot(
            name=name,
            token=token,
            user_id=current_user_id,
            status='stopped'
        )
        
        db.session.add(bot)
        db.session.commit()
        
        # Save bot code
        if code:
            success, msg = bot_manager.save_bot_code(current_user_id, bot.id, code, requirements)
            if not success:
                return jsonify({'success': False, 'message': f'បង្កើត Bot ជោគជ័យ ប៉ុន្តែមានបញ្ហា Save code: {msg}'}), 200
        
        return jsonify({
            'success': True, 
            'message': 'បង្កើត Bot ជោគជ័យ!',
            'bot_id': bot.id
        })
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Token ឈ្មោះនេះមានរួចហើយ!'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Start Bot
@app.route('/api/bots/<int:bot_id>/start', methods=['POST'])
@jwt_required()
def start_bot(bot_id):
    try:
        current_user_id = get_jwt_identity()
        bot = Bot.query.get_or_404(bot_id)
        
        if bot.user_id != current_user_id:
            return jsonify({'success': False, 'message': 'មិនមានសិទ្ធិ'}), 403
        
        success, message = bot_manager.start_bot(bot_id, current_user_id)
        return jsonify({'success': success, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Stop Bot
@app.route('/api/bots/<int:bot_id>/stop', methods=['POST'])
@jwt_required()
def stop_bot(bot_id):
    try:
        current_user_id = get_jwt_identity()
        bot = Bot.query.get_or_404(bot_id)
        
        if bot.user_id != current_user_id:
            return jsonify({'success': False, 'message': 'មិនមានសិទ្ធិ'}), 403
        
        success, message = bot_manager.stop_bot(bot_id)
        return jsonify({'success': success, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Delete Bot
@app.route('/api/bots/<int:bot_id>/delete', methods=['POST'])
@jwt_required()
def delete_bot(bot_id):
    try:
        current_user_id = get_jwt_identity()
        bot = Bot.query.get_or_404(bot_id)
        
        if bot.user_id != current_user_id:
            return jsonify({'success': False, 'message': 'មិនមានសិទ្ធិ'}), 403
        
        # Stop bot if running
        if bot.status == 'running':
            bot_manager.stop_bot(bot_id)
        
        db.session.delete(bot)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'លុប Bot ជោគជ័យ!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
