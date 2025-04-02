from telegram.ext import Application
from config import TELEGRAM_TOKEN
from modules.telegram_handler import setup_handlers

def main():
    """Main bot launch function"""
    print("Starting the bot...")
    
    # Clean temporary files at startup
    from modules.img_converter import clear_temp_files
    clear_temp_files()
    
    # Create an application instance
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Set up handlers
    setup_handlers(application)
    
    # Start the bot (simpler method)
    application.run_polling()
    
    print("Bot stopped.")

if __name__ == "__main__":
    main()
