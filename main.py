#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot for monitoring app updates with a MongoDB subscription system.
Final version using the robust async context manager for application lifecycle.
"""

import os
import asyncio
import logging
from typing import Dict, Optional, Set

import feedparser
from telegram import Bot
from telegram.error import TelegramError, Forbidden
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from pymongo import MongoClient

# --- הגדרות בסיסיות ולוגינג ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- התחברות למסד הנתונים MongoDB ---
MONGO_URI = os.getenv('MONGO_URI')
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set!")

client = MongoClient(MONGO_URI)
db = client['app_bot_db']
subscribers_collection = db['subscribers']

# --- פונקציות לניהול מנויים ---

def get_all_subscribers() -> Set[int]:
    try:
        cursor = subscribers_collection.find({}, {'chat_id': 1, '_id': 0})
        return {item['chat_id'] for item in cursor}
    except Exception as e:
        logger.error(f"Error reading from MongoDB: {e}")
        return set()

def add_subscriber(chat_id: int) -> bool:
    if subscribers_collection.find_one({'chat_id': chat_id}) is None:
        subscribers_collection.insert_one({'chat_id': chat_id})
        logger.info(f"New subscriber added to DB: {chat_id}")
        return True
    return False

def remove_subscriber(chat_id: int) -> bool:
    result = subscribers_collection.delete_one({'chat_id': chat_id})
    if result.deleted_count > 0:
        logger.info(f"Subscriber removed from DB: {chat_id}")
        return True
    return False

# --- פקודות הבוט שיפעילו המשתמשים ---

async def start_command(update, context: ContextTypes.DEFAULT_TYPE):
    if add_subscriber(update.message.chat_id):
        await update.message.reply_text("✅ נרשמת בהצלחה לקבלת עדכונים!")
    else:
        await update.message.reply_text("🤔 אתה כבר רשום לקבלת עדכונים.")

async def unsubscribe_command(update, context: ContextTypes.DEFAULT_TYPE):
    if remove_subscriber(update.message.chat_id):
        await update.message.reply_text("🗑️ הסרנו אותך מרשימת התפוצה.")
    else:
        await update.message.reply_text("🤔 לא היית רשום מלכתחילה.")

# --- לוגיקת מעקב העדכונים ---

class AppUpdateMonitor:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.last_updates = {}
        self.rss_feeds = {
            'WhatsApp': 'https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/',
            'Telegram': 'https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/',
            'Instagram': 'https://www.apkmirror.com/apk/instagram/instagram-instagram/feed/'
        }
        self.app_emojis = {'WhatsApp': '💬', 'Telegram': '✈️', 'Instagram': '📸'}

    def extract_version(self, title: str) -> str:
        import re
        version_match = re.search(r'(\d+\.\d+\.\d+(?:\.\d+)?)', title)
        return version_match.group(1) if version_match else "Unknown"

    async def check_apps_and_notify(self):
        for app_name, rss_url in self.rss_feeds.items():
            try:
                feed = feedparser.parse(rss_url)
                if not feed.entries: continue
                latest_entry = feed.entries[0]
                current_version = self.extract_version(latest_entry.title)
                last_version = self.last_updates.get(app_name, "none")
                if current_version != "Unknown" and current_version != last_version:
                    logger.info(f"New update found for {app_name}: {current_version}")
                    emoji = self.app_emojis.get(app_name, '📱')
                    message = f"🚨 {emoji} עדכון חדש באפליקציית {app_name}!\n\n📦 **{latest_entry.title}**\n🔢 גרסה: {current_version}\n\n🔗 [להורדה מ-APKMirror]({latest_entry.link})"
                    subscribers = get_all_subscribers()
                    for chat_id in subscribers:
                        try:
                            await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown', disable_web_page_preview=True)
                        except Forbidden:
                            logger.warning(f"User {chat_id} blocked the bot. Removing.")
                            remove_subscriber(chat_id)
                        except TelegramError as e:
                            logger.error(f"Failed to send message to {chat_id}: {e}")
                    self.last_updates[app_name] = current_version
            except Exception as e:
                logger.error(f"Error processing {app_name}: {e}")
    
    async def run_check_loop(self):
        await asyncio.sleep(10)
        while True:
            await self.check_apps_and_notify()
            logger.info("Background task: Check cycle complete. Sleeping for 1 hour.")
            await asyncio.sleep(3600)

# --- הפונקציה הראשית שמחברת הכל ---
async def main():
    """הפונקציה הראשית שמאתחלת ומריצה את הבוט"""
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("Missing BOT_TOKEN environment variable")
        return

    application = ApplicationBuilder().token(bot_token).build()
    
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('subscribe', start_command))
    application.add_handler(CommandHandler('unsubscribe', unsubscribe_command))

    # --- הדרך הנכונה לניהול מחזור החיים של האפליקציה ---
    # שימוש ב-async with מבטיח ש-initialize ו-shutdown יופעלו כראוי
    async with application:
        await application.initialize()  # אתחול הבוט
        await application.updater.start_polling()  # התחלת האזנה להודעות
        
        # יצירה והרצה של משימת הרקע לבדיקת עדכונים
        monitor = AppUpdateMonitor(application.bot)
        # שימוש ב-create_task כדי שהלולאה תרוץ ברקע ולא תחסום
        application.create_task(monitor.run_check_loop(), name="UpdateChecker")
        
        # לולאה אינסופית שמחזיקה את התוכנית הראשית בחיים
        # עד לקבלת אות עצירה (כמו Ctrl+C)
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped gracefully")

