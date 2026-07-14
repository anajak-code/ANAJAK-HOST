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
        try:
            bot_dir = self.get_bot_dir(user_id, bot_id)
            
            # Save main bot file
            with open(os.path.join(bot_dir, 'bot.py'), 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Save requirements
            if requirements:
                with open(os.path.join(bot_dir, 'requirements.txt'), 'w') as f:
                    f.write(requirements)
            
            return True, "Code saved successfully"
        except Exception as e:
            return False, str(e)
    
    def start_bot(self, bot_id, user_id):
        bot = Bot.query.get(bot_id)
        if not bot:
            return False, "Bot មិនមានក្នុងប្រព័ន្ធ"
        
        if bot.status == 'running':
            return False, "Bot កំពុងដំណើរការរួចហើយ"
        
        try:
            bot_dir = self.get_bot_dir(user_id, bot_id)
            bot_file = os.path.join(bot_dir, 'bot.py')
            
            if not os.path.exists(bot_file):
                return False, "Bot code មិនមាន"
            
            # Replace token in code
            with open(bot_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            code = code.replace('YOUR_TOKEN', bot.token)
            
            temp_file = os.path.join(bot_dir, 'bot_running.py')
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            process = subprocess.Popen(
                [sys.executable, temp_file],
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
            return True, "Bot បានចាប់ផ្ើមដំណើរការ"
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.add_log(bot_id, error_msg, 'error')
            return False, error_msg
    
    def stop_bot(self, bot_id):
        bot = Bot.query.get(bot_id)
        if not bot:
            return False, "Bot មិនមានក្នុងប្រព័ន្ធ"
        
        if bot.status != 'running':
            return False, "Bot មិនទាន់ដំណើរការ"
        
        try:
            if bot_id in self.processes:
                process = self.processes[bot_id]
                process.terminate()
                try:
                    process.wait(timeout=5)
                except:
                    process.kill()
                del self.processes[bot_id]
            
            bot.status = 'stopped'
            bot.pid = None
            db.session.commit()
            
            self.add_log(bot_id, "⏹️ Bot បានបញ្ប់", 'warning')
            return True, "Bot បានបញ្ឈប់ដំណើរការ"
            
        except Exception as e:
            return False, str(e)
    
    def add_log(self, bot_id, message, log_type='info'):
        try:
            log = BotLog(
                bot_id=bot_id,
                message=message,
                log_type=log_type,
                timestamp=datetime.utcnow()
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass

bot_manager = BotManager()
