import asyncio
import nest_asyncio
from fastapi import FastAPI, Request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.error import TelegramError
from pymongo import MongoClient
import certifi
import os
import uvicorn

nest_asyncio.apply()
app = FastAPI()

TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client["muminAI"]
    print("MongoDB connected!")
except Exception as e:
    print(f"MongoDB error: {e}")

bot_app = Application.builder().token(TOKEN).build()

async def start(update: Update, context):
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("עזרה")],
         [KeyboardButton("עדכון אפליקציה")],
         [KeyboardButton("פקודה אחרת")]],
        resize_keyboard=True
    )
    message = "שלום! ברוך הבא לבוט. השתמש בכפתורים."
    await update.message.reply_text(message, reply_markup=keyboard)
    print("Sent start with buttons")

async def help_command(update: Update, context):
    await update.message.reply_text("זו /help: /start להתחלה, /update לעדכון.")

async def button_handler(update: Update, context):
    text = update.message.text
    if text == "עזרה":
        await update.message.reply_text("עזרה: הסבר על הבוט.")
    elif text == "עדכון אפליקציה":
        await update.message.reply_text("עדכון אפליקציה פה.")
    elif text == "פקודה אחרת":
        await update.message.reply_text("פקודה אחרת פה.")
    print("Button pressed: {text}")

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("help", help_command))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    json_data = await request.json()
    print("Received update:", json_data)
    update = Update.de_json(json_data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"status": "ok"}

@app.head("/")
async def head():
    return {}

async def main():
    await bot_app.initialize()
    print("⌛ מנסה להגדיר webhook...")
    retries = 3
    delay = 20
    for attempt in range(retries):
        try:
            await bot_app.bot.delete_webhook(drop_pending_updates=True)
            await bot_app.bot.set_webhook(WEBHOOK_URL)
            print("📡 webhook הוגדר בהצלחה!")
            break
        except TelegramError as e:
            print(f"⚠️ ניסיון {attempt+1} נכשל: {e}")
            await asyncio.sleep(delay)
    else:
        print("❌ נכשל אחרי ניסיונות.")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    asyncio.run(main())
