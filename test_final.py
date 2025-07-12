import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

# Basic logging to see what's happening
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A simple command that replies when /start is sent."""
    await update.message.reply_text("Minimal test bot is running correctly!")

def main():
    """Starts the minimal bot."""
    if not TOKEN:
        logging.error("BOT_TOKEN environment variable not found!")
        return

    logging.info("Starting minimal test bot...")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    logging.info("Running polling...")
    # This will run the bot and block here
    application.run_polling()
    

if __name__ == "__main__":
    main()
