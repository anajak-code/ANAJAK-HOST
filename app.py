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
    # Keep only last 50 logs
    if len(bot_logs) > 50:
        bot_logs = bot_logs[-50:]
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
        # Create a temporary file for the user's code
        # We inject the token into the code environment or replace a placeholder
        filename = "user_bot_script.py"
        
        # Security Note: In a real production app, never execute raw user code like this.
        # Here we save it to a file and run it.
        with open(filename, "w") as f:
            # We prepend some setup code to ensure the token is available
            setup_code = f"""
import os
os.environ['BOT_TOKEN'] = '{bot_token}'
"""
            f.write(setup_code + "\n" + bot_code)
            
        add_log("Saving user code...")
        
        # Start the bot in a separate process
        # Using subprocess allows us to kill it later if needed
        bot_process = subprocess.Popen(
            [sys.executable, filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        is_running = True
        add_log("Bot process started.")
        
        # Start a thread to read logs from the subprocess
        log_thread = threading.Thread(target=read_bot_logs, args=(bot_process,))
        log_thread.daemon = True
        log_thread.start()
        
        return jsonify({"status": "success", "message": "Bot is starting..."})

    except Exception as e:
        add_log(f"Error starting bot: {str(e)}")
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
            add_log("Bot process terminated.")
        
        is_running = False
        bot_process = None
        
        # Clean up the temporary file
        if os.path.exists("user_bot_script.py"):
            os.remove("user_bot_script.py")
            add_log("Temporary script removed.")
            
        return jsonify({"status": "success", "message": "Bot stopped."})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

def read_bot_logs(process):
    """Read stdout and stderr from the bot process"""
    while process.poll() is None: # While process is running
        output = process.stdout.readline()
        error = process.stderr.readline()
        
        if output:
            add_log(output.strip())
        if error:
            add_log(f"ERROR: {error.strip()}")
            
    # Process finished
    global is_running
    is_running = False
    add_log("Bot process ended.")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
