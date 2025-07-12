import logging
import requests
from bs4 import BeautifulSoup
import time
import os
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, ContextTypes, CommandHandler, CallbackQueryHandler
from flask import Flask, request
from telegram.error import Forbidden, BadRequest
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
    "WhatsApp": {"rss": "https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/", "package": "com.whatsapp"},
    "Telegram": {"rss": "https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/", "package": "org.telegram.messenger"},
    "Gemini": {"rss": "https://www.apkmirror.com/apk/google-inc/google-gemini/feed/", "package": "com.google.android.apps.bard"},
    "X (Twitter)": {"rss": "https://www.apkmirror.com/apk/twitter-inc/twitter/feed/", "package": "com.twitter.android"},
    "Google Keep": {"rss": "https://www.apkmirror.com/apk/google-inc/keep/feed/", "package": "com.google.android.keep"},
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
        text, action = (f"✅ {app_name}", "remove") if app_name in subscribed_apps else (f"➕ {app_name}", "add")
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
    await query.answer()
    action, app_name, page_str = query.data.split(':', 2)
    page = int(page_str)
    chat_id = update.effective_chat.id
    if action == "add":
        user_collection.update_one({"chat_id": chat_id}, {"$addToSet": {"subscribed_apps": app_name}})
    elif action == "remove":
        user_collection.update_one({"chat_id": chat_id}, {"$pull": {"subscribed_apps": app_name}})
    keyboard = build_app_menu(chat_id, page)
    try:
        await query.edit_message_reply_markup(reply_markup=keyboard)
    except BadRequest:
        pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)

async def check_for_updates(app: Application):
    global seen_versions
    logger.info("Running scheduled update check...")
    for app_name, app_data in APPS_TO_TRACK.items():
        rss_url, package_name = app_data["rss"], app_data["package"]
        try:
            response = requests.get(rss_url, headers=REQUEST_HEADER, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "xml")
            latest_item = soup.find("item")
            if not latest_item: continue
            latest_version_title = latest_item.find("title").text
            if "beta" in latest_version_title.lower(): continue
            if seen_versions.get(app_name) != latest_version_title:
                logger.info(f"New version for {app_name}: {latest_version_title}")
                seen_versions[app_name] = latest_version_title
                subscribers = list(user_collection.find({"subscribed_apps": app_name}))
                if not subscribers: continue
                play_store_link = f"https://play.google.com/store/apps/details?id={package_name}"
                changelog = ""
                try:
                    page_res = requests.get(latest_item.find("link").text, headers=REQUEST_HEADER, timeout=15)
                    page_soup = BeautifulSoup(page_res.content, "html.parser")
                    whats_new_div = page_soup.find("div", class_="notes")
                    if whats_new_div:
                        changelog = "\n\n📋 **מה חדש:**\n" + whats_new_div.get_text(separator='\n', strip=True)
                except Exception as page_e:
                    logger.warning(f"Could not scrape changelog for {app_name}: {page_e}")
                message = f"📢 **עדכון חדש זמין!**\n\n**אפליקציה:** {app_name}\n**גרסה:** {latest_version_title}{changelog}\n\n[פתח בחנות Play]({play_store_link})"
                for user in subscribers:
                    try:
                        await app.bot.send_message(chat_id=user['chat_id'], text=message, parse_mode='Markdown')
                    except (Forbidden, BadRequest):
                        user_collection.update_one({"chat_id": user['chat_id']}, {"$pull": {"subscribed_apps": app_name}})
        except Exception as e:
            logger.error(f"Error checking {app_name}: {e}")
        time.sleep(1)

# --- Flask Endpoints for Webhook and Cron ---
@flask_app.route(f"/{TOKEN}", methods=["POST"])
def respond():
    """Endpoint to receive updates from Telegram."""
    try:
        update = Update.de_json(request.get_json(force=True), ptb_app.bot)
        # The ptb_app runs its own asyncio loop management
        asyncio.run(ptb_app.process_update(update))
    except Exception as e:
        logger.error(f"Error processing update: {e}")
    return "ok"

@flask_app.route("/trigger-update-check")
def trigger_update_check():
    """Secret endpoint for the external cron job."""
    if request.args.get("secret") == SECRET_KEY:
        asyncio.run(check_for_updates(ptb_app))
        return "Update check triggered."
    return "Unauthorized", 401

# --- PTB Handlers ---
ptb_app.add_error_handler(error_handler)
ptb_app.add_handler(CommandHandler("start", start_command))
ptb_app.add_handler(CallbackQueryHandler(navigation_callback, pattern="^nav:"))
ptb_app.add_handler(CallbackQueryHandler(toggle_subscription_callback, pattern="^(add|remove):"))

# This block is for local testing only. Render uses the Gunicorn start command.
if __name__ == "__main__":
    flask_app.run(debug=True, port=5000)
