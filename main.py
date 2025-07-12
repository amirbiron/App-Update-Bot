import logging
import requests
from bs4 import BeautifulSoup
import time
import os
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import Forbidden, BadRequest
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import pymongo
import math

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Configuration & Constants ---
TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")
REQUEST_HEADER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
APPS_PER_PAGE = 8

# --- App Database (Updated List) ---
APPS_TO_TRACK = {
    # Messengers
    "WhatsApp": {"rss": "https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/", "package": "com.whatsapp"},
    "Telegram": {"rss": "https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/", "package": "org.telegram.messenger"},
    "Signal": {"rss": "https://www.apkmirror.com/apk/signal-foundation/signal-private-messenger/feed/", "package": "org.thoughtcrime.securesms"},
    # AI Apps
    "Gemini": {"rss": "https://www.apkmirror.com/apk/google-inc/google-gemini/feed/", "package": "com.google.android.apps.bard"},
    "Claude": {"rss": "https://www.apkmirror.com/apk/anthropic/claude/feed/", "package": "com.anthropic.claude"},
    "Perplexity": {"rss": "https://www.apkmirror.com/apk/perplexity-ai/perplexity-ask-ai/feed/", "package": "ai.perplexity.app"},
    "ChatGPT": {"rss": "https://www.apkmirror.com/apk/openai/chatgpt/feed/", "package": "com.openai.chatgpt"},
    # Social Media
    "Instagram": {"rss": "https://www.apkmirror.com/apk/instagram/instagram/feed/", "package": "com.instagram.android"},
    "X (Twitter)": {"rss": "https://www.apkmirror.com/apk/twitter-inc/x/feed/", "package": "com.twitter.android"},
    "Reddit": {"rss": "https://www.apkmirror.com/apk/reddit-inc/reddit/feed/", "package": "com.reddit.frontpage"},
    # Browsers
    "Google Chrome": {"rss": "https://www.apkmirror.com/apk/google-inc/chrome/feed/", "package": "com.android.chrome"},
    # Productivity & Utilities
    "Google Drive": {"rss": "https://www.apkmirror.com/apk/google-inc/google-drive/feed/", "package": "com.google.android.apps.docs"},
    "Google Photos": {"rss": "https://www.apkmirror.com/apk/google-inc/google-photos/feed/", "package": "com.google.android.apps.photos"},
    "Google Keep": {"rss": "https://www.apkmirror.com/apk/google-inc/google-keep-notes-and-lists/feed/", "package": "com.google.android.keep"},
    "Waze": {"rss": "https://www.apkmirror.com/apk/waze/waze-gps-maps-traffic-alerts-live-navigation/feed/", "package": "com.waze"},
    "Notion": {"rss": "https://www.apkmirror.com/apk/notion-labs-inc/notion-notes-docs-tasks/feed/", "package": "notion.id"},
    "Slack": {"rss": "https://www.apkmirror.com/apk/slack-technologies-inc/slack/feed/", "package": "com.Slack"},
    "Spotify": {"rss": "https://www.apkmirror.com/apk/spotify-ltd/spotify-music/feed/", "package": "com.spotify.music"},
    "YouTube": {"rss": "https://www.apkmirror.com/apk/google-inc/youtube/feed/", "package": "com.google.android.youtube"},
}
SORTED_APPS = sorted(APPS_TO_TRACK.keys())

# --- Database Setup ---
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client.get_database("AppUpdateBotDB")
    user_collection = db.get_collection("users_v3") # Using a new collection for the final structure
    user_collection.create_index("chat_id", unique=True)
    logger.info("Successfully connected to MongoDB.")
except Exception as e:
    logger.error(f"Could not connect to MongoDB: {e}")
    exit()

# --- In-memory cache ---
seen_versions = {app: "" for app in APPS_TO_TRACK}

