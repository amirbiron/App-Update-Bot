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

# --- App Database with Package Names ---
# The data structure now includes the app's package name for Google Play links
APPS_TO_TRACK = {
    "WhatsApp": {"rss": "https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/", "package": "com.whatsapp"},
    "Telegram": {"rss": "https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/", "package": "org.telegram.messenger"},
    "Instagram": {"rss": "https://www.apkmirror.com/apk/instagram/instagram/feed/", "package": "com.instagram.android"},
    "Facebook": {"rss": "https://www.apkmirror.com/apk/facebook-2/facebook/feed/", "package": "com.facebook.katana"},
    "X (Twitter)": {"rss": "https://www.apkmirror.com/apk/twitter-inc/x/feed/", "package": "com.twitter.android"},
    "TikTok": {"rss": "https://www.apkmirror.com/apk/tiktok-pte-ltd/tiktok/feed/", "package": "com.zhiliaoapp.musically"},
    "Google Chrome": {"rss": "https://www.apkmirror.com/apk/google-inc/chrome/feed/", "package": "com.android.chrome"},
    "Waze": {"rss": "https://www.apkmirror.com/apk/waze/waze-gps-maps-traffic-alerts-live-navigation/feed/", "package": "com.waze"},
    "YouTube": {"rss": "https://www.apkmirror.com/apk/google-inc/youtube/feed/", "package": "com.google.android.youtube"},
    "Spotify": {"rss": "https://www.apkmirror.com/apk/spotify-ltd/spotify-music/feed/", "package": "com.spotify.music"},
    "Netflix": {"rss": "https://www.apkmirror.com/apk/netflix-inc/netflix/feed/", "package": "com.netflix.mediaclient"},
}
SORTED_APPS = sorted(APPS_TO_TRACK.keys())

# --- Database Setup ---
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client.get_database("AppUpdateBotDB")
    user_collection = db.get_collection("users_v2")
    user_collection.create_index("chat_id", unique=True)
    logger.info("Successfully connected to MongoDB.")
except Exception as e:
    logger.error(f"Could not connect to MongoDB: {e}")
    exit()

# --- In-memory cache ---
seen_versions = {app: "" for app in APPS_TO_TRACK}

# --- UI & Bot Logic ---
# (Functions from previous steps like build_app_menu, get_main_menu, start_command, etc. remain here)
# For brevity, only the modified `check_for_updates` function is shown here.
# The full code block below contains the complete, final file.
# --- (The rest of the helper and command functions are in the full block below) ---

# --- Helper Functions for UI (Unchanged) ---
def build_app_menu(app_list, page, action_prefix):
    buttons = []
    start_index = page * APPS_PER_PAGE
    end_index = start_index + APPS_PER_PAGE
    for app_name in app_list[start_index:end_index]:
        buttons.append([InlineKeyboardButton(app_name, callback_data=f"{action_prefix}:{app_name}")])
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ הקודם", callback_data=f"nav_{action_prefix}:{page-1}"))
    if end_index < len(app_list):
        nav_buttons.append(InlineKeyboardButton("הבא ➡️", callback_data=f"nav_{action_prefix}:{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton("🔙 חזרה לתפריט הראשי", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("➕ הוספת התראה", callback_data="add_app_menu")],
        [InlineKeyboardButton("➖ הסרת התראה", callback_data="remove_app_menu")],
        [InlineKeyboardButton("📋 ההתראות שלי", callback_data="my_subscriptions")],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Command & Callback Handlers (Unchanged, except start_command) ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_collection.update_one({"chat_id": chat_id}, {"$setOnInsert": {"chat_id": chat_id, "subscribed_apps": []}}, upsert=True)
    await update.message.reply_text(
        "ברוך הבא לבוט עדכוני האפליקציות! 🤖\n\n"
        "תוכל לבחור לקבל התראות אישיות עבור האפליקציות שמעניינות אותך.\n"
        "השתמש בתפריט כדי להתחיל:",
        reply_markup=get_main_menu()
    )
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("תפריט ראשי:", reply_markup=get_main_menu())
async def my_subscriptions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = user_collection.find_one({"chat_id": update.effective_chat.id})
    if user and user.get("subscribed_apps"):
        apps_str = "\n- ".join(sorted(user["subscribed_apps"]))
        message = f"אתה רשום להתראות עבור האפליקציות הבאות:\n- {apps_str}"
    else:
        message = "אינך רשום להתראות כלל."
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="main_menu")]]))
async def navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, page_str = query.data.split(':')
    page = int(page_str)
    menu_type = action.split('_')[1]
    if menu_type == "add":
        keyboard = build_app_menu(SORTED_APPS, page, "add")
        await query.edit_message_text("בחר אפליקציה להוספה:", reply_markup=keyboard)
    elif menu_type == "remove":
        user = user_collection.find_one({"chat_id": update.effective_chat.id})
        user_apps = sorted(user.get("subscribed_apps", []))
        keyboard = build_app_menu(user_apps, page, "remove")
        await query.edit_message_text("בחר אפליקציה להסרה:", reply_markup=keyboard)
