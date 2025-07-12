#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Startup script for the Telegram App Monitor Bot
Checks environment variables and dependencies before starting
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = ['BOT_TOKEN', 'MONGO_URI']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these environment variables before starting the bot")
        return False
    
    logger.info("All required environment variables are set")
    return True

def check_dependencies():
    """Check if all required Python packages are installed"""
    required_packages = [
        'telegram',
        'feedparser', 
        'pymongo',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing required packages: {', '.join(missing_packages)}")
        logger.error("Please install them using: pip install -r requirements.txt")
        return False
    
    logger.info("All required packages are installed")
    return True

def main():
    """Main startup function"""
    logger.info("Starting Telegram App Monitor Bot...")
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Import and run the main bot
    try:
        from main import main as bot_main
        import asyncio
        
        logger.info("Starting bot...")
        asyncio.run(bot_main())
        
    except ImportError as e:
        logger.error(f"Failed to import main module: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()