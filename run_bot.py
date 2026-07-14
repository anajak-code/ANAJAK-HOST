import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import threading

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
# ដាក់ Token របស់អ្នកនៅទីនេះ ឬប្រើ Environment Variable
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE" 

# Global application instance
app_instance = None
is_bot_active = False

def start_telegram_bot():
    global app_instance, is_bot_active
    
    if is_bot_active:
        return

    try:
        # Create the Application and pass it your bot's token.
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Define command handlers
        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello! I am AHNAJAK-BOT running 24/7.")
            
        async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Commands:\n/start - Say Hello\n/help - Show Help")

        start_handler = CommandHandler('start', start)
        help_handler = CommandHandler('help', help_cmd)
        
        application.add_handler(start_handler)
        application.add_handler(help_handler)
        
        app_instance = application
        is_bot_active = True
        
        # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
        # We use run_polling() which blocks, so this must be called in a thread
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"Error starting bot: {e}")
        is_bot_active = False

def stop_telegram_bot():
    global app_instance, is_bot_active
    if app_instance and is_bot_active:
        try:
            app_instance.stop()
            is_bot_active = False
            print("Bot stopped.")
        except Exception as e:
            print(f"Error stopping bot: {e}")

def get_bot_status():
    if is_bot_active:
        return "Online 🟢"
    else:
        return "Offline 🔴"
