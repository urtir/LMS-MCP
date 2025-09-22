#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Security Bot with RAG Integration
Main bot implementation with report generation and Q&A capabilities
"""

# Fix Windows Unicode encoding issues
import sys
if sys.platform == "win32":
    import io
    # Force UTF-8 encoding on Windows
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Safe print function for Windows
def safe_print(text):
    """Print text with fallback for Windows encoding issues"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Remove emojis and special characters if encoding fails
        safe_text = text.encode('ascii', errors='ignore').decode('ascii')
        print(safe_text)

import asyncio
import logging
import json
import os
import threading
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add config directory to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
from config.config_manager import ConfigManager
config = ConfigManager()

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)

# Add parent directories to path for importing project modules
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Import project components
from src.database import ChatDatabase
from src.api import FastMCPBridge
from openai import OpenAI

# Import webapp chatbot components for consistency
from src.webapp.webapp_chatbot import ChatSession, process_chat_message

# Import config and other telegram modules
# Use internal telegram config
from src.utils.telegram_config import TelegramBotConfig

from src.telegram.telegram_report_generator import get_report_generator
from src.telegram.telegram_pdf_generator import PDFReportGenerator

logger = logging.getLogger(__name__)

class TelegramSecurityBot:
    """Main Telegram bot class for security reporting and Q&A"""
    
    def __init__(self):
        self.config = TelegramBotConfig()
        
        # Setup database paths from JSON configuration
        database_dir = config.get('database.DATABASE_DIR')
        self.wazuh_db_name = config.get('database.WAZUH_DB_NAME') 
        self.chat_db_name = config.get('database.CHAT_DB_NAME')
        
        # Build full paths
        self.wazuh_db_path = os.path.join(database_dir, self.wazuh_db_name)
        self.chat_db_path = os.path.join(database_dir, self.chat_db_name)
        
        # Ensure absolute paths
        if not os.path.isabs(self.wazuh_db_path):
            self.wazuh_db_path = os.path.join(project_root, self.wazuh_db_path)
        if not os.path.isabs(self.chat_db_path):
            self.chat_db_path = os.path.join(project_root, self.chat_db_path)
        self.token = self.config.BOT_TOKEN
        self.authorized_users = set()  # Will be populated from database/config
        
        # Initialize existing components (same as webapp)
        self.chat_db = ChatDatabase()
        self.mcp_bridge = FastMCPBridge()
        self.llm_client = OpenAI(
            base_url=self.config.LM_STUDIO_CONFIG['base_url'],
            api_key=self.config.LM_STUDIO_CONFIG['api_key'],
            timeout=None  # No timeout
        )
        
        # Initialize new components
        self.pdf_generator = PDFReportGenerator()
        self.report_generator = None  # Will be initialized async
        
        # Bot state
        self.application = None
        self.chat_sessions = {}  # Store chat sessions per user
        
        # Realtime alert system
        self.alert_subscribers = set()  # Users subscribed to alerts
        self.alert_running = False
        self.last_alert_check = datetime.now()
        self.sent_alert_ids = set()  # Track sent alert IDs to prevent duplicates
        self.pending_alerts = []  # Store alerts to be sent
    
    async def initialize(self):
        """Initialize all bot components"""
        try:
            logger.info("🚀 Initializing Telegram Security Bot...")
            
            # Initialize report generator
            self.report_generator = await get_report_generator()
            
            # Initialize MCP bridge
            await self.mcp_bridge.connect_to_server()
            
            # Load authorized users (for now, allow any user - can be configured later)
            self.authorized_users.add("all")  # Temporary - implement proper authorization
            
            logger.info("✅ Telegram Security Bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing bot: {e}")
            return False
    
    def is_user_authorized(self, user_id: int) -> bool:
        """Check if user is authorized to use bot"""
        # For now, allow all users - implement proper authorization later
        return True
        # return user_id in self.authorized_users or "all" in self.authorized_users
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        if not self.is_user_authorized(user.id):
            await update.message.reply_text(
                "❌ Anda tidak memiliki akses ke bot ini. Hubungi administrator untuk otorisasi."
            )
            return
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Daily Report", callback_data='report_daily'),
                InlineKeyboardButton("📈 3-Day Report", callback_data='report_3day')
            ],
            [
                InlineKeyboardButton("📋 Weekly Report", callback_data='report_weekly'),
                InlineKeyboardButton("📅 Monthly Report", callback_data='report_monthly')
            ],
            [
                InlineKeyboardButton("🚨 Enable Alerts", callback_data='enable_alerts'),
                InlineKeyboardButton("🔕 Disable Alerts", callback_data='disable_alerts')
            ],
            [
                InlineKeyboardButton("❓ Ask Security Question", callback_data='mode_question'),
                InlineKeyboardButton("📊 System Status", callback_data='system_status')
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data='settings'),
                InlineKeyboardButton("📖 Help", callback_data='help')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
🔒 **Security Monitoring Bot**

Selamat datang {user.first_name}!

Saya adalah bot untuk monitoring keamanan sistem Wazuh. Saya dapat:

• 📊 Generate laporan keamanan (harian, 3-hari, mingguan, bulanan)
• 🚨 Mengirim alert realtime untuk event critical (level 7+)
• 🤖 Menjawab pertanyaan tentang data keamanan menggunakan AI
• 📄 Membuat laporan PDF yang detail
• 🔍 Melakukan analisis mendalam dengan RAG system

