#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot for monitoring app updates with a MongoDB subscription system
Using the built-in Job Queue for scheduled tasks.
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

def add_subscriber(chat_id: int):
    if subscribers_collection.find_one({'chat_id': chat_id}) is None:
        subscribers_collection.insert_one({'chat_id': chat_id})
        logger.info(f"New subscriber added to DB: {chat_id}")
        return True
    return False

def remove_subscriber(chat_id: int):
    result = subscribers_collection.delete_one({'chat_id': chat_id})
    if result.deleted_count > 0:
        logger.info(f"Subscriber removed from DB: {chat_id}")
        return True
    return False

# --- פקודות הבוט ---

async def start_command(update, context):
    if add_subscriber(update.message.chat_id):
        await update.message.reply_text("✅ נרשמת בהצלחה לקבלת עדכונים!")
    else:
        await update.message.reply_text("🤔 אתה כבר רשום לקבלת עדכונים.")

async def unsubscribe_command(update, context):
    if remove_subscriber(update.message.chat_id):
        await update.message.reply_text("🗑️ הסרנו אותך מרשימת התפוצה.")
    else:
        await update.message.reply_text("🤔 לא היית רשום מלכתחילה.")

# --- לוגיקת מעקב העדכונים ---

# אוסף הגדרות ומשתנים גלובליים למעקב
LAST_UPDATES = {}
RSS_FEEDS = {
    'WhatsApp': 'https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/',
    'Telegram': 'https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/',
    'Instagram': 'https://www.apkmirror.com/apk/instagram/instagram-instagram/feed/'
}
APP_EMOJIS = {'WhatsApp': '💬', 'Telegram': '✈️', 'Instagram': '📸'}

def extract_version(title: str) -> str:
    import re
    version_match = re.search(r'(\d+\.\d+\.\d+(?:\.\d+)?)', title)
    return version_match.group(1) if version_match else "Unknown"

async def check_all_apps(context: ContextTypes.DEFAULT_TYPE):
    """
    הפונקציה שתרוץ כל שעה. היא בודקת את כל האפליקציות.
    """
    logger.info("Job Queue: Starting app update check cycle...")
    bot = context.bot

    for app_name, rss_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                continue
            
            latest_entry = feed.entries[0]
            current_version = extract_version(latest_entry.title)
            last_version = LAST_UPDATES.get(app_name, "none")

            if current_version != "Unknown" and current_version != last_version:
                logger.info(f"New update found for {app_name}: {current_version}")
                
                # בניית ההודעה
                emoji = APP_EMOJIS.get(app_name, '📱')
                message = f"🚨 {emoji} עדכון חדש באפליקציית {app_name}!\n\n📦 **{latest_entry.title}**\n🔢 גרסה: {current_version}\n\n🔗 [להורדה מ-APKMirror]({latest_entry.link})"
                
                # שליחה לכל המנויים
                subscribers = get_all_subscribers()
                for chat_id in subscribers:
                    try:
                        await bot.send_message(
                            chat_id=chat_id, text=message, parse_mode='Markdown', disable_web_page_preview=True
                        )
                    except Forbidden:
                        logger.warning(f"User {chat_id} blocked the bot. Removing from subscribers.")
                        remove_subscriber(chat_id)
                    except TelegramError as e:
                        logger.error(f"Failed to send message to {chat_id}: {e}")
                
                LAST_UPDATES[app_name] = current_version
            
        except Exception as e:
            logger.error(f"Error processing {app_name}: {e}")

async def main():
    """הפונקציה הראשית שמריצה הכל"""
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("Missing BOT_TOKEN environment variable")
        return

    application = ApplicationBuilder().token(bot_token).build()
    
    # רישום הפקודות
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('subscribe', start_command))
    application.add_handler(CommandHandler('unsubscribe', unsubscribe_command))

    # --- שימוש ב-Job Queue ---
    job_queue = application.job_queue
    # הרצת המשימה פעם אחת 10 שניות אחרי ההתחלה, ואז כל שעה
    job_queue.run_repeating(check_all_apps, interval=3600, first=10)

    # הרצת הבוט
    logger.info("Starting bot...")
    await application.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}")

