#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
בדיקה מקומית מהירה לבוט טלגרם
Test script for local development
"""

import os
import asyncio
import feedparser
from datetime import datetime

# הגדרת משתני סביבה לבדיקה (החלף בערכים שלך)
BOT_TOKEN = "your_bot_token_here"
CHAT_ID = "your_chat_id_here"

def test_rss_feeds():
    """בדיקת קריאת RSS feeds"""
    print("🔍 בודק RSS feeds...")
    
    rss_feeds = {
        'WhatsApp': 'https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/feed/',
        'Telegram': 'https://www.apkmirror.com/apk/telegram-fz-llc/telegram/feed/',
        'Instagram': 'https://www.apkmirror.com/apk/instagram/instagram-instagram/feed/'
    }
    
    for app_name, rss_url in rss_feeds.items():
        print(f"\n📱 בודק {app_name}...")
        
        try:
            feed = feedparser.parse(rss_url)
            
            if feed.entries:
                latest = feed.entries[0]
                print(f"  ✅ נמצא עדכון: {latest.title}")
                print(f"  📅 תאריך: {latest.published}")
                print(f"  🔗 קישור: {latest.link}")
                
                # חילוץ גרסה
                import re
                version_match = re.search(r'(\d+\.\d+\.\d+(?:\.\d+)?)', latest.title)
                if version_match:
                    print(f"  🔢 גרסה: {version_match.group(1)}")
            else:
                print(f"  ❌ לא נמצאו עדכונים")
                
        except Exception as e:
            print(f"  ❌ שגיאה: {e}")

async def test_telegram_bot():
    """בדיקת חיבור לבוט טלגרם"""
    print("\n🤖 בודק חיבור לבוט טלגרם...")
    
    if BOT_TOKEN == "your_bot_token_here" or CHAT_ID == "your_chat_id_here":
        print("  ❌ אנא החלף את BOT_TOKEN ו-CHAT_ID בערכים האמיתיים")
        return
    
    try:
        from telegram import Bot
        
        bot = Bot(token=BOT_TOKEN)
        
        # בדיקה בסיסית
        me = await bot.get_me()
        print(f"  ✅ הבוט מחובר: @{me.username}")
        
        # שליחת הודעת בדיקה
        test_message = "🧪 הודעת בדיקה מהבוט!"
        await bot.send_message(chat_id=CHAT_ID, text=test_message)
        print(f"  ✅ הודעת בדיקה נשלחה בהצלחה!")
        
    except Exception as e:
        print(f"  ❌ שגיאה בחיבור לטלגרם: {e}")

def test_version_extraction():
    """בדיקת חילוץ גרסאות"""
    print("\n🔢 בודק חילוץ גרסאות...")
    
    test_titles = [
        "WhatsApp 2.23.24.14 APK",
        "Telegram 10.5.0 APK",
        "Instagram 300.0.0.34.111 APK",
        "כותרת ללא גרסה"
    ]
    
    import re
    
    for title in test_titles:
        version_match = re.search(r'(\d+\.\d+\.\d+(?:\.\d+)?)', title)
        if version_match:
            print(f"  ✅ {title} -> גרסה: {version_match.group(1)}")
        else:
            print(f"  ❌ {title} -> לא נמצאה גרסה")

def show_env_setup():
    """הצגת הוראות הגדרת משתני סביבה"""
    print("\n⚙️ הגדרת משתני סביבה:")
    print("\n# Linux/Mac:")
    print("export BOT_TOKEN='your_actual_bot_token'")
    print("export CHAT_ID='your_actual_chat_id'")
    print("\n# Windows:")
    print("set BOT_TOKEN=your_actual_bot_token")
    print("set CHAT_ID=your_actual_chat_id")
    print("\n# או ב-PowerShell:")
    print("$env:BOT_TOKEN='your_actual_bot_token'")
    print("$env:CHAT_ID='your_actual_chat_id'")

async def main():
    """פונקציה ראשית לבדיקות"""
    print("🚀 מתחיל בדיקות מערכת...")
    print("=" * 50)
    
    # בדיקת RSS
    test_rss_feeds()
    
    # בדיקת חילוץ גרסאות
    test_version_extraction()
    
    # בדיקת טלגרם
    await test_telegram_bot()
    
    # הצגת הוראות
    show_env_setup()
    
    print("\n" + "=" * 50)
    print("✅ בדיקות הסתיימו!")
    print("אם הכל עבד טוב, אתה מוכן להעלות לענן 🚀")

if __name__ == "__main__":
    # קבלת משתני סביבה אם הם מוגדרים
    if os.getenv('BOT_TOKEN'):
        BOT_TOKEN = os.getenv('BOT_TOKEN')
    if os.getenv('CHAT_ID'):
        CHAT_ID = os.getenv('CHAT_ID')
    
    asyncio.run(main())