async def add_remove_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "add_app_menu":
        keyboard = build_app_menu(SORTED_APPS, 0, "add")
        await query.edit_message_text("בחר אפליקציה כדי לקבל עליה עדכונים:", reply_markup=keyboard)
    elif query.data == "remove_app_menu":
        user = user_collection.find_one({"chat_id": update.effective_chat.id})
        user_apps = sorted(user.get("subscribed_apps", []))
        if not user_apps:
            await query.edit_message_text("אינך רשום לאף אפליקציה.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="main_menu")]]))
            return
        keyboard = build_app_menu(user_apps, 0, "remove")
        await query.edit_message_text("בחר אפליקציה להפסקת העדכונים:", reply_markup=keyboard)
async def add_remove_app_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, app_name = query.data.split(':', 1)
    chat_id = update.effective_chat.id
    if action == "add":
        user_collection.update_one({"chat_id": chat_id}, {"$addToSet": {"subscribed_apps": app_name}})
        await query.answer(text=f"✅ הוספת את {app_name} לרשימה!")
    elif action == "remove":
        user_collection.update_one({"chat_id": chat_id}, {"$pull": {"subscribed_apps": app_name}})
        await query.answer(text=f"❌ הסרת את {app_name} מהרשימה!")
    current_page = 0
    if query.message.reply_markup:
        for row in query.message.reply_markup.inline_keyboard:
            for button in row:
                if "nav_" in button.callback_data:
                    current_page = int(button.callback_data.split(":")[-1])
                    break
    if action == "add":
        await query.edit_message_reply_markup(reply_markup=build_app_menu(SORTED_APPS, current_page, "add"))
    elif action == "remove":
        user = user_collection.find_one({"chat_id": chat_id})
        user_apps = sorted(user.get("subscribed_apps", []))
        if not user_apps:
            await query.edit_message_text("לא נותרו אפליקציות ברשימה שלך.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="main_menu")]]))
        else:
            max_page = math.ceil(len(user_apps) / APPS_PER_PAGE) - 1
            current_page = min(current_page, max_page)
            await query.edit_message_reply_markup(reply_markup=build_app_menu(user_apps, current_page, "remove"))

# --- Background Job (Modified) ---
async def check_for_updates(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks for app updates, tries to find changelog, and notifies relevant users."""
    global seen_versions
    for app_name, app_data in APPS_TO_TRACK.items():
        rss_url = app_data["rss"]
        package_name = app_data["package"]
        try:
            response = requests.get(rss_url, headers=REQUEST_HEADER, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "xml")
            
            latest_item = soup.find("item")
            if not latest_item:
                continue
                
            latest_version_title = latest_item.find("title").text
            
            # **NEW**: Skip beta versions
            if "beta" in latest_version_title.lower():
                logger.info(f"Skipping beta version for {app_name}: {latest_version_title}")
                continue

            if seen_versions.get(app_name) != latest_version_title:
                logger.info(f"New version found for {app_name}: {latest_version_title}")
                seen_versions[app_name] = latest_version_title
                
                subscribers = list(user_collection.find({"subscribed_apps": app_name}))
                if not subscribers:
                    continue

                # **NEW**: Change link to Google Play
                play_store_link = f"https://play.google.com/store/apps/details?id={package_name}"
                
                # **NEW**: Try to scrape the changelog from the APKMirror page
                page_link = latest_item.find("link").text
                changelog = ""
                try:
                    page_res = requests.get(page_link, headers=REQUEST_HEADER, timeout=15)
                    page_soup = BeautifulSoup(page_res.content, "html.parser")
                    # This selector targets the "What's New" section on APKMirror
                    whats_new_div = page_soup.find("div", class_="notes")
                    if whats_new_div:
                        changelog = "\n\n📋 **מה חדש:**\n" + whats_new_div.get_text(separator='\n', strip=True)
                except Exception as page_e:
                    logger.warning(f"Could not scrape changelog for {app_name}: {page_e}")

                message = (
                    f"📢 **עדכון חדש זמין!**\n\n"
                    f"**אפליקציה:** {app_name}\n"
                    f"**גרסה:** {latest_version_title}"
                    f"{changelog}\n\n"  # Add changelog if found
                    f"[פתח בחנות Play]({play_store_link})"
                )
                
                for user in subscribers:
                    chat_id = user['chat_id']
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                    except (Forbidden, BadRequest):
                        logger.warning(f"User {chat_id} blocked or unreachable. Removing.")
                        user_collection.update_one({"chat_id": chat_id}, {"$pull": {"subscribed_apps": app_name}})
                    except Exception as e:
                        logger.error(f"Failed to send message to {chat_id}: {e}")
            time.sleep(1)
        except requests.RequestException as e:
            logger.error(f"Could not fetch update for {app_name}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while checking {app_name}: {e}")

# --- Main Bot Runner (Unchanged) ---
def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    application = Application.builder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(my_subscriptions_callback, pattern="^my_subscriptions$"))
    application.add_handler(CallbackQueryHandler(add_remove_menu_callback, pattern="^(add|remove)_app_menu$"))
    application.add_handler(CallbackQueryHandler(navigation_callback, pattern="^nav_"))
    application.add_handler(CallbackQueryHandler(add_remove_app_callback, pattern="^(add|remove):"))
    
    application.job_queue.run_repeating(check_for_updates, interval=900, first=10)
    
    logger.info("Bot is starting with final features...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)

if __name__ == "__main__":
    run_bot()

