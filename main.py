#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot for monitoring app updates with a MongoDB subscription system
"""

import os
import asyncio
import logging
from typing import Dict, Optional, Set

import feedparser
from telegram import Bot
from telegram.error import TelegramError, Forbidden
from telegram.ext import ApplicationBuilder, CommandHandler
from pymongo import MongoClient

# --- הגדרות ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- התחברות ל-MongoDB ---
MONGO_URI = os.getenv('MONGO_URI')
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set!")

client = MongoClient(MONGO_URI)
db = client['app_bot_db'] # שם מסד הנתונים
subscribers_collection = db['subscribers'] # שם האוסף (collection) שיחזיק את המנויים

# --- פונקציות לניהול מנויים מול מסד הנתונים ---

def get_all_subscribers() -> Set[int]:
    """שליפת כל מזהי המנויים ממסד הנתונים"""
    try:
        cursor = subscribers_collection.find({}, {'chat_id': 1, '_id': 0})
        return {item['chat_id'] for item in cursor}
    except Exception as e:
        logger.error(f"Error reading from MongoDB: {e}")
        return set()

def add_subscriber(chat_id: int):
    """הוספת מנוי חדש אם הוא לא קיים"""
    if subscribers_collection.find_one({'chat_id': chat_id}) is None:
        subscribers_collection.insert_one({'chat_id': chat_id})
        logger.info(f"New subscriber added to DB: {chat_id}")
        return True
    return False

def remove_subscriber(chat_id: int):
    """הסרת מנוי ממסד הנתונים"""
    result = subscribers_collection.delete_one({'chat_id': chat_id})
    if result.deleted_count > 0:
        logger.info(f"Subscriber removed from DB: {chat_id}")
        return True
    return False

# --- פקודות הבוט ---

async def start_command(update, context):
    """מטפל בפקודות /start ו /subscribe"""
    if add_subscriber(update.message.chat_id):
        await update.message.reply_text("✅ נרשמת בהצלחה לקבלת עדכונים!")
    else:
        await update.message.reply_text("🤔 אתה כבר רשום לקבלת עדכונים.")

async def unsubscribe_command(update, context):
    """מטפל בפקודת /unsubscribe"""
    if remove_subscriber(update.message.chat_id):
        await update.message.reply_text("🗑️ הסרנו אותך מרשימת התפוצה.")
    else:
        await update.message.reply_text("🤔 לא היית רשום מלכתחילה.")

# --- לוגיקת מעקב העדכונים ---

class AppUpdateMonitor:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.last_updates = {}
        # ... (שאר ההגדרות של הפידים והאמוג'ים נשארות זהות)
        self.rss_feeds = {
            'WhatsApp': 'https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/',
            'Telegram': 'https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/',
            'Instagram': 'https://www.apkmirror.com/apk/instagram/instagram-instagram/feed/'
        }
        self.app_emojis = {
            'WhatsApp': '💬', 'Telegram': '✈️', 'Instagram': '📸'
        }

    # ... (הפונקציות parse_rss_feed, extract_version, is_new_update נשארות זהות)
    def parse_rss_feed(self, app_name: str, rss_url: str) -> Optional[Dict]:
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries: return None
            latest_entry = feed.entries[0]
            return {
                'app_name': app_name, 'title': latest_entry.title,
                'link': latest_entry.link, 'published': latest_entry.published,
                'version': self.extract_version(latest_entry.title)
            }
        except Exception as e:
            logger.error(f"Error parsing RSS for {app_name}: {e}")
            return None

    def extract_version(self, title: str) -> str:
        import re
        version_match = re.search(r'(\d+\.\d+\.\d+(?:\.\d+)?)', title)
        return version_match.group(1) if version_match else "Unknown"

    def is_new_update(self, app_name: str, current_update: Dict) -> bool:
        last_version = self.last_updates.get(app_name, {}).get('version', '')
        current_version = current_update.get('version', '')
        return current_version != "Unknown" and current_version != last_version

    async def send_update_to_all(self, update_info: Dict):
        """שליחת התראה לכל המנויים ממסד הנתונים"""
        subscribers = get_all_subscribers()
        if not subscribers:
            logger.info("No subscribers to notify.")
            return

        app_name = update_info['app_name']
        emoji = self.app_emojis.get(app_name, '📱')
        message = f"🚨 {emoji} עדכון חדש באפליקציית {app_name}!\n\n📦 **{update_info['title']}**\n🔢 גרסה: {update_info['version']}\n📅 תאריך: {update_info['published']}\n\n🔗 [להורדה מ-APKMirror]({update_info['link']})"

        logger.info(f"Sending notification for {app_name} to {len(subscribers)} subscribers.")
        
        for chat_id in subscribers:
            try:
                await self.bot.send_message(
                    chat_id=chat_id, text=message, parse_mode='Markdown', disable_web_page_preview=True
                )
            except Forbidden:
                logger.warning(f"User {chat_id} blocked the bot. Removing from subscribers.")
                remove_subscriber(chat_id)
            except TelegramError as e:
                logger.error(f"Failed to send message to {chat_id}: {e}")
            await asyncio.sleep(0.1)

    async def check_all_apps_loop(self):
        """לולאת המעקב הראשית"""
        # ... (הלוגיקה הפנימית של הלולאה נשארת זהה)
        while True:
            logger.info("Starting app update check cycle...")
            for app_name, rss_url in self.rss_feeds.items():
                current_update = self.parse_rss_feed(app_name, rss_url)
                if not current_update: continue
                if self.is_new_update(app_name, current_update):
                    logger.info(f"New update found for {app_name}: {current_update['version']}")
                    await self.send_update_to_all(current_update)
                    self.last_updates[app_name] = current_update
                else:
                    logger.info(f"No new update for {app_name}")
                await asyncio.sleep(5)
            logger.info("Waiting 1 hour for next check...")
            await asyncio.sleep(3600)

async def main():
    """הפונקציה הראשית שמריצה הכל"""
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("Missing BOT_TOKEN environment variable")
        return

    application = ApplicationBuilder().token(bot_token).build()
    
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('subscribe', start_command))
    application.add_handler(CommandHandler('unsubscribe', unsubscribe_command))

    monitor = AppUpdateMonitor(application.bot)
    asyncio.create_task(monitor.check_all_apps_loop())
    
    logger.info("Starting bot polling...")
    await application.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
