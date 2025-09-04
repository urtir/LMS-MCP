#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Telegram Alert Bot for Testing
Simplified version to test alert functionality
"""

import asyncio
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleAlertBot:
    """Simple Telegram bot for testing alert functionality"""
    
    def __init__(self):
        self.token = "8289779353:AAG5TLJJP8JjwUJzQXMILAOG-7ufQA9ueM8"
        self.application = None
        self.alert_subscribers = set()
        self.last_alert_check = datetime.now()
        self.monitoring_task = None
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        keyboard = [
            [
                InlineKeyboardButton("🚨 Enable Alerts", callback_data='enable_alerts'),
                InlineKeyboardButton("🔕 Disable Alerts", callback_data='disable_alerts')
            ],
            [
                InlineKeyboardButton("📊 Alert Status", callback_data='alert_status')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔒 **Simple Alert Bot**\n\n"
            "Bot untuk testing alert system Wazuh.\n\n"
            "Commands:\n"
            "/start - Show menu\n"
            "/enable_alerts - Enable alerts\n" 
            "/disable_alerts - Disable alerts\n"
            "/status - Check status\n\n"
            "Choose an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        
        if data == 'enable_alerts':
            await self.enable_alerts(query, user_id)
        elif data == 'disable_alerts':
            await self.disable_alerts(query, user_id)
        elif data == 'alert_status':
            await self.show_status(query, user_id)
    
    async def enable_alerts(self, query, user_id):
        """Enable alerts for user"""
        self.alert_subscribers.add(user_id)
        
        # Start monitoring if not already running
        if not self.monitoring_task:
            self.monitoring_task = asyncio.create_task(self.monitoring_loop())
        
        await query.edit_message_text(
            "🚨 **Alerts Enabled**\n\n"
            f"✅ You will receive alerts for rule level 7+\n"
            f"👥 Total subscribers: {len(self.alert_subscribers)}\n"
            f"🔄 Monitoring: Active\n\n"
            "Use /disable_alerts to turn off."
        )
        
        logger.info(f"User {user_id} enabled alerts")
    
    async def disable_alerts(self, query, user_id):
        """Disable alerts for user"""
        self.alert_subscribers.discard(user_id)
        
        # Stop monitoring if no subscribers
        if not self.alert_subscribers and self.monitoring_task:
            self.monitoring_task.cancel()
            self.monitoring_task = None
        
        await query.edit_message_text(
            "🔕 **Alerts Disabled**\n\n"
            f"❌ Alerts turned off for your account\n"
            f"👥 Remaining subscribers: {len(self.alert_subscribers)}\n"
            f"🔄 Monitoring: {'Active' if self.monitoring_task else 'Stopped'}\n\n"
            "Use /enable_alerts to turn on."
        )
        
        logger.info(f"User {user_id} disabled alerts")
    
    async def show_status(self, query, user_id):
        """Show alert status"""
        user_subscribed = user_id in self.alert_subscribers
        
        await query.edit_message_text(
            f"📊 **Alert System Status**\n\n"
            f"**Your Status:** {'🟢 Subscribed' if user_subscribed else '🔴 Not Subscribed'}\n"
            f"**Monitoring:** {'🟢 Active' if self.monitoring_task else '🔴 Stopped'}\n"
            f"**Subscribers:** {len(self.alert_subscribers)}\n"
            f"**Last Check:** {self.last_alert_check.strftime('%H:%M:%S')}\n\n"
            f"**Alert Criteria:**\n"
            f"• Rule Level 7+ (High severity)\n"
            f"• Rule Level 8+ (Critical severity)\n"
            f"• Check interval: 30 seconds"
        )
    
    async def cmd_enable_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command handler for /enable_alerts"""
        user_id = update.effective_user.id
        self.alert_subscribers.add(user_id)
        
        if not self.monitoring_task:
            self.monitoring_task = asyncio.create_task(self.monitoring_loop())
        
        await update.message.reply_text(
            f"🚨 **Alerts Enabled**\n\n"
            f"✅ You will receive alerts for rule level 7+\n"
            f"👥 Total subscribers: {len(self.alert_subscribers)}\n"
            f"🔄 Monitoring: Active"
        )
        
        logger.info(f"User {user_id} enabled alerts via command")
    
    async def cmd_disable_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command handler for /disable_alerts"""
        user_id = update.effective_user.id
        self.alert_subscribers.discard(user_id)
        
        if not self.alert_subscribers and self.monitoring_task:
            self.monitoring_task.cancel()
            self.monitoring_task = None
        
        await update.message.reply_text(
            f"🔕 **Alerts Disabled**\n\n"
            f"❌ Alerts turned off\n"
            f"👥 Remaining subscribers: {len(self.alert_subscribers)}\n"
            f"🔄 Monitoring: {'Active' if self.monitoring_task else 'Stopped'}"
        )
        
        logger.info(f"User {user_id} disabled alerts via command")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command handler for /status"""
        user_id = update.effective_user.id
        user_subscribed = user_id in self.alert_subscribers
        
        await update.message.reply_text(
            f"📊 **Alert System Status**\n\n"
            f"**Your Status:** {'🟢 Subscribed' if user_subscribed else '🔴 Not Subscribed'}\n"
            f"**Monitoring:** {'🟢 Active' if self.monitoring_task else '🔴 Stopped'}\n"
            f"**Subscribers:** {len(self.alert_subscribers)}\n"
            f"**Last Check:** {self.last_alert_check.strftime('%H:%M:%S')}\n\n"
            f"**Database:** {'🟢 Available' if self.check_database() else '🔴 Error'}"
        )
    
    def check_database(self) -> bool:
        """Check if database is accessible"""
        try:
            conn = sqlite3.connect('wazuh_archives.db')
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM wazuh_archives WHERE rule_level >= 7 LIMIT 1")
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return False
    
    async def monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("🔄 Alert monitoring started")
        
        try:
            while True:
                if self.alert_subscribers:
                    alerts = self.check_for_critical_events()
                    if alerts:
                        await self.send_alerts(alerts)
                
                await asyncio.sleep(30)  # Check every 30 seconds
        
        except asyncio.CancelledError:
            logger.info("🔕 Alert monitoring stopped")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
    
    def check_for_critical_events(self) -> List[Dict[str, Any]]:
        """Check for new critical events"""
        try:
            conn = sqlite3.connect('wazuh_archives.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM wazuh_archives 
                WHERE rule_level >= 7 
                AND timestamp > ? 
                ORDER BY timestamp DESC 
                LIMIT 100
            """, (self.last_alert_check.strftime('%Y-%m-%d %H:%M:%S'),))
            
            events = cursor.fetchall()
            conn.close()
            
            if events:
                self.last_alert_check = datetime.now()
                
                alert_events = []
                for event in events:
                    alert_events.append({
                        'timestamp': event['timestamp'],
                        'agent_name': event['agent_name'] or 'Unknown',
                        'rule_id': event['rule_id'],
                        'rule_level': event['rule_level'],
                        'rule_description': event['rule_description'] or 'No description'
                    })
                
                logger.info(f"🚨 Found {len(alert_events)} new critical events")
                return alert_events
            
            self.last_alert_check = datetime.now()
            return []
            
        except Exception as e:
            logger.error(f"Error checking events: {e}")
            return []
    
    async def send_alerts(self, alerts: List[Dict[str, Any]]):
        """Send alerts to subscribers"""
        if not alerts:
            return
        
        # Group by severity
        critical = [a for a in alerts if a['rule_level'] >= 8]
        high = [a for a in alerts if a['rule_level'] == 7]
        
        # Create message
        message = self.create_alert_message(critical, high)
        
        # Send to all subscribers
        for user_id in self.alert_subscribers.copy():
            try:
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=message
                )
                logger.info(f"✅ Alert sent to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send alert to {user_id}: {e}")
                if "blocked" in str(e).lower():
                    self.alert_subscribers.discard(user_id)
    
    def create_alert_message(self, critical: List[Dict], high: List[Dict]) -> str:
        """Create alert message"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        parts = [
            f"🚨 SECURITY ALERT 🚨",
            f"Time: {timestamp}",
            ""
        ]
        
        if critical:
            parts.append(f"💥 CRITICAL ({len(critical)} events):")
            for alert in critical[:3]:
                parts.append(f"• Level {alert['rule_level']} - {alert['rule_description'][:60]}...")
                parts.append(f"  Agent: {alert['agent_name']} | Rule: {alert['rule_id']}")
            if len(critical) > 3:
                parts.append(f"  ... and {len(critical) - 3} more")
            parts.append("")
        
        if high:
            parts.append(f"⚠️ HIGH ({len(high)} events):")
            for alert in high[:2]:
                parts.append(f"• Level {alert['rule_level']} - {alert['rule_description'][:60]}...")
                parts.append(f"  Agent: {alert['agent_name']} | Rule: {alert['rule_id']}")
            if len(high) > 2:
                parts.append(f"  ... and {len(high) - 2} more")
            parts.append("")
        
        parts.extend([
            "🔍 Action Required:",
            "• Review events in Wazuh dashboard", 
            "• Investigate potential threats",
            "",
            "Use /status to check system status"
        ])
        
        return "\n".join(parts)
    
    async def run_bot(self):
        """Run the bot"""
        try:
            logger.info("🚀 Starting Simple Alert Bot...")
            
            # Create application
            self.application = Application.builder().token(self.token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("enable_alerts", self.cmd_enable_alerts))
            self.application.add_handler(CommandHandler("disable_alerts", self.cmd_disable_alerts))
            self.application.add_handler(CommandHandler("status", self.cmd_status))
            self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
            
            # Start bot
            logger.info("✅ Bot initialized")
            logger.info(f"🤖 Bot Username: @{(await self.application.bot.get_me()).username}")
            logger.info("🔄 Starting polling...")
            
            # Run bot
            async with self.application:
                await self.application.start()
                await self.application.updater.start_polling()
                
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt")
                finally:
                    if self.monitoring_task:
                        self.monitoring_task.cancel()
                    await self.application.updater.stop()
                    await self.application.stop()
        
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise

def main():
    """Main function"""
    async def run_async():
        bot = SimpleAlertBot()
        await bot.run_bot()
    
    try:
        asyncio.run(run_async())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot error: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Simple Alert Bot Starting")
    print("=" * 50)
    print("Features:")
    print("✅ Real-time alert monitoring")
    print("✅ Rule level 7+ detection")
    print("✅ Multiple subscriber support")
    print("✅ Simple command interface")
    print()
    
    main()
