import os
import sys
import subprocess
from datetime import datetime
from models import db, Bot, BotLog

class BotManager:
    def __init__(self, base_dir='bots_data'):
        self.base_dir = base_dir
        self.processes = {}
    
    def get_bot_dir(self, user_id, bot_id):
        bot_dir = os.path.join(self.base_dir, str(user_id), str(bot_id))
        os.makedirs(bot_dir, exist_ok=True)
        return bot_dir
    
    def save_bot_code(self, user_id, bot_id, code, requirements=''):
        bot_dir = self.get_bot_dir(user_id, bot_id)
        
        with open(os.path.join(bot_dir, 'bot.py'), 'w', encoding='utf-8') as f:
            f.write(code)
        
        if requirements:
            with open(os.path.join(bot_dir, 'requirements.txt'), 'w') as f:
                f.write(requirements)
        
        return bot_dir
    
    def start_bot(self, bot_id, user_id):
        bot = Bot.query.get(bot_id)
        if not bot or bot.status == 'running':
            return False, "Bot កំពុងដំណើរការរួចហើយ"
        
        bot_dir = self.get_bot_dir(user_id, bot_id)
        bot_file = os.path.join(bot_dir, 'bot.py')
        
        if not os.path.exists(bot_file):
            return False, "Bot code មិនមាន"
        
        try:
            process = subprocess.Popen(
                [sys.executable, bot_file],
                cwd=bot_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[bot_id] = process
            
            bot.status = 'running'
            bot.pid = process.pid
            bot.last_started = datetime.utcnow()
            db.session.commit()
            
            self.add_log(bot_id, f"✅ Bot បានចាប់ផ្ដើម (PID: {process.pid})", 'success')
            return True, "Bot បានចាប់ផ្ដើម"
            
        except Exception as e:
            self.add_log(bot_id, f" Error: {str(e)}", 'error')
            return False, str(e)
    
    def stop_bot(self, bot_id):
        bot = Bot.query.get(bot_id)
        if not bot or bot.status != 'running':
            return False, "Bot មិនទាន់ដំណើរការ"
        
        try:
            if bot_id in self.processes:
                process = self.processes[bot_id]
                process.terminate()
                process.wait(timeout=5)
                del self.processes[bot_id]
            
            bot.status = 'stopped'
            bot.pid = None
            db.session.commit()
            
            self.add_log(bot_id, "⏹️ Bot បានបញ្ប់", 'warning')
            return True, "Bot បានបញ្ឈប់"
            
        except Exception as e:
            return False, str(e)
    
    def add_log(self, bot_id, message, log_type='info'):
        log = BotLog(
            bot_id=bot_id,
            message=message,
            log_type=log_type,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()

bot_manager = BotManager()
