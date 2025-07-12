import logging
import requests
from bs4 import BeautifulSoup
import time
import os
import asyncio # <-- Import asyncio
from telegram import Update
from telegram.error import Forbidden
from telegram.ext import Application, CommandHandler, ContextTypes
import pymongo

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Configuration ---
TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")

# --- Database Setup ---
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client.get_database("AppUpdateBotDB")
    user_collection = db.get_collection("users")
    user_collection.create_index("chat_id", unique=True)
    logger.info("Successfully connected to MongoDB.")
except Exception as e:
    logger.error(f"Could not connect to MongoDB: {e}")
    exit()

APPS_TO_TRACK = {
    "WhatsApp": "https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/",
    "Telegram": "https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/",
    "Instagram": "https://www.apkmirror.com/apk/instagram/instagram/feed/",
}

# --- In-memory cache for seen versions ---
seen_versions = {app: "" for app in APPS_TO_TRACK}

# --- Bot Functions ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    try:
        user_collection.update_one({"chat_id": chat_id}, {"$set": {"chat_id": chat_id}}, upsert=True)
        await update.message.reply_text("נרשמת בהצלחה! 🔔\nאני אשלח לך הודעה אישית בכל פעם שאמצא עדכון חדש.\nכדי לבטל את הרישום, השתמש בפקודה /stop.")
        logger.info(f"User {chat_id} subscribed.")
    except Exception as e:
        logger.error(f"Failed to add user {chat_id} to DB: {e}")
        await update.message.reply_text("אירעה שגיאה ברישום. נסה שוב מאוחר יותר.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    try:
        result = user_collection.delete_one({"chat_id": chat_id})
        if result.deleted_count > 0:
            await update.message.reply_text("הרישום שלך בוטל. 🔕\nלא תקבל יותר עדכונים. כדי להירשם מחדש, השתמש בפקודה /start.")
            logger.info(f"User {chat_id} unsubscribed.")
        else:
            await update.message.reply_text("לא היית רשום.")
    except Exception as e:
        logger.error(f"Failed to remove user {chat_id} from DB: {e}")
        await update.message.reply_text("אירעה שגיאה בביטול הרישום.")

async def check_for_updates(context: ContextTypes.DEFAULT_TYPE) -> None:
    global seen_versions
    subscribers = list(user_collection.find({}, {"_id": 0, "chat_id": 1}))
    if not subscribers:
        logger.info("No subscribers to notify. Skipping check.")
        return

    for app_name, rss_url in APPS_TO_TRACK.items():
        try:
            response = requests.get(rss_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "xml")
            latest_item = soup.find("item")
            if latest_item:
                latest_version_title = latest_item.find("title").text
                if seen_versions.get(app_name) != latest_version_title:
                    logger.info(f"New version found for {app_name}: {latest_version_title}")
                    seen_versions[app_name] = latest_version_title
                    link = latest_item.find("link").text
                    message = f"📢 **עדכון חדש זמין!**\n\n**אפליקציה:** {app_name}\n**גרסה:** {latest_version_title}\n\n[הורדה מאתר APKMirror]({link})"
                    for user in subscribers:
                        chat_id = user['chat_id']
                        try:
                            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                        except Forbidden:
                            logger.warning(f"User {chat_id} has blocked the bot. Removing from database.")
                            user_collection.delete_one({"chat_id": chat_id})
                        except Exception as e:
                            logger.error(f"Failed to send message to {chat_id}: {e}")
            time.sleep(2)
        except requests.RequestException as e:
            logger.error(f"Could not fetch update for {app_name}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred for {app_name}: {e}")

def run_bot():
    """Starts the bot."""
    # Create and set a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    application = Application.builder().token(TOKEN).build()
    logger.info("Bot is starting in personal mode...")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.job_queue.run_repeating(check_for_updates, interval=900, first=10)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    run_bot()
