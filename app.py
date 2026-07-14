from flask import Flask, render_template, jsonify, request
import threading
import time
import os
from run_bot import start_telegram_bot, stop_telegram_bot, get_bot_status

app = Flask(__name__)

# Global variable to track bot thread
bot_thread = None
is_running = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_bot():
    global bot_thread, is_running
    
    if is_running:
        return jsonify({"status": "error", "message": "Bot is already running!"})
    
    try:
        # Start bot in a separate thread so it doesn't block the web server
        bot_thread = threading.Thread(target=start_telegram_bot)
        bot_thread.daemon = True
        bot_thread.start()
        is_running = True
        return jsonify({"status": "success", "message": "Bot started successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    global is_running
    
    if not is_running:
        return jsonify({"status": "error", "message": "Bot is not running."})
        
    try:
        stop_telegram_bot()
        is_running = False
        return jsonify({"status": "success", "message": "Bot stopped successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/status', methods=['GET'])
def status():
    current_status = get_bot_status()
    return jsonify({"running": is_running, "bot_status": current_status})

if __name__ == '__main__':
    # Run on port 5000 or environment port
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