# --- UI Components ---
def build_app_menu(chat_id, page):
    """Builds the unified, stateful, and paginated menu of apps."""
    user_subs = user_collection.find_one({"chat_id": chat_id}, {"subscribed_apps": 1, "_id": 0})
    subscribed_apps = set(user_subs.get("subscribed_apps", []))
    
    buttons = []
    start_index = page * APPS_PER_PAGE
    end_index = start_index + APPS_PER_PAGE
    
    for app_name in SORTED_APPS[start_index:end_index]:
        if app_name in subscribed_apps:
            # User is subscribed - show ✅ and a 'remove' action
            text = f"✅ {app_name}"
            action = "remove"
        else:
            # User is not subscribed - show ➕ and an 'add' action
            text = f"➕ {app_name}"
            action = "add"
        
        button = InlineKeyboardButton(text, callback_data=f"{action}:{app_name}:{page}")
        buttons.append([button])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ הקודם", callback_data=f"nav:{page-1}"))
    if end_index < len(SORTED_APPS):
        nav_buttons.append(InlineKeyboardButton("הבא ➡️", callback_data=f"nav:{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
        
    return InlineKeyboardMarkup(buttons)

# --- Command & Callback Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Greets the user and shows the main menu."""
    chat_id = update.effective_chat.id
    user_collection.update_one({"chat_id": chat_id}, {"$setOnInsert": {"chat_id": chat_id, "subscribed_apps": []}}, upsert=True)
    
    await update.message.reply_text(
        "**ברוך הבא לבוט עדכוני האפליקציות!** 🤖\n\n"
        "אני סורק את הרשת ומאתר עדכוני גרסה משמעותיים (לא גרסאות בטא) לאפליקציות פופולריות.\n\n"
        "כשאמצא עדכון, אשלח לך התראה עם פירוט החידושים (במידה וזמין) וקישור ישיר לחנות ה-Play.\n\n"
        "לחץ על הכפתור כדי להתחיל לנהל את רשימת ההתראות האישית שלך:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📱 ניהול התראות", callback_data="nav:0")]])
    )

async def navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles app menu pagination."""
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(':')[1])
    
    keyboard = build_app_menu(update.effective_chat.id, page)
    try:
        await query.edit_message_text("בחר אפליקציות למעקב. ✅ מסמן שאתה רשום, ➕ מסמן שאינך רשום.", reply_markup=keyboard)
    except BadRequest:  # Ignore error if the message content hasn't changed
        pass

async def toggle_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds or removes an app from a user's subscription list and refreshes the menu."""
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

    # Refresh the menu to show the new state
    keyboard = build_app_menu(chat_id, page)
    try:
        await query.edit_message_reply_markup(reply_markup=keyboard)
    except BadRequest: # If the keyboard doesn't change, telegram might throw an error. Ignore it.
        pass

# --- Background Job ---
async def check_for_updates(context: ContextTypes.DEFAULT_TYPE) -> None:
    # This function's internal logic remains largely the same as the previous version
    global seen_versions
    for app_name, app_data in APPS_TO_TRACK.items():
        rss_url = app_data["rss"]
        package_name = app_data["package"]
        try:
            response = requests.get(rss_url, headers=REQUEST_HEADER, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "xml")
            
            latest_item = soup.find("item")
            if not latest_item: continue
            
            latest_version_title = latest_item.find("title").text
            
            if "beta" in latest_version_title.lower(): continue

            if seen_versions.get(app_name) != latest_version_title:
                logger.info(f"New version found for {app_name}: {latest_version_title}")
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
                        await context.bot.send_message(chat_id=user['chat_id'], text=message, parse_mode='Markdown')
                    except (Forbidden, BadRequest):
                        user_collection.update_one({"chat_id": user['chat_id']}, {"$pull": {"subscribed_apps": app_name}})
                    except Exception as e:
                        logger.error(f"Failed to send message to {user['chat_id']}: {e}")
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error checking {app_name}: {e}")

# --- Main Bot Runner ---
def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    application = Application.builder().token(TOKEN).build()
    
    # Handlers for the new UI
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(navigation_callback, pattern="^nav:"))
    application.add_handler(CallbackQueryHandler(toggle_subscription_callback, pattern="^(add|remove):"))
    
    application.job_queue.run_repeating(check_for_updates, interval=900, first=10)
    
    logger.info("Bot starting with unified toggle menu...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)

if __name__ == "__main__":
    run_bot()

