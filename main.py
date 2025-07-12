   python
import asyncio
import nest_asyncio
from fastapi import FastAPI
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from pymongo import MongoClient
import certifi
import os

# Apply nest_asyncio for Render compatibility
nest_asyncio.apply()

# Initialize FastAPI for Render health checks
app = FastAPI()

# Get environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Set in Render environment variables
MONGO_URI = os.getenv("MONGO_URI")  # Set in Render environment variables

# MongoDB Connection
try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=30000)
    db = client["muminAI"]  # Replace with your database name
    # Test connection
    client.admin.command("ping")
    print("MongoDB connection successful!")
except Exception as e:
    print(f"MongoDB connection failed: {e}")

# Define command handlers
async def start(update: Update, context):
    await update.message.reply_text("Hello! I'm your App Update Bot. Try /help for more commands.")

async def help_command(update: Update, context):
    await update.message.reply_text("Available commands:\n/start - Start the bot\n/help - Show this message")

async def echo(update: Update, context):
    await update.message.reply_text(f"You said: {update.message.text}")

# FastAPI routes for Render
@app.get("/")
async def root():
    return {"status": "ok"}

@app.head("/")
async def head():
    return {}

# Main function to run the bot
async def main():
    # Initialize the bot application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot with polling
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
```
