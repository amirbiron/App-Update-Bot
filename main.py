import logging
import requests
from bs4 import BeautifulSoup
import time
import os
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, ContextTypes, CommandHandler, CallbackQueryHandler
from flask import Flask, request
import pymongo
import math

# --- Setup ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration & Constants ---
TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")
SECRET_KEY = os.environ.get("CRON_SECRET_KEY")
APP_URL = os.environ.get("RENDER_APP_URL")

REQUEST_HEADER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
APPS_PER_PAGE = 8

APPS_TO_TRACK = {
    # Add your final list of apps here
    "WhatsApp": {"rss": "https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/", "package": "com.whatsapp"},
    "Telegram": {"rss": "https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/", "package": "org.telegram.messenger"},
    # ... etc
}
SORTED_APPS = sorted(APPS_TO_TRACK.keys())

# --- Database & App Initialization ---
client = pymongo.MongoClient(MONGO_URI)
db = client.get_database("AppUpdateBotDB")
user_collection = db.get_collection("users_v3")
user_collection.create_index("chat_id", unique=True)
seen_versions = {app: "" for app in APPS_TO_TRACK}

ptb_app = Application.builder().token(TOKEN).build()
flask_app = Flask(__name__)

# --- UI & Bot Logic Functions ---

def build_app_menu(chat_id, page):
    user_subs = user_collection.find_one({"chat_id": chat_id}, {"subscribed_apps": 1, "_id": 0})
    subscribed_apps = set(user_subs.get("subscribed_apps", []))
    buttons = []
    start_index = page * APPS_PER_PAGE
    end_index = start_index + APPS_PER_PAGE
    for app_name in SORTED_APPS[start_index:end_index]:
        if app_name in subscribed_apps:
            text, action = f"✅ {app_name}", "remove"
        else:
            text, action = f"➕ {app_name}", "add"
        buttons.append([InlineKeyboardButton(text, callback_data=f"{action}:{app_name}:{page}")])
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ הקודם", callback_data=f"nav:{page-1}"))
    if end_index < len(SORTED_APPS):
        nav_buttons.append(InlineKeyboardButton("הבא ➡️", callback_data=f"nav:{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    return InlineKeyboardMarkup(buttons)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_collection.update_one({"chat_id": chat_id}, {"$setOnInsert": {"chat_id": chat_id, "subscribed_apps": []}}, upsert=True)
    await update.message.reply_text(
        "**ברוך הבא לבוט עדכוני האפליקציות!** 🤖\n\n"
        "לחץ על הכפתור כדי להתחיל לנהל את רשימת ההתראות האישית שלך:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📱 ניהול התראות", callback_data="nav:0")]])
    )

async def navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(':')[1])
    keyboard = build_app_menu(update.effective_chat.id, page)
    await query.edit_message_text("בחר אפליקציות למעקב. ✅ מסמן שאתה רשום, ➕ מסמן שאינך רשום.", reply_markup=keyboard)

async def toggle_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, app_name, page_str = query.data.split(':', 2)
    page = int(page_str)
    chat_id = update.effective_chat.id
    if action == "add":
        user_collection.update_one({"chat_id": chat_id}, {"$addToSet": {"subscribed_apps": app_name}})
        await query.answer(text=f"✅ הוספת את {app_name} למעקב!")
    elif action == "remove":
        user_collection.update_one({"chat_id": chat_id}, {"$pull": {"subscribed_apps": app_name}})
        await query.answer(text=f"❌ הסרת את {app_name} מהמעקב!")
    keyboard = build_app_menu(chat_id, page)
    await query.edit_message_reply_markup(reply_markup=keyboard)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)

async def check_for_updates(app: Application):
    global seen_versions
    # (The logic for this function is long, assuming it's correct from previous versions)
    # This is a placeholder, ensure the full logic is here
    logger.info("Running scheduled update check...")
    # ... Full check_for_updates logic goes here ...
    pass

# --- Flask Endpoints for Webhook and Cron ---
@flask_app.route(f"/{TOKEN}", methods=["POST"])
def respond():
    update = Update.de_json(request.get_json(force=True), ptb_app.bot)
    asyncio.run(ptb_app.process_update(update))
    return "ok"

@flask_app.route("/trigger-update-check")
def trigger_update_check():
    if request.args.get("secret") == SECRET_KEY:
        asyncio.run(check_for_updates(ptb_app))
        return "Update check triggered."
    return "Unauthorized", 401

# --- PTB Handlers ---
ptb_app.add_error_handler(error_handler)
ptb_app.add_handler(CommandHandler("start", start_command))
ptb_app.add_handler(CallbackQueryHandler(navigation_callback, pattern="^nav:"))
ptb_app.add_handler(CallbackQueryHandler(toggle_subscription_callback, pattern="^(add|remove):"))
