import logging
import requests
from bs4 import BeautifulSoup
import time
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Configuration ---
TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

APPS_TO_TRACK = {
    "WhatsApp": "https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/",
    "Telegram": "https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/",
    "Instagram": "https://www.apkmirror.com/apk/instagram/instagram/feed/",
    "Google Maps": "https://www.apkmirror.com/apk/google-inc/maps/feed/",
    "Gmail": "https://www.apkmirror.com/apk/google-inc/gmail/feed/",
    "YouTube": "https://www.apkmirror.com/apk/google-inc/youtube/feed/",
    "GBWhatsApp": "https://www.apkmirror.com/apk/gbwhatsapp/gbwhatsapp/feed/",
    "Waze": "https://www.apkmirror.com/apk/waze/waze-gps-maps-traffic-alerts-live-navigation/feed/",
    "Google Chrome": "https://www.apkmirror.com/apk/google-inc/chrome/feed/",
    "Viber": "https://www.apkmirror.com/apk/viber-media-s-a-r-l/viber/feed/",
    "TikTok": "https://www.apkmirror.com/apk/tiktok-pte-ltd/tiktok/feed/",
    "Spotify": "https://www.apkmirror.com/apk/spotify-ltd/spotify-music/feed/",
    "Netflix": "https://www.apkmirror.com/apk/netflix-inc/netflix/feed/",
    "Google Drive": "https://www.apkmirror.com/apk/google-inc/google-drive/feed/",
    "Google Photos": "https://www.apkmirror.com/apk/google-inc/google-photos/feed/",
    "Google Calendar": "https://www.apkmirror.com/apk/google-inc/google-calendar/feed/",
    "Google Docs": "https://www.apkmirror.com/apk/google-inc/google-docs/feed/",
    "Google Sheets": "https://www.apkmirror.com/apk/google-inc/google-sheets/feed/",
    "Google Slides": "https://www.apkmirror.com/apk/google-inc/google-slides/feed/",
    "Google Keep": "https://www.apkmirror.com/apk/google-inc/google-keep-notes-and-lists/feed/",
    "Google News": "https://www.apkmirror.com/apk/google-inc/google-news/feed/",
    "Google Translate": "https://www.apkmirror.com/apk/google-inc/google-translate/feed/",
    "Google Assistant": "https://www.apkmirror.com/apk/google-inc/google-assistant/feed/",
}

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- In-memory cache for seen versions ---
seen_versions = {app: "" for app in APPS_TO_TRACK}

# --- Bot Functions ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends an explanation of what the bot does."""
    await update.message.reply_text("היי! אני בוט שעוקב אחר עדכונים לאפליקציות. אני אשלח הודעה בכל פעם שתצא גרסה חדשה.")

async def check_for_updates(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check for new app versions and send a notification."""
    global seen_versions
    job = context.job
    
    for app_name, rss_url in APPS_TO_TRACK.items():
        try:
            response = requests.get(rss_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "xml")
            
            latest_item = soup.find("item")
            if latest_item:
                latest_version_title = latest_item.find("title").text
                
                # Simple check to see if the title changed
                if seen_versions.get(app_name) != latest_version_title:
                    logger.info(f"New version found for {app_name}: {latest_version_title}")
                    
                    # Update cache first to prevent duplicate messages
                    seen_versions[app_name] = latest_version_title
                    
                    # Construct and send message
                    link = latest_item.find("link").text
                    message = f"📢 **עדכון חדש זמין!**\n\n**אפליקציה:** {app_name}\n**גרסה:** {latest_version_title}\n\n[הורדה מאתר APKMirror]({link})"
                    await context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
                else:
                    logger.info(f"No new version for {app_name}. Current is {latest_version_title}")
            
            time.sleep(2) # Be nice to the server

        except requests.RequestException as e:
            logger.error(f"Could not fetch update for {app_name}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred for {app_name}: {e}")

def run_bot():
    """Starts the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()
    logger.info("Bot is starting...")

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))

    # Add job to the queue
    application.job_queue.run_repeating(check_for_updates, interval=900, first=10) # 900 seconds = 15 minutes

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot has started successfully.")


if __name__ == "__main__":
    run_bot()

