#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot for monitoring app updates with a MongoDB subscription system.
Using the built-in Job Queue for scheduled tasks.
Final, stable version.
"""

import os
import asyncio
import logging
from typing import Dict, Optional, Set

import feedparser
from telegram import Bot
from telegram.error import TelegramError, Forbidden
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue
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
    # אם משתנה הסביבה לא הוגדר, התוכנית תיכשל עם שגיאה ברורה
    raise ValueError("MONGO_URI environment variable not set!")

client = MongoClient(MONGO_URI)
db = client['app_bot_db']  # שם מסד הנתונים
subscribers_collection = db['subscribers']  # שם האוסף (collection) שיחזיק את המנויים

# --- פונקציות לניהול מנויים מול מסד הנתונים ---

def get_all_subscribers() -> Set[int]:
    """שליפת כל מזהי המנויים ממסד הנתונים"""
    try:
        # מחזיר רק את השדה 'chat_id' מכל המסמכים
        cursor = subscribers_collection.find({}, {'chat_id': 1, '_id': 0})
        # המרה ל-set כדי למנוע כפילויות ולהקל על חיפושים
        return {item['chat_id'] for item in cursor}
    except Exception as e:
        logger.error(f"Error reading from MongoDB: {e}")
        return set()

def add_subscriber(chat_id: int) -> bool:
    """הוספת מנוי חדש אם הוא לא קיים"""
    # בדיקה אם המשתמש כבר קיים כדי למנוע כפילות
    if subscribers_collection.find_one({'chat_id': chat_id}) is None:
        subscribers_collection.insert_one({'chat_id': chat_id})
        logger.info(f"New subscriber added to DB: {chat_id}")
        return True
    return False

def remove_subscriber(chat_id: int) -> bool:
    """הסרת מנוי ממסד הנתונים"""
    result = subscribers_collection.delete_one({'chat_id': chat_id})
    if result.deleted_count > 0:
        logger.info(f"Subscriber removed from DB: {chat_id}")
        return True
    return False

# --- פקודות הבוט שיפעילו המשתמשים ---

async def start_command(update, context: ContextTypes.DEFAULT_TYPE):
    """מטפל בפקודות /start ו /subscribe"""
    if add_subscriber(update.message.chat_id):
        await update.message.reply_text("✅ נרשמת בהצלחה לקבלת עדכונים!")
    else:
        await update.message.reply_text("🤔 אתה כבר רשום לקבלת עדכונים.")

async def unsubscribe_command(update, context: ContextTypes.DEFAULT_TYPE):
    """מטפל בפקודת /unsubscribe"""
    if remove_subscriber(update.message.chat_id):
        await update.message.reply_text("🗑️ הסרנו אותך מרשימת התפוצה.")
    else:
        await update.message.reply_text("🤔 לא היית רשום מלכתחילה.")

# --- לוגיקת מעקב העדכונים (המשימה המחזורית) ---

# משתנים גלובליים שישמרו את מצב העדכונים האחרונים
LAST_UPDATES = {}
RSS_FEEDS = {
    'WhatsApp': 'https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/',
    'Telegram': 'https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/',
    'Instagram': 'https://www.apkmirror.com/apk/instagram/instagram-instagram/feed/'
}
APP_EMOJIS = {'WhatsApp': '💬', 'Telegram': '✈️', 'Instagram': '📸'}

def extract_version(title: str) -> str:
    """חילוץ מספר גרסה מכותרת באמצעות ביטוי רגולרי"""
    import re
    version_match = re.search(r'(\d+\.\d+\.\d+(?:\.\d+)?)', title)
    return version_match.group(1) if version_match else "Unknown"

async def check_all_apps(context: ContextTypes.DEFAULT_TYPE):
    """
    הפונקציה שתרוץ כל שעה. היא בודקת את כל האפליקציות ושולחת עדכונים.
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

            # בדיקה אם הגרסה חדשה ואינה שגויה
            if current_version != "Unknown" and current_version != last_version:
                logger.info(f"New update found for {app_name}: {current_version}")
                
                emoji = APP_EMOJIS.get(app_name, '📱')
                message = f"🚨 {emoji} עדכון חדש באפליקציית {app_name}!\n\n📦 **{latest_entry.title}**\n🔢 גרסה: {current_version}\n\n🔗 [להורדה מ-APKMirror]({latest_entry.link})"
                
                # שליחה לכל המנויים ממסד הנתונים
                subscribers = get_all_subscribers()
                for chat_id in subscribers:
                    try:
                        await bot.send_message(
                            chat_id=chat_id, text=message, parse_mode='Markdown', disable_web_page_preview=True
                        )
                    except Forbidden:
                        # אם משתמש חסם את הבוט, נסיר אותו מרשימת המנויים
                        logger.warning(f"User {chat_id} blocked the bot. Removing from subscribers.")
                        remove_subscriber(chat_id)
                    except TelegramError as e:
                        logger.error(f"Failed to send message to {chat_id}: {e}")
                
                # עדכון הגרסה האחרונה שראינו
                LAST_UPDATES[app_name] = current_version
            
        except Exception as e:
            logger.error(f"Error processing {app_name}: {e}")

# --- הפונקציה הראשית שמחברת הכל ---
async def main():
    """הפונקציה הראשית שמאתחלת ומריצה את הבוט"""
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("Missing BOT_TOKEN environment variable")
        return

    # יצירת תור המשימות במפורש
    job_queue = JobQueue()

    # בניית האפליקציה והעברת תור המשימות אליה
    application = ApplicationBuilder().token(bot_token).job_queue(job_queue).build()
    
    # רישום הפקודות שהבוט יכיר
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('subscribe', start_command)) # כינוי נוסף לפקודת התחלה
    application.add_handler(CommandHandler('unsubscribe', unsubscribe_command))

    # תזמון המשימה שתרוץ כל שעה
    job_queue.run_repeating(check_all_apps, interval=3600, first=10)

    # הרצת הבוט
    logger.info("Starting bot, listening for commands and running jobs...")
    await application.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}")

