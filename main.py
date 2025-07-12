import asyncio
import nest_asyncio
from fastapi import FastAPI
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from pymongo import MongoClient
import certifi
import os
import os
print("PAT:", os.getenv("GITHUB_TOKEN"))  # הסר לאחר בדיקה

nest_asyncio.apply()
app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["muminAI"]

async def start(update: Update, context):
    await update.message.reply_text("Hello! Try /help.")

async def help_command(update: Update, context):
    await update.message.reply_text("Commands:\n/start\n/help")

@app.get("/")
async def root():
    return {"status": "ok"}

@app.head("/")
async def head():
    return {}

async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
