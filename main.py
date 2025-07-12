#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot for monitoring app updates
בוט טלגרם למעקב אחר עדכוני אפליקציות
"""

import os
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import feedparser
from telegram import Bot
from telegram.error import TelegramError

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class AppUpdateMonitor:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id
        self.last_updates = {}  # אחסון העדכון האחרון של כל אפליקציה
        
        # RSS feeds for monitoring
        self.rss_feeds = {
            'WhatsApp': 'https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/',
            'Telegram': 'https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/',
            'Instagram': 'https://www.apkmirror.com/apk/instagram/instagram-instagram/feed/'
        }
        
        # אמוג'י לכל אפליקציה
        self.app_emojis = {
            'WhatsApp': '💬',
            'Telegram': '✈️',
            'Instagram': '📸'
        }
    
    def parse_rss_feed(self, app_name: str, rss_url: str) -> Optional[Dict]:
        """קריאת RSS feed והחזרת העדכון האחרון"""
        try:
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                logger.warning(f"No entries found for {app_name}")
                return None
            
            # העדכון האחרון
            latest_entry = feed.entries[0]
            
            return {
                'app_name': app_name,
                'title': latest_entry.title,
                'link': latest_entry.link,
                'published': latest_entry.published,
                'summary': getattr(latest_entry, 'summary', ''),
                'version': self.extract_version(latest_entry.title)
            }
            
        except Exception as e:
            logger.error(f"Error parsing RSS for {app_name}: {e}")
            return None
    
    def extract_version(self, title: str) -> str:
        """חילוץ מספר גרסה מכותרת"""
        # דוגמה: "WhatsApp 2.23.24.14 APK" -> "2.23.24.14"
        import re
        version_match = re.search(r'(\d+\.\d+\.\d+(?:\.\d+)?)', title)
        return version_match.group(1) if version_match else "Unknown"
    
    def is_new_update(self, app_name: str, current_update: Dict) -> bool:
        """בדיקה אם יש עדכון חדש"""
        if app_name not in self.last_updates:
            return True
        
        last_version = self.last_updates[app_name].get('version', '')
        current_version = current_update.get('version', '')
        
        return current_version != last_version
    
    async def send_update_notification(self, update_info: Dict):
        """שליחת התראה על עדכון חדש"""
        app_name = update_info['app_name']
        emoji = self.app_emojis.get(app_name, '📱')
        
        message = f"""
🚨 {emoji} עדכון חדש באפליקציית {app_name}!

📦 **{update_info['title']}**
🔢 גרסה: {update_info['version']}
📅 תאריך: {update_info['published']}

🔗 [להורדה מ-APKMirror]({update_info['link']})

---
מעקב אוטומטי של בוט עדכוני אפליקציות 🤖
        """.strip()
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            logger.info(f"Sent notification for {app_name} version {update_info['version']}")
            
        except TelegramError as e:
            logger.error(f"Failed to send message: {e}")
    
    async def check_all_apps(self):
        """בדיקת כל האפליקציות לעדכונים"""
        logger.info("Starting app update check cycle...")
        
        for app_name, rss_url in self.rss_feeds.items():
            logger.info(f"Checking {app_name}...")
            
            # קריאת RSS feed
            current_update = self.parse_rss_feed(app_name, rss_url)
            
            if not current_update:
                continue
            
            # בדיקה אם יש עדכון חדש
            if self.is_new_update(app_name, current_update):
                logger.info(f"New update found for {app_name}: {current_update['version']}")
                
                # שליחת התראה
                await self.send_update_notification(current_update)
                
                # שמירת העדכון האחרון
                self.last_updates[app_name] = current_update
            else:
                logger.info(f"No new update for {app_name}")
            
            # המתנה קצרה בין בדיקות
            await asyncio.sleep(5)
        
        logger.info("App update check cycle completed")
    
    async def send_startup_message(self):
        """שליחת הודעת התחלה"""
        startup_message = """
🤖 **בוט מעקב עדכוני אפליקציות פעיל!**

📱 אפליקציות במעקב:
• WhatsApp 💬
• Telegram ✈️
• Instagram 📸

⏰ בדיקת עדכונים כל שעה
🔔 תקבלו התראה מיידית על עדכונים חדשים

---
הבוט מוכן לעבודה! 🚀
        """.strip()
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=startup_message,
                parse_mode='Markdown'
            )
        except TelegramError as e:
            logger.error(f"Failed to send startup message: {e}")
    
    async def run_monitor(self):
        """הרצת הבוט הראשית"""
        logger.info("Starting App Update Monitor Bot...")
        
        # שליחת הודעת התחלה
        await self.send_startup_message()
        
        # לולאה אינסופית לבדיקת עדכונים
        while True:
            try:
                await self.check_all_apps()
                
                # המתנה של שעה לבדיקה הבאה
                logger.info("Waiting 1 hour for next check...")
                await asyncio.sleep(3600)  # 60 * 60 = 3600 שניות = שעה
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(300)  # המתנה של 5 דקות במקרה של שגיאה

def main():
    """פונקציה ראשית"""
    # קבלת משתני סביבה
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    
    if not bot_token or not chat_id:
        logger.error("Missing BOT_TOKEN or CHAT_ID environment variables")
        return
    
    # יצירת הבוט והרצתו
    monitor = AppUpdateMonitor(bot_token, chat_id)
    
    try:
        asyncio.run(monitor.run_monitor())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()