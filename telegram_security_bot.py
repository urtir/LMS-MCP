#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Security Bot with RAG Integration
Main bot implementation with report generation and Q&A capabilities
"""

import asyncio
import logging
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)

# Import existing components
from database import ChatDatabase
from mcp_tool_bridge import FastMCPBridge
from openai import OpenAI

# Import new components
from config.telegram_bot_config import TelegramBotConfig
from telegram_report_generator import get_report_generator
from telegram_pdf_generator import PDFReportGenerator

logger = logging.getLogger(__name__)

class TelegramSecurityBot:
    """Main Telegram bot class for security reporting and Q&A"""
    
    def __init__(self):
        self.config = TelegramBotConfig()
        self.token = self.config.BOT_TOKEN
        self.authorized_users = set()  # Will be populated from database/config
        
        # Initialize existing components (same as webapp)
        self.chat_db = ChatDatabase()
        self.mcp_bridge = FastMCPBridge()
        self.llm_client = OpenAI(
            base_url=self.config.LM_STUDIO_CONFIG['base_url'],
            api_key=self.config.LM_STUDIO_CONFIG['api_key']
        )
        
        # Initialize new components
        self.pdf_generator = PDFReportGenerator()
        self.report_generator = None  # Will be initialized async
        
        # Bot state
        self.application = None
        self.chat_sessions = {}  # Store chat sessions per user
    
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
    
    async def handle_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle security questions using RAG system (similar to webapp)"""
        user_id = update.effective_user.id
        user_question = update.message.text
        
        if not self.is_user_authorized(user_id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        # Check if user is in question mode
        if user_id not in self.chat_sessions or self.chat_sessions[user_id].get('mode') != 'question':
            # Auto-activate question mode
            session_id = self.chat_db.create_session(f"Telegram_{user_id}_{int(time.time())}")
            self.chat_sessions[user_id] = {
                'mode': 'question',
                'session_id': session_id
            }
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            session_id = self.chat_sessions[user_id]['session_id']
            
            logger.info(f"Processing question from user {user_id}: {user_question}")
            
            # Use MCP bridge for RAG query (same as webapp)
            rag_response = await self.mcp_bridge.execute_tool(
                "check_wazuh_log",
                {
                    "query": user_question,
                    "max_results": 10,
                    "days_range": 7
                }
            )
            
            # Check if tool execution was successful
            if rag_response.get('status') != 'success':
                raise Exception(f"RAG query failed: {rag_response.get('message', 'Unknown error')}")
            
            # Extract content from response - this should already be processed by FastMCP
            rag_content = rag_response.get('content', 'No data found')
            
            # The FastMCP server should have already done semantic search and filtering
            # So we just need to send the filtered, relevant security data to LLM
            response = self.llm_client.chat.completions.create(
                model=self.config.LM_STUDIO_CONFIG['model'],
                messages=[
                    {
                        "role": "system",
                        "content": """You are a cybersecurity assistant specialized in analyzing Wazuh security data. 
                        Answer questions about security events, threats, and system status based on the provided data.
                        
                        The data has already been filtered using semantic search to show only relevant security events.
                        Provide responses in Indonesian language. Be precise, helpful, and include specific details 
                        from the security data when available. Focus on actionable security insights.
                        
                        Keep responses concise and under 800 tokens."""
                    },
                    {
                        "role": "user",
                        "content": f"Pertanyaan: {user_question}\n\nData Keamanan Relevan (sudah difilter): {rag_content[:3000]}"  # Limit to 3000 chars max
                    }
                ],
                temperature=self.config.LM_STUDIO_CONFIG['temperature'],
                max_tokens=800  # Limit response length
            )
            
            answer = response.choices[0].message.content
            
            # Save interaction to database (same as webapp)
            self.chat_db.add_message(session_id, "user", user_question)
            self.chat_db.add_message(session_id, "assistant", answer)
            
            # Send response
            await update.message.reply_text(answer, parse_mode='Markdown')
            
            logger.info(f"✅ Question answered for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing question from user {user_id}: {e}")
            await update.message.reply_text(
                f"❌ Error processing question: {str(e)}\n\n"
                "Please try again or contact administrator."
            )
    
    async def handle_system_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle system status check"""
        query = update.callback_query
        
        await query.edit_message_text("🔄 Checking system status...")
        
        try:
            # Check LM Studio connection
            lm_status = "✅ Connected"
            try:
                test_response = self.llm_client.chat.completions.create(
                    model=self.config.LM_STUDIO_CONFIG['model'],
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                lm_status = "✅ Connected"
            except Exception:
                lm_status = "❌ Disconnected"
            
            # Check MCP connection
            mcp_status = "✅ Connected" if self.mcp_bridge.client else "❌ Disconnected"
            
            # Check database
            try:
                stats = self.chat_db.get_stats()
                db_status = f"✅ Connected ({stats.get('total_sessions', 0)} sessions)"
            except Exception:
                db_status = "❌ Error"
            
            # Check report generator
            report_status = "✅ Ready" if self.report_generator else "❌ Not initialized"
            
            status_text = f"""
🔧 **System Status**

**Core Components:**
• LM Studio: {lm_status}
• FastMCP Server: {mcp_status}
• Database: {db_status}
• Report Generator: {report_status}

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

**Report Types:**
• **Daily Report** - Last 24 hours security events
• **3-Day Report** - 3-day trend analysis
• **Weekly Report** - Weekly security summary
• **Monthly Report** - Comprehensive monthly assessment

**Question Mode:**
Ask questions about security data using natural language:
• "Show me critical events today"
• "How many failed login attempts?"
• "Which agents are having issues?"
• "Any malware detected recently?"

**Features:**
✅ Real-time security monitoring
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
            
            self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
            self.application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND, 
                self.handle_question
            ))
            
            # Setup bot commands
            await self.setup_bot_commands()
            
            # Start bot
            logger.info("✅ Bot initialized successfully")
            logger.info(f"🤖 Bot Username: @{(await self.application.bot.get_me()).username}")
            logger.info("🔄 Starting polling...")
            
            # Use simple polling approach that works with existing event loop
            async with self.application:
                await self.application.start()
                await self.application.updater.start_polling()
                
                # Keep running
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt")
                finally:
                    await self.application.updater.stop()
                    await self.application.stop()
            
        except Exception as e:
            logger.error(f"❌ Error running bot: {e}")
            raise

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
    print("=" * 60)
    print("🚀 Telegram Security Bot Starting")
    print("=" * 60)
    print(f"🤖 Bot Token: {TelegramBotConfig.BOT_TOKEN[:10]}...") 
    print(f"🔧 LM Studio: {TelegramBotConfig.LM_STUDIO_CONFIG['base_url']}")
    print(f"🗄️  Database: {TelegramBotConfig.DATABASE_CONFIG['wazuh_db']}")
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
