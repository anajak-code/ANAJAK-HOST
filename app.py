import os
import sys
import threading
import time
import subprocess
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Allow requests from your Vercel Frontend
CORS(app, resources={r"/api/*": {"origins": "https://forest-smp-test.vercel.app"}})

# Global variables to manage the bot process
bot_process = None
is_running = False
bot_logs = []

def add_log(message):
    global bot_logs
    timestamp = time.strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    bot_logs.append(log_entry)
    # Keep only last 100 logs
    if len(bot_logs) > 100:
        bot_logs = bot_logs[-100:]
    print(log_entry)

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "running": is_running,
        "logs": "\n".join(bot_logs)
    })

@app.route('/api/run', methods=['POST'])
def run_bot():
    global bot_process, is_running
    
    if is_running:
        return jsonify({"status": "error", "message": "Bot is already running. Please stop it first."})
    
    data = request.json
    bot_token = data.get('token')
    bot_code = data.get('code')
    
    if not bot_token or not bot_code:
        return jsonify({"status": "error", "message": "Token and Code are required."})

    try:
        filename = "user_bot_script.py"
        
        # 1. Inject Token into code
        setup_code = f"""
import os
os.environ['BOT_TOKEN'] = '{bot_token}'
# Force output to appear immediately
import sys
sys.stdout.reconfigure(line_buffering=True)
"""
        full_code = setup_code + "\n" + bot_code
        
        with open(filename, "w") as f:
            f.write(full_code)
            
        add_log("Saving user code...")
        
        # 2. IMPORTANT: Install dependencies automatically before running
        # This ensures python-telegram-bot is available even on Render Free tier
        add_log("Installing required libraries (python-telegram-bot)...")
        install_proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "python-telegram-bot", "requests"],
            capture_output=True, text=True
        )
        
        if install_proc.returncode != 0:
            add_log(f"Installation Warning: {install_proc.stderr}")
        else:
            add_log("Libraries installed/updated successfully.")

        # 3. Start the bot process
        bot_process = subprocess.Popen(
            [sys.executable, filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Combine stderr into stdout so we see errors in logs
            text=True,
            bufsize=1 # Line buffered
        )
        
        is_running = True
        add_log("Bot process started.")
        
        # Start a thread to read logs
        log_thread = threading.Thread(target=read_bot_logs, args=(bot_process,))
        log_thread.daemon = True
        log_thread.start()
        
        return jsonify({"status": "success", "message": "Bot is starting..."})

    except Exception as e:
        add_log(f"CRITICAL ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    global bot_process, is_running
    
    if not is_running:
        return jsonify({"status": "error", "message": "No bot is currently running."})
        
    try:
        if bot_process:
            bot_process.terminate()
            try:
                bot_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                bot_process.kill()
            add_log("Bot process terminated by user.")
        
        is_running = False
        bot_process = None
        
        if os.path.exists("user_bot_script.py"):
            os.remove("user_bot_script.py")
            
        return jsonify({"status": "success", "message": "Bot stopped."})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

def read_bot_logs(process):
    """Read output from the bot process line by line"""
    try:
        while process.poll() is None:
            line = process.stdout.readline()
            if line:
                add_log(line.strip())
            else:
                break # EOF
    except Exception as e:
        add_log(f"Log reader error: {e}")
    
    # Process finished
    global is_running
    is_running = False
    add_log("Bot process ended unexpectedly or completed.")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
