import logging
import requests
from bs4 import BeautifulSoup
import time
import os
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import Forbidden, BadRequest
import pymongo
import math
import http.server
import socketserver
import threading

# --- Basic Setup ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration & Constants ---
TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")
PORT = 8080 # Port for the keep-alive server

if not all([TOKEN, MONGO_URI]):
    logger.error("FATAL: Missing BOT_TOKEN or MONGO_URI environment variables!")
    exit()

REQUEST_HEADER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"}
APPS_PER_PAGE = 8
APPS_TO_TRACK = {
    "WhatsApp": {"rss": "https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/", "package": "com.whatsapp"},
    "Telegram": {"rss": "https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/", "package": "org.telegram.messenger"},
    "Gemini": {"rss": "https://www.apkmirror.com/apk/google-inc/google-gemini/feed/", "package": "com.google.android.apps.bard"},
    "X (Twitter)": {"rss": "https://www.apkmirror.com/apk/twitter-inc/twitter/feed/", "package": "com.twitter.android"},
    "Google Keep": {"rss": "https://www.apkmirror.com/apk/google-inc/keep/feed/", "package": "com.google.android.keep"},
}
SORTED_APPS = sorted(APPS_TO_TRACK.keys())

# --- Database Setup ---
client = pymongo.MongoClient(MONGO_URI)
db = client.get_database("AppUpdateBotDB")
user_collection = db.get_collection("users_v3")
user_collection.create_index("chat_id", unique=True)
seen_versions = {app: "" for app in APPS_TO_TRACK}

# --- Keep-Alive Web Server ---
def run_keep_alive_server():
    """Runs a simple HTTP server in a background thread to keep the service alive."""
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        logger.info(f"Keep-alive server started on port {PORT}")
        httpd.serve_forever()

# --- UI & Bot Logic ---
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
    if page > 0: nav_buttons.append(InlineKeyboardButton("⬅️ הקודם", callback_data=f"nav:{page-1}"))
    if end_index < len(SORTED_APPS): nav_buttons.append(InlineKeyboardButton("הבא ➡️", callback_data=f"nav:{page+1}"))
    if nav_buttons: buttons.append(nav_buttons)
    return InlineKeyboardMarkup(buttons)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_collection.update_one({"chat_id": chat_id}, {"$setOnInsert": {"chat_id": chat_id, "subscribed_apps": []}}, upsert=True)
    await update.message.reply_text(
        "**ברוך הבא לבוט עדכוני האפליקציות!** 🤖\n\nלחץ על הכפתור כדי לנהל את רשימת ההתראות שלך:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📱 ניהול התראות", callback_data="nav:0")]])
    )

async def navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(':')[1])
    keyboard = build_app_menu(update.effective_chat.id, page)
    await query.edit_message_text("בחר אפליקציות למעקב:", reply_markup=keyboard)

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
    except BadRequest: pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)

async def check_for_updates(context: ContextTypes.DEFAULT_TYPE):
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
                message = f"📢 עדכון חדש זמין!\n\n**אפליקציה:** {app_name}\n**גרסה:** {latest_version_title}\n\n[פתח בחנות Play]({play_store_link})"
                for user in subscribers:
                    try:
                        await context.bot.send_message(chat_id=user['chat_id'], text=message, parse_mode='Markdown')
                    except (Forbidden, BadRequest):
                        user_collection.update_one({"chat_id": user['chat_id']}, {"$pull": {"subscribed_apps": app_name}})
        except Exception as e:
            logger.error(f"Error checking {app_name}: {e}")
        time.sleep(1)

# --- Main Application Runner ---
def main():
    """Start the bot."""
    # Start the keep-alive server in a separate thread
    keep_alive_thread = threading.Thread(target=run_keep_alive_server)
    keep_alive_thread.daemon = True
    keep_alive_thread.start()

    # Create and configure the Telegram bot application
    application = Application.builder().token(TOKEN).build()
    
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(navigation_callback, pattern="^nav:"))
    application.add_handler(CallbackQueryHandler(toggle_subscription_callback, pattern="^(add|remove):"))
    
    # Add the job to check for updates
    application.job_queue.run_repeating(check_for_updates, interval=900, first=10)
    
    logger.info("Bot starting with Polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