Pilih menu di bawah untuk memulai:
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        
        if not self.is_user_authorized(user_id):
            await query.edit_message_text("❌ Unauthorized access")
            return
        
        # Route to appropriate handler
        if data.startswith('report_'):
            await self.handle_report_request(update, context, data)
        elif data == 'enable_alerts':
            await self.handle_enable_alerts(update, context)
        elif data == 'disable_alerts':
            await self.handle_disable_alerts(update, context)
        elif data == 'mode_question':
            await self.handle_question_mode(update, context)
        elif data == 'system_status':
            await self.handle_system_status(update, context)
        elif data == 'settings':
            await self.handle_settings(update, context)
        elif data == 'help':
            await self.handle_help(update, context)
        else:
            await query.edit_message_text("❓ Unknown command")
    
    async def handle_report_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, report_type: str):
        """Handle report generation requests"""
        query = update.callback_query
        report_name = report_type.replace('report_', '')
        
        # Show processing message
        processing_msg = await query.edit_message_text(
            f"🔄 Generating {report_name} report...\n\n"
            "This may take a few moments. Please wait."
        )
        
        try:
            # Generate report based on type
            logger.info(f"Generating {report_name} report for user {update.effective_user.id}")
            
            if report_name == 'daily':
                report_data = await self.report_generator.generate_daily_report()
            elif report_name == '3day':
                report_data = await self.report_generator.generate_three_daily_report()
            elif report_name == 'weekly':
                report_data = await self.report_generator.generate_weekly_report()
            elif report_name == 'monthly':
                report_data = await self.report_generator.generate_monthly_report()
            else:
                await query.edit_message_text("❌ Invalid report type")
                return
            
            # Check for errors
            if 'error' in report_data:
                await query.edit_message_text(f"❌ Error generating report: {report_data['error']}")
                return
            
            # Create text summary first
            summary_text = self._create_text_summary(report_data)
            
            # Send text summary
            await query.edit_message_text(summary_text, parse_mode='Markdown')
            
            # Generate and send PDF
            pdf_buffer = await self.pdf_generator.generate_pdf_report(report_data)
            pdf_buffer.seek(0)
            
            filename = f"security_report_{report_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=pdf_buffer,
                filename=filename,
                caption=f"📄 Detailed {report_name.title()} Security Report",
                reply_to_message_id=query.message.message_id
            )
            
            logger.info(f"✅ {report_name} report sent successfully to user {update.effective_user.id}")
            
        except Exception as e:
            logger.error(f"Error generating {report_name} report: {e}")
            await query.edit_message_text(f"❌ Error generating report: {str(e)}")
    
    async def handle_question_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle question mode activation"""
        query = update.callback_query
        
        # Set user to question mode
        user_id = update.effective_user.id
        if user_id not in self.chat_sessions:
            self.chat_sessions[user_id] = {
                'mode': 'question',
                'session_id': self.chat_db.create_session(f"Telegram_{user_id}_{int(time.time())}")
            }
        else:
            self.chat_sessions[user_id]['mode'] = 'question'
        
        await query.edit_message_text(
            "🤖 **Question Mode Activated**\n\n"
            "Silakan kirim pertanyaan Anda tentang data keamanan sistem.\n\n"
            "Contoh pertanyaan:\n"
            "• 'Tampilkan critical events hari ini'\n"
            "• 'Berapa banyak failed login attempts?'\n"
            "• 'Apa saja malware yang terdeteksi?'\n"
            "• 'Status agent mana yang bermasalah?'\n\n"
            "Ketik /menu untuk kembali ke menu utama.",
            parse_mode='Markdown'
        )
    
    async def handle_enable_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enable realtime alerts for critical events (level 7+)"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        # Add user to alert subscribers
        self.alert_subscribers.add(user_id)
        
        # Start alert monitoring if not already running
        if not self.alert_running:
            self.start_alert_monitoring()
        
        await query.edit_message_text(
            "🚨 **Realtime Alerts Enabled**\n\n"
            "✅ Anda akan menerima notifikasi realtime untuk:\n"
            "• Critical events (Rule Level 8+)\n"
            "• High severity incidents (Rule Level 6-7)\n"
            "• Medium events (Rule Level 5)\n"
            "• Security threats dan anomali\n\n"
            f"👥 Total subscribers: {len(self.alert_subscribers)}\n"
            f"🔄 Alert monitoring: {'Active' if self.alert_running else 'Starting...'}\n"
            "⚡ Check interval: 10 detik (REALTIME)\n\n"
            "Gunakan /disable_alerts untuk menonaktifkan."
        )
        
        logger.info(f"User {user_id} enabled realtime alerts")
    
    async def handle_disable_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Disable realtime alerts for user"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        # Remove user from alert subscribers
        self.alert_subscribers.discard(user_id)
        
        # Stop alert monitoring if no subscribers
        if not self.alert_subscribers and self.alert_running:
            self.stop_alert_monitoring()
            # Reset sent alert tracking when monitoring stops
            self.sent_alert_ids.clear()
            logger.info("🔄 Alert tracking reset - all alerts can be sent again when monitoring restarts")
        
        await query.edit_message_text(
            "🔕 **Realtime Alerts Disabled**\n\n"
            "❌ Alert notifications telah dimatikan untuk akun Anda.\n\n"
            f"👥 Remaining subscribers: {len(self.alert_subscribers)}\n"
            f"🔄 Alert monitoring: {'Active' if self.alert_running else 'Stopped'}\n\n"
            "Gunakan /enable_alerts untuk mengaktifkan kembali."
        )
        
        logger.info(f"User {user_id} disabled realtime alerts")
    
    async def handle_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle security questions using SAME SYSTEM as webapp chatbot"""
        user_id = update.effective_user.id
        user_question = update.message.text
        
        if not self.is_user_authorized(user_id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        # Check if user is in question mode - auto activate untuk semua message
        if user_id not in self.chat_sessions:
            session_id = self.chat_db.create_session(f"Telegram_{user_id}_{int(time.time())}")
            # Use SAME ChatSession class as webapp chatbot
            chat_session = ChatSession(session_id)
            self.chat_sessions[user_id] = {
                'mode': 'question',
                'session_id': session_id,
                'chat_session': chat_session  # Add actual ChatSession object
            }
        
        chat_session = self.chat_sessions[user_id]['chat_session']
        session_id = self.chat_sessions[user_id]['session_id']
        
        # Initialize tools if not already done (SAME as webapp)
        await chat_session.initialize_tools()
        
        # Add user message to session (SAME as webapp)
        chat_session.add_message("user", user_question)
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            # === USE MODIFIED PROCESS FOR TELEGRAM BOT (ASYNC COMPATIBLE) ===
            
            logger.info(f"=== PROCESSING MESSAGE FOR SESSION {session_id} ===")
            logger.info(f"Using MODIFIED async-compatible system for Telegram bot")
            
            # Call our async-compatible version instead of webapp function
            result = await self.process_chat_message_async(chat_session, session_id)
            
            if "error" in result:
                error_message = f"❌ Error processing question: {result['error']}"
                await update.message.reply_text(error_message)
                logger.error(f"Chat processing error: {result['error']}")
                return
            
            # Get the response content (webapp returns "response" key, not "content")
            response_content = result.get("response", "Maaf, tidak ada response yang dihasilkan.")
            
            # Clean response for Telegram (remove think tags, etc.)
            response_content = self._remove_think_tags(response_content)
            response_content = self._clean_markdown(response_content)
            
            # NOTE: No need to save to database again - process_chat_message already saved it
            
            # Split long responses for Telegram
            max_length = 4096  # Telegram message limit
            if len(response_content) > max_length:
                parts = [response_content[i:i+max_length] for i in range(0, len(response_content), max_length)]
                for part in parts:
                    await update.message.reply_text(part, parse_mode='Markdown')
            else:
                await update.message.reply_text(response_content, parse_mode='Markdown')
            
            logger.info("Response sent successfully to Telegram")
            logger.info(f"Chat processing complete. Response length: {len(response_content)} characters")
            logger.info(f"✅ Question answered for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing question from user {user_id}: {e}")
            await update.message.reply_text(
                f"❌ Error processing question: {str(e)}\n\n"
                "Please try again or contact administrator."
            )
    
    async def handle_system_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle system status check - only MCP"""
        query = update.callback_query
        
        await query.edit_message_text("🔄 Checking MCP status...")
        
        try:
            # Check MCP connection only
            mcp_status = "✅ Connected" if self.mcp_bridge.client else "❌ Disconnected"
            
            # Check report generator
            report_status = "✅ Ready" if self.report_generator else "❌ Not initialized"
            
            status_text = f"""
🔧 **System Status**

**Core Components:**
• FastMCP Server: {mcp_status}
• Report Generator: {report_status}

**🚨 Alert System:**
• Alert Monitoring: {'🟢 Active' if self.alert_running else '🔴 Stopped'}
• Total Subscribers: {len(self.alert_subscribers)}
• Last Alert Check: {self.last_alert_check.strftime('%d/%m/%Y %H:%M:%S')}

**Configuration:**
• Model: {self.config.LM_STUDIO_CONFIG['model']}
• Database: {self.config.DATABASE_CONFIG['wazuh_db']}

**Bot Statistics:**
• Active Sessions: {len(self.chat_sessions)}
• Authorized Users: All users allowed

*Status checked: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}*
            """
            
            await query.edit_message_text(status_text, parse_mode='Markdown')
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error checking status: {str(e)}")
    
    async def handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle settings menu"""
        query = update.callback_query
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Status", callback_data='system_status')],
            [InlineKeyboardButton("📊 Database Stats", callback_data='db_stats')],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data='back_main')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        settings_text = """
⚙️ **Settings & Configuration**

**Available Options:**
• Check system status
• View database statistics
• Return to main menu

**Current Configuration:**
• Auto-report: Disabled (manual only)
• PDF Generation: Enabled
• Question Mode: Available
        """
        
        await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle help command"""
        query = update.callback_query
        
        help_text = """
