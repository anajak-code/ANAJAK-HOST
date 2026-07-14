import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Bot, BotLog
from bot_manager import bot_manager
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///bots.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============================================================
# 🏠 PUBLIC ROUTES
# ============================================================
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username មានរួចហើយ!', 'error')
            return redirect(url_for('register'))
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('✅ Register ជោគជ័យ! សូម Login', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('❌ Username ឬ Password មិនត្រឹមត្រូវ!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ============================================================
# 📊 DASHBOARD
# ============================================================
@app.route('/dashboard')
@login_required
def dashboard():
    bots = Bot.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', bots=bots)

# ============================================================
# 🤖 BOT MANAGEMENT
# ============================================================
@app.route('/bot/create', methods=['GET', 'POST'])
@login_required
def create_bot():
    if request.method == 'POST':
        name = request.form.get('name')
        token = request.form.get('token')
        code = request.form.get('code')
        requirements = request.form.get('requirements', '')
        
        if Bot.query.filter_by(token=token).first():
            flash('❌ Bot Token នេះមានរួចហើយ!', 'error')
            return redirect(url_for('create_bot'))
        
        bot = Bot(name=name, token=token, user_id=current_user.id)
        db.session.add(bot)
        db.session.commit()
        
        # Save bot code
        bot_manager.save_bot_code(current_user.id, bot.id, code, requirements)
        
        flash('✅ Bot បានបង្កើតជោគជ័យ!', 'success')
        return redirect(url_for('bot_detail', bot_id=bot.id))
    
    return render_template('create_bot.html')

@app.route('/bot/<int:bot_id>')
@login_required
def bot_detail(bot_id):
    bot = Bot.query.get_or_404(bot_id)
    if bot.user_id != current_user.id:
        flash('❌ មិនមានសិទ្ធិ!', 'error')
        return redirect(url_for('dashboard'))
    
    logs = BotLog.query.filter_by(bot_id=bot_id).order_by(BotLog.timestamp.desc()).limit(50).all()
    stats = bot_manager.get_bot_stats(bot_id)
    
    return render_template('bot_detail.html', bot=bot, logs=logs, stats=stats)

@app.route('/bot/<int:bot_id>/start', methods=['POST'])
@login_required
def start_bot(bot_id):
    bot = Bot.query.get_or_404(bot_id)
    if bot.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'មិនមានសិទ្ធិ!'})
    
    success, message = bot_manager.start_bot(bot_id, current_user.id)
    return jsonify({'success': success, 'message': message})

@app.route('/bot/<int:bot_id>/stop', methods=['POST'])
@login_required
def stop_bot(bot_id):
    bot = Bot.query.get_or_404(bot_id)
    if bot.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'មិនមានសិទ្ធិ!'})
    
    success, message = bot_manager.stop_bot(bot_id)
    return jsonify({'success': success, 'message': message})

@app.route('/bot/<int:bot_id>/delete', methods=['POST'])
@login_required
def delete_bot(bot_id):
    bot = Bot.query.get_or_404(bot_id)
    if bot.user_id != current_user.id:
        flash('❌ មិនមានសិទ្ធិ!', 'error')
        return redirect(url_for('dashboard'))
    
    # Stop bot if running
    if bot.status == 'running':
        bot_manager.stop_bot(bot_id)
    
    db.session.delete(bot)
    db.session.commit()
    
    flash('✅ Bot បានលុប!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/bot/<int:bot_id>/logs')
@login_required
def bot_logs(bot_id):
    bot = Bot.query.get_or_404(bot_id)
    if bot.user_id != current_user.id:
        return jsonify({'logs': []})
    
    logs = bot_manager.get_logs(bot_id, current_user.id)
    return jsonify({'logs': logs})

# ============================================================
# 🗄️ DATABASE INIT
# ============================================================
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
