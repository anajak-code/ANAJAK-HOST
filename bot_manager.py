import os
import sys
import subprocess
import psutil
from datetime import datetime
from models import db, Bot, BotLog

class BotManager:
    """គ្រប់គ្រង bot processes"""
    
    def __init__(self, base_dir='bots_data'):
        self.base_dir = base_dir
        self.processes = {}  # bot_id -> process
    
    def get_bot_dir(self, user_id, bot_id):
        """ទទួល path សម្រាប់ bot"""
        bot_dir = os.path.join(self.base_dir, str(user_id), str(bot_id))
        os.makedirs(bot_dir, exist_ok=True)
        return bot_dir
    
    def save_bot_code(self, user_id, bot_id, code, requirements=''):
        """រក្សាទុក bot code"""
        bot_dir = self.get_bot_dir(user_id, bot_id)
        
        # Save main bot file
        with open(os.path.join(bot_dir, 'bot.py'), 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Save requirements
        if requirements:
            with open(os.path.join(bot_dir, 'requirements.txt'), 'w') as f:
                f.write(requirements)
        
        return bot_dir
    
    def start_bot(self, bot_id, user_id):
        """ចាប់ផ្ដើម bot"""
        bot = Bot.query.get(bot_id)
        if not bot or bot.status == 'running':
            return False, "Bot កំពុងដំណើរការរួចហើយ"
        
        bot_dir = self.get_bot_dir(user_id, bot_id)
        bot_file = os.path.join(bot_dir, 'bot.py')
        
        if not os.path.exists(bot_file):
            return False, "Bot code មិនមាន"
        
        try:
            # Run bot as subprocess
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
            self.add_log(bot_id, f"❌ Error: {str(e)}", 'error')
            return False, str(e)
    
    def stop_bot(self, bot_id):
        """បញ្ឈប់ bot"""
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
            
            self.add_log(bot_id, "⏹️ Bot បានបញ្ឈប់", 'warning')
            return True, "Bot បានបញ្ឈប់"
            
        except Exception as e:
            return False, str(e)
    
    def get_logs(self, bot_id, user_id, lines=50):
        """ទទួល logs ពី bot"""
        bot_dir = self.get_bot_dir(user_id, bot_id)
        log_file = os.path.join(bot_dir, 'bot.log')
        
        if not os.path.exists(log_file):
            return []
        
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = f.readlines()
        
        return logs[-lines:]
    
    def get_bot_stats(self, bot_id):
        """ទទួល stats របស់ bot"""
        if bot_id not in self.processes:
            return None
        
        try:
            process = self.processes[bot_id]
            proc = psutil.Process(process.pid)
            
            return {
                'cpu_percent': proc.cpu_percent(),
                'memory_mb': proc.memory_info().rss / 1024 / 1024,
                'status': proc.status()
            }
        except:
            return None
    
    def add_log(self, bot_id, message, log_type='info'):
        """បន្ថែម log ទៅ database"""
        log = BotLog(
            bot_id=bot_id,
            message=message,
            log_type=log_type,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()

# Global instance
bot_manager = BotManager()