📖 **Bot Help & Commands**

**Available Commands:**
/start - Show main menu
/menu - Return to main menu
/status - Check system status
/help - Show this help
/enable_alerts - Enable realtime alerts
/disable_alerts - Disable realtime alerts
/alert_status - Check alert system status

**Report Types:**
• **Daily Report** - Last 24 hours security events
• **3-Day Report** - 3-day trend analysis
• **Weekly Report** - Weekly security summary
• **Monthly Report** - Comprehensive monthly assessment

**🚨 Realtime Alert System:**
• Monitors critical events (Rule Level 5+)
• Instant notifications untuk medium/high/critical incidents
• 10-second check interval (AGGRESSIVE REALTIME)
• Only checks LATEST 5 ROWS (no historical data)
• Auto-disable jika tidak ada subscribers

**Question Mode:**
Ask questions about security data using natural language:
• "Show me critical events today"
• "How many failed login attempts?"
• "Which agents are having issues?"
• "Any malware detected recently?"

**Features:**
✅ Real-time security monitoring
✅ Critical event alerts (Level 7+)
✅ AI-powered threat analysis
✅ Professional PDF reports
✅ Interactive Q&A with RAG
✅ Multi-language support (Indonesian)

**Need Help?**
Contact your system administrator for technical support.
        """
        
        await query.edit_message_text(help_text, parse_mode='Markdown')
    
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command - return to main menu"""
        # Reset user session mode
        user_id = update.effective_user.id
        if user_id in self.chat_sessions:
            self.chat_sessions[user_id]['mode'] = 'menu'
        
        # Reuse start command logic
        await self.start_command(update, context)
    
    def _create_text_summary(self, report_data: Dict[str, Any]) -> str:
        """Create text summary of report for Telegram"""
        config = report_data.get('report_config', {})
        statistics = report_data.get('statistics', {})
        summary = statistics.get('summary', {})
        ai_analysis = report_data.get('ai_analysis', {})
        
        # Format the summary
        summary_text = f"""
{config.get('emoji', '📊')} **{config.get('name', 'Security Report')}**

📅 **Period:** {report_data.get('period', 'Unknown')}
⏰ **Generated:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

📈 **Key Metrics:**
• Total Events: `{summary.get('total_events', 0):,}`
• Critical (L7): `{statistics.get('critical_events', 0)}`
• High (L6): `{statistics.get('high_events', 0)}`
• Active Agents: `{report_data.get('agent_status', {}).get('active_agents', 0)}`

🤖 **AI Risk Assessment:**
• Risk Score: `{ai_analysis.get('risk_score', 'N/A')}/10`
• Risk Level: `{ai_analysis.get('risk_level', 'Unknown')}`

🔍 **Quick Analysis:**
{self._extract_quick_analysis(ai_analysis.get('ai_analysis', 'Analysis not available'))[:200]}...

📄 **PDF report akan dikirim terpisah**
        """
        
        return summary_text
    
    def _extract_quick_analysis(self, full_analysis: str) -> str:
        """Extract quick summary from full AI analysis"""
        # Simple extraction of first paragraph or summary
        lines = full_analysis.split('\n')
        for line in lines:
            if len(line.strip()) > 50:  # Find first substantial line
                return line.strip()
        return "Analysis completed successfully"
    
    def start_alert_monitoring(self):
        """Start AGGRESSIVE realtime alert monitoring (every 10 seconds)"""
        if self.alert_running:
            return
        
        self.alert_running = True
        
        # Use more aggressive scheduling - every 10 seconds for true realtime
        if self.application and self.application.job_queue:
            self.application.job_queue.run_repeating(
                self.check_and_send_alerts,
                interval=10,  # 10 seconds for more realtime monitoring
                first=3,      # Start after 3 seconds
                name="realtime_alert_monitoring"
            )
            logger.info("🚨 AGGRESSIVE realtime alert monitoring started (10s interval, rule level 5+, LATEST 5 ROWS ONLY)")
        else:
            logger.warning("⚠️ Job queue not available, alert monitoring not started")
    
    def stop_alert_monitoring(self):
        """Stop realtime alert monitoring"""
        self.alert_running = False
        
        if self.application and self.application.job_queue:
            # Remove existing alert monitoring jobs
            jobs = self.application.job_queue.get_jobs_by_name("realtime_alert_monitoring")
            for job in jobs:
                job.schedule_removal()
            logger.info("🔕 Aggressive realtime alert monitoring stopped")
    
    async def check_and_send_alerts(self, context: ContextTypes.DEFAULT_TYPE):
        """Check for critical events and send alerts (runs as scheduled job)"""
        try:
            # Only proceed if we have subscribers
            if not self.alert_subscribers:
                return
            
            # Check for new critical events
            new_alerts = self.check_for_critical_events()
            
            if new_alerts:
                # Send alerts to all subscribers
                await self.send_alerts_to_subscribers(new_alerts)
                
        except Exception as e:
            logger.error(f"Error in alert checking job: {e}")
    
    def check_for_critical_events(self) -> List[Dict[str, Any]]:
        """Check database for new critical events (rule level 5+) - REALTIME with duplicate prevention"""
        try:
            # Connect to Wazuh archives database
            conn = sqlite3.connect(self.wazuh_db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            # Get ONLY LATEST 5 events with rule level >= 5 (REALTIME ONLY)
            # Use ID-based tracking instead of timestamp to prevent duplicates
            cursor.execute("""
                SELECT * FROM wazuh_archives 
                WHERE rule_level >= 5
                ORDER BY timestamp DESC, id DESC
                LIMIT 5
            """)
            
            events = cursor.fetchall()
            conn.close()
            
            if events:
                # Filter out already sent alerts
                new_events = []
                for event in events:
                    event_id = event['id']
                    if event_id not in self.sent_alert_ids:
                        # Add to sent alerts tracking
                        self.sent_alert_ids.add(event_id)
                        
                        new_events.append({
                            'id': event['id'],
                            'timestamp': event['timestamp'],
                            'agent_name': event['agent_name'] or 'Unknown',
                            'rule_id': event['rule_id'],
                            'rule_level': event['rule_level'],
                            'rule_description': event['rule_description'],
                            'location': event['location'],
                            'full_log': event['full_log']
                        })
                
                # Clean up sent_alert_ids to prevent memory issues (keep only last 1000)
                if len(self.sent_alert_ids) > 1000:
                    # Keep only the most recent 500 IDs
                    recent_ids = sorted(list(self.sent_alert_ids))[-500:]
                    self.sent_alert_ids = set(recent_ids)
                
                if new_events:
                    logger.info(f"🚨 Found {len(new_events)} NEW UNIQUE events (rule level 5+, duplicates filtered)")
                    return new_events
                else:
                    logger.debug("No new unique events found (all events already sent)")
                    return []
            
            return []
            
        except Exception as e:
            logger.error(f"Error checking for critical events: {e}")
            return []
    
    async def send_alerts_to_subscribers(self, alerts: List[Dict[str, Any]]):
        """Send alert notifications to all subscribers"""
        if not self.alert_subscribers or not alerts:
            return
        
        try:
            # Group alerts by severity
            critical_alerts = [a for a in alerts if a['rule_level'] >= 8]
            high_alerts = [a for a in alerts if a['rule_level'] >= 6 and a['rule_level'] < 8]
            medium_alerts = [a for a in alerts if a['rule_level'] == 5]
            
            # Create alert message
            alert_message = self._create_alert_message(critical_alerts, high_alerts, medium_alerts)
            
            # Send to all subscribers with Markdown formatting
            for user_id in self.alert_subscribers.copy():  # Copy to avoid modification during iteration
                try:
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=alert_message,
                        parse_mode='Markdown',  # Enable Markdown formatting for code blocks
                        disable_web_page_preview=True  # Disable preview for cleaner look
                    )
                    logger.info(f"✅ Alert sent to user {user_id} with full log details")
                
                except Exception as e:
                    logger.error(f"❌ Failed to send alert to user {user_id}: {e}")
                    # Remove user if they blocked the bot
                    if "bot was blocked by the user" in str(e).lower():
                        self.alert_subscribers.discard(user_id)
                        logger.info(f"🚫 Removed blocked user {user_id} from alert subscribers")
        
        except Exception as e:
            logger.error(f"Error sending alerts to subscribers: {e}")
    
    def _create_alert_message(self, critical_alerts: List[Dict], high_alerts: List[Dict], medium_alerts: List[Dict]) -> str:
        """Create formatted alert message for rule level 5+ WITH FULL LOG DETAILS"""
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        message_parts = [
            "🚨 *SECURITY ALERT* 🚨\n",
            f"⏰ *Time:* {timestamp}\n"
        ]
        
        if critical_alerts:
            message_parts.append(f"💥 *CRITICAL Events (L8+):* {len(critical_alerts)}")
            for i, alert in enumerate(critical_alerts[:2], 1):  # Show max 2 critical with full details
                desc = alert['rule_description'][:60] + "..." if len(alert['rule_description']) > 60 else alert['rule_description']
                message_parts.extend([
                    f"\n*🔥 Critical Alert #{i}:*",
                    f"• *Level:* {alert['rule_level']} | *Rule:* {alert['rule_id']}",
                    f"• *Agent:* `{alert['agent_name']}`",
                    f"• *Location:* `{alert['location'] or 'N/A'}`",
                    f"• *Description:* {desc}",
                    f"• *Timestamp:* `{alert['timestamp']}`"
                ])
                
                # Add full_log as code block
                full_log = alert.get('full_log', '').strip()
                if full_log:
                    # Truncate very long logs to prevent message size limits
                    if len(full_log) > 800:
                        full_log = full_log[:800] + "...[truncated]"
                    
                    message_parts.extend([
                        f"• *Full Log:*",
                        f"```",
                        full_log,
                        f"```"
                    ])
                else:
                    message_parts.append("• *Full Log:* _(No log data available)_")
                
                message_parts.append("")
            
            if len(critical_alerts) > 2:
                message_parts.append(f"  ⚡ _...dan {len(critical_alerts) - 2} critical alerts lainnya_")
            message_parts.append("")
        
        if high_alerts:
            message_parts.append(f"⚠️ *HIGH Events (L6-7):* {len(high_alerts)}")
            for i, alert in enumerate(high_alerts[:1], 1):  # Show max 1 high with full details
                desc = alert['rule_description'][:60] + "..." if len(alert['rule_description']) > 60 else alert['rule_description']
                message_parts.extend([
                    f"\n*🔴 High Alert #{i}:*",
                    f"• *Level:* {alert['rule_level']} | *Rule:* {alert['rule_id']}",
                    f"• *Agent:* `{alert['agent_name']}`",
                    f"• *Location:* `{alert['location'] or 'N/A'}`",
                    f"• *Description:* {desc}",
                    f"• *Timestamp:* `{alert['timestamp']}`"
                ])
                
                # Add full_log as code block
                full_log = alert.get('full_log', '').strip()
                if full_log:
                    # Truncate very long logs
                    if len(full_log) > 600:
                        full_log = full_log[:600] + "...[truncated]"
                    
                    message_parts.extend([
                        f"• *Full Log:*",
                        f"```",
                        full_log,
                        f"```"
                    ])
                else:
                    message_parts.append("• *Full Log:* _(No log data available)_")
                
                message_parts.append("")
                
            if len(high_alerts) > 1:
                message_parts.append(f"  ⚡ _...dan {len(high_alerts) - 1} high alerts lainnya_")
            message_parts.append("")
        
        if medium_alerts:
            message_parts.append(f"🔍 *MEDIUM Events (L5):* {len(medium_alerts)}")
            # For medium alerts, show summary only (no full logs to avoid spam)
            for alert in medium_alerts[:2]:  # Show max 2 medium summary
                desc = alert['rule_description'][:50] + "..." if len(alert['rule_description']) > 50 else alert['rule_description']
                message_parts.extend([
                    f"• *L{alert['rule_level']}* - {desc}",
                    f"  `{alert['agent_name']}` | Rule: `{alert['rule_id']}`"
                ])
            if len(medium_alerts) > 2:
                message_parts.append(f"  ⚡ _...dan {len(medium_alerts) - 2} medium alerts lainnya_")
            message_parts.append("")
        
        message_parts.extend([
            "🎯 *Action Required:*",
            "• Review events dalam dashboard Wazuh",
            "• Investigasi potential threats", 
            "• Update security measures jika diperlukan",
            "",
            "💬 _Ketik pertanyaan untuk detail analysis dengan AI!_"
        ])
        
        return "\n".join(message_parts)
    
    async def cmd_enable_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command handler for /enable_alerts"""
        user_id = update.effective_user.id
        
        if not self.is_user_authorized(user_id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        # Add user to alert subscribers
        self.alert_subscribers.add(user_id)
        
        # Start alert monitoring if not already running
        if not self.alert_running:
            self.start_alert_monitoring()
        
        await update.message.reply_text(
            "🚨 Realtime Alerts Enabled\n\n"
            "✅ Anda akan menerima notifikasi realtime untuk:\n"
            "• Critical events (Rule Level 8+)\n"
            "• High severity incidents (Rule Level 6-7)\n"
            "• Medium events (Rule Level 5)\n"
            "• Security threats dan anomali\n\n"
            f"👥 Total subscribers: {len(self.alert_subscribers)}\n"
            f"🔄 Alert monitoring: {'Active' if self.alert_running else 'Starting...'}\n"
            "⚡ Check interval: 10 detik (REALTIME)\n\n"
            "Gunakan /disable_alerts untuk menonaktifkan."
        )
        
        logger.info(f"User {user_id} enabled realtime alerts via command")
    
    async def cmd_disable_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command handler for /disable_alerts"""
        user_id = update.effective_user.id
        
        if not self.is_user_authorized(user_id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        # Remove user from alert subscribers
        self.alert_subscribers.discard(user_id)
        
        # Stop alert monitoring if no subscribers
        if not self.alert_subscribers and self.alert_running:
            self.stop_alert_monitoring()
        
        await update.message.reply_text(
            "🔕 Realtime Alerts Disabled\n\n"
            "❌ Alert notifications telah dimatikan untuk akun Anda.\n\n"
            f"👥 Remaining subscribers: {len(self.alert_subscribers)}\n"
            f"🔄 Alert monitoring: {'Active' if self.alert_running else 'Stopped'}\n\n"
            "Gunakan /enable_alerts untuk mengaktifkan kembali."
        )
        
        logger.info(f"User {user_id} disabled realtime alerts via command")
    
    async def cmd_alert_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command handler for /alert_status"""
        user_id = update.effective_user.id
        
        if not self.is_user_authorized(user_id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        user_subscribed = user_id in self.alert_subscribers
        
        status_text = f"""
🚨 Alert System Status

Your Status: {'🟢 Subscribed' if user_subscribed else '🔴 Not Subscribed'}
Alert Monitoring: {'🟢 Active' if self.alert_running else '🔴 Stopped'}
Total Subscribers: {len(self.alert_subscribers)}
Last Check: {self.last_alert_check.strftime('%d/%m/%Y %H:%M:%S')}

Alert Criteria:
• Rule Level 5+ (Medium, High, Critical)
• Rule Level 6-7 (High severity)  
• Rule Level 8+ (Critical severity)
• Check interval: 10 seconds (REALTIME)

Commands:
/enable_alerts - Enable notifications
/disable_alerts - Disable notifications
/alert_status - Check current status
        """
        
        await update.message.reply_text(status_text)
    
    async def setup_bot_commands(self):
        """Setup bot commands for Telegram menu"""
        commands = [
            BotCommand(command, description) 
            for command, description in self.config.BOT_COMMANDS
        ]
        
        await self.application.bot.set_my_commands(commands)
    
    async def run_bot(self):
        """Main method to run the bot"""
        try:
            logger.info("🚀 Starting Telegram Security Bot...")
            
            # Initialize bot
            if not await self.initialize():
                logger.error("❌ Failed to initialize bot")
                return
            
            # Create application
            self.application = Application.builder().token(self.token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("menu", self.menu_command))
            self.application.add_handler(CommandHandler("status", self.handle_system_status))
            self.application.add_handler(CommandHandler("help", self.handle_help))
            self.application.add_handler(CommandHandler("enable_alerts", self.cmd_enable_alerts))
            self.application.add_handler(CommandHandler("disable_alerts", self.cmd_disable_alerts))
            self.application.add_handler(CommandHandler("alert_status", self.cmd_alert_status))
            
            self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
            self.application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND, 
                self.handle_question
            ))
            
            # Setup bot commands
            await self.setup_bot_commands()
            
            # Start bot
            logger.info("✅ Bot initialized successfully")
            bot_info = await self.application.bot.get_me()
            logger.info(f"Bot Username: @{bot_info.username}")
            logger.info("🔄 Starting polling...")
            
            # Use simple polling approach that works with existing event loop
            async with self.application:
                await self.application.start()
                await self.application.updater.start_polling()
                
                # Start realtime alert monitoring if there are subscribers
                alert_task = None
                if self.alert_subscribers:
                    alert_task = asyncio.create_task(self.realtime_alert_monitor())
                
                # Keep running
                try:
                    while True:
                        await asyncio.sleep(1)
                        
                        # Check if we need to start/stop alert monitoring
                        if self.alert_subscribers and not alert_task:
                            alert_task = asyncio.create_task(self.realtime_alert_monitor())
                            logger.info("🚨 Started realtime alert monitoring")
                        elif not self.alert_subscribers and alert_task:
                            alert_task.cancel()
                            alert_task = None
                            logger.info("🔕 Stopped realtime alert monitoring")
                            
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt")
                finally:
                    if alert_task:
                        alert_task.cancel()
                    await self.application.updater.stop()
                    await self.application.stop()
            
        except Exception as e:
            logger.error(f"❌ Error running bot: {e}")
            raise
    
    async def realtime_alert_monitor(self):
        """Realtime alert monitoring loop"""
        logger.info("🔄 Realtime alert monitoring started")
        
        try:
            while self.alert_subscribers:  # Keep running while there are subscribers
                try:
                    # Check for new critical events
                    alerts = self.check_for_critical_events()
                    
                    if alerts:
                        await self.send_alerts_to_subscribers(alerts)
                    
                    # Wait 30 seconds before next check
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"Error in alert monitoring: {e}")
                    await asyncio.sleep(60)  # Wait longer on error
        
        except asyncio.CancelledError:
            logger.info("🔕 Realtime alert monitoring cancelled")
        except Exception as e:
            logger.error(f"Fatal error in alert monitoring: {e}")
        
        logger.info("🔕 Realtime alert monitoring stopped")
    
    def _remove_think_tags(self, text: str) -> str:
        """Remove <think> tags and their content from LLM response - AGGRESSIVE VERSION"""
        import re
        
        if not text:
            return text
        
        # Remove <think>...</think> blocks (case insensitive, multiline, greedy)
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove any remaining opening or closing think tags
        text = re.sub(r'</?think>', '', text, flags=re.IGNORECASE)
        
        # Also handle cases where think content might be at the beginning
        # Remove everything from start until first non-think content
        lines = text.split('\n')
        cleaned_lines = []
        found_content = False
        
        for line in lines:
            line_stripped = line.strip()
            # Skip empty lines and think-related content at start
            if not found_content and (not line_stripped or 'think' in line_stripped.lower()):
                continue
            found_content = True
            cleaned_lines.append(line)
        
        # Rejoin and clean up extra whitespace/newlines
        text = '\n'.join(cleaned_lines)
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Replace multiple newlines with double newline
        text = text.strip()  # Remove leading/trailing whitespace
        
        return text
    
    def _clean_markdown(self, text: str) -> str:
        """Clean problematic markdown characters that cause parsing errors"""
        import re
        
        # Replace problematic characters
        text = text.replace('`', "'")  # Replace backticks with single quotes
        text = text.replace('*', '•')  # Replace asterisks with bullets
        text = text.replace('_', '-')  # Replace underscores with dashes
        text = text.replace('[', '(')  # Replace square brackets
        text = text.replace(']', ')')
        text = text.replace('#', '➤')  # Replace hash symbols
        
        # Remove problematic markdown patterns
        text = re.sub(r'\*\*([^*]+)\*\*', r'**\1**', text)  # Fix bold formatting
        text = re.sub(r'`([^`]+)`', r'"\1"', text)  # Replace code blocks with quotes
        
        return text
    
    def _strip_markdown(self, text: str) -> str:
        """Strip all markdown formatting for plain text fallback"""
        import re
        
        # Remove all markdown formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Remove bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # Remove italic
        text = re.sub(r'`([^`]+)`', r'"\1"', text)      # Replace code with quotes
        text = re.sub(r'#{1,6}\s*', '', text)           # Remove headers
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Remove links
        text = text.replace('_', ' ')                   # Replace underscores
        
        return text
    
    async def process_chat_message_async(self, session: "ChatSession", session_id: str) -> Dict[str, Any]:
        """Process chat message with LM Studio and MCP tools (ASYNC VERSION for Telegram)"""
        try:
            logger.info(f"=== PROCESSING MESSAGE FOR SESSION {session.session_id} ===")
            logger.info(f"Session has {len(session.get_messages())} messages")
            logger.info(f"Available MCP tools: {len(session.mcp_tools) if session.mcp_tools else 0}")
            
            # Get LM Studio response with tools
            logger.info(f"Sending request to LM Studio: {self.config.LM_STUDIO_CONFIG['base_url']}")
            logger.info(f"Model: {self.config.LM_STUDIO_CONFIG['model']}")
            
            messages = session.get_messages()
            logger.debug(f"Messages to send: {messages}")
            
            response = self.llm_client.chat.completions.create(
                model=self.config.LM_STUDIO_CONFIG['model'],
                messages=messages,
                tools=session.mcp_tools,
                tool_choice="auto"
            )
            
            logger.info("LM Studio response received successfully")
            
            assistant_message = response.choices[0].message
            tool_results = []
            
            if assistant_message.tool_calls:
                logger.info(f"Processing {len(assistant_message.tool_calls)} tool calls")
                
                # Add assistant message with tool calls
                session.messages.append({
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": tool_call.function,
                        }
                        for tool_call in assistant_message.tool_calls
                    ],
                })
                
                # Execute each tool call (ASYNC VERSION)
                for i, tool_call in enumerate(assistant_message.tool_calls):
                    try:
                        tool_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        
                        logger.info(f"Executing tool {i+1}/{len(assistant_message.tool_calls)}: {tool_name}")
                        logger.debug(f"Tool arguments: {arguments}")
                        
                        # Execute MCP tool (AWAIT instead of asyncio.run)
                        result = await self.mcp_bridge.execute_tool(tool_name, arguments)
                        logger.info(f"Tool {tool_name} executed successfully")
                        logger.debug(f"Tool result: {result}")
                        
                        # Log actual tool content for debugging
                        if result and "content" in result:
                            content_preview = str(result["content"])[:200] + "..." if len(str(result["content"])) > 200 else str(result["content"])
                            logger.info(f"Tool content preview: {content_preview}")
                        
                        tool_results.append({
                            "name": tool_name,
                            "arguments": arguments,
                            "result": result
                        })
                        
                        # Add tool result to messages
                        session.messages.append({
                            "role": "tool",
                            "content": json.dumps(result),
                            "tool_call_id": tool_call.id,
                        })
                        
                    except Exception as e:
                        logger.error(f"Tool execution error for {tool_call.function.name}: {e}", exc_info=True)
                        error_result = {
                            "status": "error",
                            "message": str(e),
                            "tool_name": tool_call.function.name
                        }
                        tool_results.append({
                            "name": tool_call.function.name,
                            "arguments": {},
                            "result": error_result
                        })
                        
                        session.messages.append({
                            "role": "tool",
                            "content": json.dumps(error_result),
                            "tool_call_id": tool_call.id,
                        })
                
                # Get final response after tool execution
                logger.info("Getting final response from LM Studio after tool execution...")
                final_response = self.llm_client.chat.completions.create(
                    model=self.config.LM_STUDIO_CONFIG['model'],
                    messages=session.get_messages()
                )
                
                final_message = final_response.choices[0].message.content
                logger.info("Final response received from LM Studio")
                logger.debug(f"Final message: {final_message}")
                
                # Clean think tags immediately from final message
                if final_message:
                    cleaned_message = self._remove_think_tags(final_message)
                    logger.info(f"Message cleaned from think tags. Original length: {len(final_message) if final_message else 0}, Cleaned length: {len(cleaned_message)}")
                    final_message = cleaned_message
                
                session.add_message("assistant", final_message)
                
                # Save assistant message to database with tool usage
                logger.info("Saving assistant message to database...")
                self.chat_db.add_message(session_id, "assistant", final_message, tool_results)
                logger.info("Message saved to database successfully")
                
                return {
                    "response": final_message,
                    "tool_calls": tool_results,
                    "thinking": None,
                    "session_id": session.session_id
                }
            
            else:
                # No tool calls, regular response
                logger.info("No tool calls - processing regular response")
                response_text = assistant_message.content
                logger.debug(f"Response text: {response_text}")
                
                session.add_message("assistant", response_text)
                
                # Save assistant message to database
                logger.info("Saving regular response to database...")
                self.chat_db.add_message(session_id, "assistant", response_text)
                logger.info("Response saved to database successfully")
                
                return {
                    "response": response_text,
                    "tool_calls": [],
                    "thinking": None,
                    "session_id": session.session_id
                }
        
        except Exception as e:
            logger.error(f"ERROR PROCESSING CHAT MESSAGE: {e}", exc_info=True)
            return {
                "error": f"Failed to process message: {str(e)}",
                "session_id": session.session_id
            }

# Main execution
def main():
    """Main function to run the bot"""
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    async def run_async():
        bot = TelegramSecurityBot()
        await bot.run_bot()
    
    # Check if we're already in an async context
    try:
        # Try to get current running loop
        loop = asyncio.get_running_loop()
        # If successful, we're in an async context, create task
        task = loop.create_task(run_async())
        # For interactive environments, we need to handle this differently
        return task
    except RuntimeError:
        # Not in async context, safe to use asyncio.run
        asyncio.run(run_async())

if __name__ == "__main__":
    # Create config instance for display
    config_instance = TelegramBotConfig()
    safe_print("=" * 60)
    safe_print("🚀 Telegram Security Bot Starting")
    safe_print("=" * 60)
    safe_print(f"🤖 Bot Token: {config_instance.BOT_TOKEN[:10]}...") 
    safe_print(f"🔧 LM Studio: {config_instance.LM_STUDIO_CONFIG['base_url']}")
    safe_print(f"🗄️  Database: {config_instance.DATABASE_CONFIG['wazuh_db']}")
    print("=" * 60)
    print()
    print("Features:")
    print("✅ Daily, 3-day, weekly, monthly reports")
    print("✅ AI-powered security analysis")
    print("✅ PDF report generation")
    print("✅ Interactive Q&A with RAG")
    print("✅ Real-time threat monitoring")
    print()
    print("Starting bot...")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot error: {e}")
        logger.exception("Bot startup error")
