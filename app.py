#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Combined Flask app and Telegram Bot
Runs the health check endpoint and the bot in the background
"""

import os
import asyncio
import threading
import logging
from flask import Flask, jsonify

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Telegram App Monitor Bot',
        'version': '1.0.0'
    })

@app.route('/health')
def detailed_health():
    """Detailed health check"""
    # Check environment variables
    env_status = {
        'BOT_TOKEN': bool(os.getenv('BOT_TOKEN')),
        'MONGO_URI': bool(os.getenv('MONGO_URI'))
    }
    
    return jsonify({
        'status': 'healthy',
        'environment': env_status,
        'service': 'Telegram App Monitor Bot'
    })

def run_bot():
    """Run the Telegram bot in a separate thread"""
    try:
        from main import main as bot_main
        asyncio.run(bot_main())
    except Exception as e:
        logger.error(f"Error running bot: {e}")

def start_bot_background():
    """Start the bot in a background thread"""
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("Bot started in background thread")

if __name__ == '__main__':
    # Start the bot in background
    start_bot_background()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port)