#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Application - Telegram Security Bot with Automated Reporting
Integrates all components: Bot, Scheduler, and existing LLM system
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime

# Import bot components
from telegram_security_bot import TelegramSecurityBot
from telegram_report_scheduler import TelegramReportScheduler
from config.telegram_bot_config import TelegramBotConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramBotApplication:
    """Main application class that manages bot and scheduler"""
    
    def __init__(self):
        self.config = TelegramBotConfig()
        self.bot = None
        self.scheduler = None
        self.running = False
    
    async def initialize(self):
        """Initialize all components"""
        try:
            logger.info("🚀 Initializing Telegram Bot Application...")
            
            # Initialize bot
            self.bot = TelegramSecurityBot()
            bot_init = await self.bot.initialize()
            
            if not bot_init:
                logger.error("❌ Failed to initialize bot")
                return False
            
            # Initialize scheduler
            self.scheduler = TelegramReportScheduler(self.config.BOT_TOKEN)
            scheduler_init = await self.scheduler.initialize()
            
            if not scheduler_init:
                logger.error("❌ Failed to initialize scheduler")
                return False
            
            # Setup automated schedules
            self.scheduler.setup_schedules()
            
            logger.info("✅ All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during initialization: {e}")
            return False
    
    async def start(self):
        """Start the application"""
        try:
            if not await self.initialize():
                logger.error("Initialization failed, exiting...")
                return
            
            self.running = True
            
            # Start scheduler in background
            self.scheduler.start_scheduler()
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            logger.info("🎯 Starting Telegram Bot...")
            logger.info(f"📞 Bot Token: {self.config.BOT_TOKEN[:20]}...")
            logger.info("🔄 Scheduler: Running in background")
            logger.info("📊 Features: Reports, Q&A, PDF generation, RAG integration")
            
            # Start bot (this blocks until stopped)
            await self.bot.run_bot()
            
        except Exception as e:
            logger.error(f"❌ Error starting application: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown"""
        if not self.running:
            return
            
        logger.info("🛑 Shutting down application...")
        self.running = False
        
        # Stop scheduler
        if self.scheduler:
            self.scheduler.stop_scheduler()
            logger.info("⏰ Scheduler stopped")
        
        # Bot shutdown is handled by telegram library
        logger.info("🤖 Bot shutdown complete")
        
        logger.info("✅ Application shutdown complete")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
    
    def add_authorized_user(self, chat_id: int, user_type: str = 'admin'):
        """Add authorized user for automated reports"""
        if self.scheduler:
            return self.scheduler.add_authorized_chat(chat_id, user_type)
        return False
    
    def get_status(self) -> dict:
        """Get application status"""
        status = {
            'running': self.running,
            'bot_initialized': self.bot is not None,
            'scheduler_initialized': self.scheduler is not None,
            'timestamp': datetime.now().isoformat()
        }
        
        if self.scheduler:
            status['scheduler'] = self.scheduler.get_schedule_status()
        
        return status

def print_startup_banner():
    """Print startup banner"""
    print("=" * 80)
    print("🔒 TELEGRAM SECURITY BOT - AUTOMATED REPORTING SYSTEM")
    print("=" * 80)
    print(f"🤖 Bot Token: {TelegramBotConfig.BOT_TOKEN[:20]}...")
    print(f"🧠 LLM Model: {TelegramBotConfig.LM_STUDIO_CONFIG['model']}")
    print(f"🔧 LM Studio: {TelegramBotConfig.LM_STUDIO_CONFIG['base_url']}")
    print(f"🗄️  Database: {TelegramBotConfig.DATABASE_CONFIG['wazuh_db']}")
    print("=" * 80)
    print("\n📋 FEATURES:")
    print("✅ Interactive Security Bot with Menu Interface")
    print("✅ AI-Powered Security Analysis (LM Studio + RAG)")
    print("✅ Professional PDF Report Generation")
    print("✅ Automated Report Scheduling (Daily/3-day/Weekly/Monthly)")
    print("✅ Real-time Security Q&A with Wazuh Database")
    print("✅ Integration with existing FastMCP Server")
    print("✅ Multi-language Support (Indonesian)")
    
    print("\n📊 REPORT TYPES:")
    for report_type, config in TelegramBotConfig.REPORT_TYPES.items():
        print(f"• {config['emoji']} {config['name']} - {config['description']}")
    
    print("\n⏰ AUTOMATED SCHEDULES:")
    for report_type, schedule_config in TelegramBotConfig.REPORT_SCHEDULES.items():
        if schedule_config['enabled']:
            print(f"• {report_type.title()}: {schedule_config['time']} ({'Every ' + str(schedule_config.get('interval_days', 1)) + ' days' if 'interval_days' in schedule_config else 'Daily'})")
    
    print("\n🎯 READY TO START!")
    print("=" * 80)
    print()

async def main():
    """Main function"""
    try:
        print_startup_banner()
        
        # Check prerequisites
        print("🔍 Checking prerequisites...")
        
        # Check if wazuh database exists
        if not os.path.exists(TelegramBotConfig.DATABASE_CONFIG['wazuh_db']):
            print(f"⚠️  Warning: Wazuh database not found at {TelegramBotConfig.DATABASE_CONFIG['wazuh_db']}")
            print("   Make sure wazuh_archives.db is available")
        
        # Check if chat database exists
        if not os.path.exists(TelegramBotConfig.DATABASE_CONFIG['chat_db']):
            print(f"ℹ️  Chat database will be created automatically")
        
        print("✅ Prerequisites check complete")
        print()
        
        # Create and start application
        app = TelegramBotApplication()
        await app.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Application error: {e}")
        logger.exception("Application startup error")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
