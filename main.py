#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot for monitoring app updates with a subscription system
בוט טלגרם למעקב אחר עדכוני אפליקציות עם מערכת הרשמה
"""

import os
import time
import asyncio
import logging
import json
from typing import Dict, Optional, Set

import feedparser
from telegram import Bot
from telegram.error import TelegramError, Forbidden
from telegram.ext import ApplicationBuilder, CommandHandler

# --- הגדרות ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# חשוב! זהו הנתיב לקובץ המנויים. נסביר בהמשך למה הוא מוגדר כך עבור Render.
SUBSCRIBERS_FILE = '/data/subscribers.json'

# --- פונקציות לניהול מנויים ---

def load_subscribers() -> Set[int]:
    """טעינת מזהי המנויים מהקובץ"""
    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()
    try:
        with open(SUBSCRIBERS_FILE, 'r') as f:
            data = json.load(f)
            return set(data.get('subscribers', []))
    except (json.JSONDecodeError, FileNotFoundError):
        return set()

def save_subscribers(subscribers: Set[int]):
    """שמירת מזהי המנויים לקובץ"""
    # יצירת התיקייה אם היא לא קיימת
    os.makedirs(os.path.dirname(SUBSCRIBERS_FILE), exist_ok=True)
    with open(SUBSCRIBERS_FILE, 'w') as f:
        json.dump({'subscribers': list(subscribers)}, f)

# --- פקודות הבוט ---

async def start_command(update, context):
    """מטפל בפקודות /start ו /subscribe"""
    chat_id = update.message.chat_id
    subscribers = load_subscribers()
    
    if chat_id not in subscribers:
        subscribers.add(chat_id)
        save_subscribers(subscribers)
        logger.info(f"New subscriber added: {chat_id}")
        await update.message.reply_text("✅ נרשמת בהצלחה לקבלת עדכונים!")
    else:
        await update.message.reply_text("🤔 אתה כבר רשום לקבלת עדכונים.")

async def unsubscribe_command(update, context):
    """מטפל בפקודת /unsubscribe"""
    chat_id = update.message.chat_id
    subscribers = load_subscribers()

    if chat_id in subscribers:
        subscribers.remove(chat_id)
        save_subscribers(subscribers)
        logger.info(f"Subscriber removed: {chat_id}")
        await update.message.reply_text("🗑️ הסרנו אותך מרשימת התפוצה. לא תקבל יותר עדכונים.")
    else:
        await update.message.reply_text("🤔 לא היית רשום מלכתחילה.")

# --- לוגיקת מעקב העדכונים (כמעט ללא שינוי, מלבד שליחת ההודעות) ---

class AppUpdateMonitor:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.last_updates = {}
        self.rss_feeds = {
            'WhatsApp': 'https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/',
            'Telegram': 'https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/',
            'Instagram': 'https://www.apkmirror.com/apk/instagram/instagram-instagram/feed/'
        }
        self.app_emojis = {
            'WhatsApp': '💬', 'Telegram': '✈️', 'Instagram': '📸'
        }

    def parse_rss_feed(self, app_name: str, rss_url: str) -> Optional[Dict]:
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                logger.warning(f"No entries found for {app_name}")
                return None
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
        """שליחת התראה לכל המנויים"""
        subscribers = load_subscribers()
        if not subscribers:
            logger.info("No subscribers to notify.")
            return

        app_name = update_info['app_name']
        emoji = self.app_emojis.get(app_name, '📱')
        message = f"""
🚨 {emoji} עדכון חדש באפליקציית {app_name}!

📦 **{update_info['title']}**
🔢 גרסה: {update_info['version']}
📅 תאריך: {update_info['published']}

🔗 [להורדה מ-APKMirror]({update_info['link']})
        """.strip()

        logger.info(f"Sending notification for {app_name} to {len(subscribers)} subscribers.")
        
        # לולאה על כל המנויים ושליחת הודעה
        for chat_id in list(subscribers): # יצירת עותק כדי שנוכל לשנות את המקורי
            try:
                await self.bot.send_message(
                    chat_id=chat_id, text=message, parse_mode='Markdown', disable_web_page_preview=True
                )
            except Forbidden:
                # המשתמש חסם את הבוט, נסיר אותו מהרשימה
                logger.warning(f"User {chat_id} blocked the bot. Removing from subscribers.")
                subscribers.remove(chat_id)
                save_subscribers(subscribers)
            except TelegramError as e:
                logger.error(f"Failed to send message to {chat_id}: {e}")
            await asyncio.sleep(0.1) # כדי לא להציף את ה-API של טלגרם

    async def check_all_apps_loop(self):
        """לולאת המעקב הראשית"""
        while True:
            logger.info("Starting app update check cycle...")
            for app_name, rss_url in self.rss_feeds.items():
                current_update = self.parse_rss_feed(app_name, rss_url)
                if not current_update:
                    continue
                
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

    # בניית אפליקציית הבוט
    application = ApplicationBuilder().token(bot_token).build()

    # רישום הפקודות
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('subscribe', start_command)) # כינוי נוסף
    application.add_handler(CommandHandler('unsubscribe', unsubscribe_command))

    # יצירת והרצת לולאת המעקב כרקע
    monitor = AppUpdateMonitor(application.bot)
    asyncio.create_task(monitor.check_all_apps_loop())
    
    # שליחת הודעת התחלה (אופציונלי, אפשר להסיר אם לא רוצים)
    await application.bot.send_message(
        chat_id=os.getenv('ADMIN_CHAT_ID'), # שולח הודעת אתחול רק למנהל
        text="🤖 בוט עדכונים עם מערכת הרשמה פעיל!"
    )

    # הרצת הבוט (מקשיב לפקודות)
    logger.info("Starting bot polling...")
    await application.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

