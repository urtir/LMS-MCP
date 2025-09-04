#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Report Scheduler
Handles automated report scheduling and delivery
"""

import asyncio
import schedule
import time
import threading
import logging
from datetime import datetime
from typing import Dict, List, Any
from telegram import Bot

from config.telegram_bot_config import TelegramBotConfig
from telegram_report_generator import get_report_generator
from telegram_pdf_generator import PDFReportGenerator

logger = logging.getLogger(__name__)

class TelegramReportScheduler:
    """Automated report scheduling system"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.bot = Bot(token=bot_token)
        self.config = TelegramBotConfig()
        self.report_generator = None
        self.pdf_generator = PDFReportGenerator()
        self.is_running = False
        self.scheduler_thread = None
        
        # Will store authorized chat IDs
        self.authorized_chats = {
            'admin': [],
            'security_team': [],
            'management': []
        }
    
    async def initialize(self):
        """Initialize scheduler components"""
        try:
            logger.info("🔄 Initializing report scheduler...")
            
            # Initialize report generator
            self.report_generator = await get_report_generator()
            
            # Load authorized chat IDs (for now, empty - will be populated via commands)
            # In production, load from database or config file
            
            logger.info("✅ Report scheduler initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing scheduler: {e}")
            return False
    
    def add_authorized_chat(self, chat_id: int, user_type: str = 'admin'):
        """Add authorized chat ID for automated reports"""
        if user_type in self.authorized_chats:
            if chat_id not in self.authorized_chats[user_type]:
                self.authorized_chats[user_type].append(chat_id)
                logger.info(f"Added chat {chat_id} to {user_type} group")
                return True
        return False
    
    def remove_authorized_chat(self, chat_id: int, user_type: str = None):
        """Remove authorized chat ID"""
        removed = False
        if user_type:
            if user_type in self.authorized_chats and chat_id in self.authorized_chats[user_type]:
                self.authorized_chats[user_type].remove(chat_id)
                removed = True
        else:
            # Remove from all groups
            for group in self.authorized_chats.values():
                if chat_id in group:
                    group.remove(chat_id)
                    removed = True
        
        if removed:
            logger.info(f"Removed chat {chat_id} from authorized lists")
        return removed
    
    def get_recipients_for_report(self, report_type: str) -> List[int]:
        """Get chat IDs that should receive specific report type"""
        schedule_config = self.config.REPORT_SCHEDULES.get(report_type, {})
        recipient_types = schedule_config.get('recipients', ['admin'])
        
        recipients = []
        for recipient_type in recipient_types:
            recipients.extend(self.authorized_chats.get(recipient_type, []))
        
        return list(set(recipients))  # Remove duplicates
    
    def setup_schedules(self):
        """Setup automated report schedules"""
        try:
            logger.info("⏰ Setting up automated report schedules...")
            
            # Daily reports
            if self.config.REPORT_SCHEDULES['daily']['enabled']:
                schedule.every().day.at(
                    self.config.REPORT_SCHEDULES['daily']['time']
                ).do(self._schedule_wrapper, self.send_daily_report)
                logger.info(f"📊 Daily reports scheduled at {self.config.REPORT_SCHEDULES['daily']['time']}")
            
            # 3-day reports 
            if self.config.REPORT_SCHEDULES['three_daily']['enabled']:
                interval = self.config.REPORT_SCHEDULES['three_daily']['interval_days']
                schedule.every(interval).days.at(
                    self.config.REPORT_SCHEDULES['three_daily']['time']
                ).do(self._schedule_wrapper, self.send_three_daily_report)
                logger.info(f"📈 3-day reports scheduled every {interval} days at {self.config.REPORT_SCHEDULES['three_daily']['time']}")
            
            # Weekly reports
            if self.config.REPORT_SCHEDULES['weekly']['enabled']:
                schedule.every().monday.at("08:00").do(self._schedule_wrapper, self.send_weekly_report)
                logger.info("📋 Weekly reports scheduled every Monday at 08:00")
            
            # Monthly reports
            if self.config.REPORT_SCHEDULES['monthly']['enabled']:
                # Note: schedule library doesn't support "first day of month" directly
                # We'll check this in a daily job
                schedule.every().day.at("08:00").do(self._schedule_wrapper, self.check_monthly_report)
                logger.info("📅 Monthly reports check scheduled daily at 08:00")
            
            logger.info("✅ All schedules configured successfully")
            
        except Exception as e:
            logger.error(f"❌ Error setting up schedules: {e}")
    
    def _schedule_wrapper(self, coro_func):
        """Wrapper to run async functions in scheduler"""
        try:
            # Create new event loop for this thread if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async function
            loop.run_until_complete(coro_func())
            
        except Exception as e:
            logger.error(f"Error in scheduled task: {e}")
    
    async def send_daily_report(self):
        """Send automated daily report"""
        try:
            logger.info("📊 Generating automated daily report...")
            
            recipients = self.get_recipients_for_report('daily')
            if not recipients:
                logger.info("No recipients configured for daily reports")
                return
            
            # Generate report
            report_data = await self.report_generator.generate_daily_report()
            
            if 'error' in report_data:
                logger.error(f"Error generating daily report: {report_data['error']}")
                return
            
            # Create text summary
            summary_text = self._create_automated_summary(report_data, 'daily')
            
            # Generate PDF
            pdf_buffer = await self.pdf_generator.generate_pdf_report(report_data)
            pdf_buffer.seek(0)
            
            filename = f"daily_security_report_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            # Send to all recipients
            for chat_id in recipients:
                try:
                    # Send text summary
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=summary_text,
                        parse_mode='Markdown'
                    )
                    
                    # Send PDF
                    pdf_buffer.seek(0)
                    await self.bot.send_document(
                        chat_id=chat_id,
                        document=pdf_buffer,
                        filename=filename,
                        caption="📊 Automated Daily Security Report"
                    )
                    
                    logger.info(f"✅ Daily report sent to chat {chat_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to send daily report to chat {chat_id}: {e}")
            
            logger.info(f"📊 Daily report sent to {len(recipients)} recipients")
            
        except Exception as e:
            logger.error(f"Error in automated daily report: {e}")
    
    async def send_three_daily_report(self):
        """Send automated 3-day report"""
        try:
            logger.info("📈 Generating automated 3-day report...")
            
            recipients = self.get_recipients_for_report('three_daily')
            if not recipients:
                logger.info("No recipients configured for 3-day reports")
                return
            
            report_data = await self.report_generator.generate_three_daily_report()
            
            if 'error' in report_data:
                logger.error(f"Error generating 3-day report: {report_data['error']}")
                return
            
            summary_text = self._create_automated_summary(report_data, 'three_daily')
            pdf_buffer = await self.pdf_generator.generate_pdf_report(report_data)
            
            filename = f"3day_security_report_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            for chat_id in recipients:
                try:
                    await self.bot.send_message(chat_id=chat_id, text=summary_text, parse_mode='Markdown')
                    pdf_buffer.seek(0)
                    await self.bot.send_document(
                        chat_id=chat_id, document=pdf_buffer, filename=filename,
                        caption="📈 Automated 3-Day Security Trend Report"
                    )
                    logger.info(f"✅ 3-day report sent to chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to send 3-day report to chat {chat_id}: {e}")
            
            logger.info(f"📈 3-day report sent to {len(recipients)} recipients")
            
        except Exception as e:
            logger.error(f"Error in automated 3-day report: {e}")
    
    async def send_weekly_report(self):
        """Send automated weekly report"""
        try:
            logger.info("📋 Generating automated weekly report...")
            
            recipients = self.get_recipients_for_report('weekly')
            if not recipients:
                logger.info("No recipients configured for weekly reports")
                return
            
            report_data = await self.report_generator.generate_weekly_report()
            
            if 'error' in report_data:
                logger.error(f"Error generating weekly report: {report_data['error']}")
                return
            
            summary_text = self._create_automated_summary(report_data, 'weekly')
            pdf_buffer = await self.pdf_generator.generate_pdf_report(report_data)
            
            filename = f"weekly_security_report_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            for chat_id in recipients:
                try:
                    await self.bot.send_message(chat_id=chat_id, text=summary_text, parse_mode='Markdown')
                    pdf_buffer.seek(0)
                    await self.bot.send_document(
                        chat_id=chat_id, document=pdf_buffer, filename=filename,
                        caption="📋 Automated Weekly Security Summary"
                    )
                    logger.info(f"✅ Weekly report sent to chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to send weekly report to chat {chat_id}: {e}")
            
            logger.info(f"📋 Weekly report sent to {len(recipients)} recipients")
            
        except Exception as e:
            logger.error(f"Error in automated weekly report: {e}")
    
    async def check_monthly_report(self):
        """Check if monthly report should be sent (first day of month)"""
        try:
            now = datetime.now()
            
            # Only send on first day of month
            if now.day != 1:
                return
            
            logger.info("📅 Generating automated monthly report...")
            
            recipients = self.get_recipients_for_report('monthly')
            if not recipients:
                logger.info("No recipients configured for monthly reports")
                return
            
            report_data = await self.report_generator.generate_monthly_report()
            
            if 'error' in report_data:
                logger.error(f"Error generating monthly report: {report_data['error']}")
                return
            
            summary_text = self._create_automated_summary(report_data, 'monthly')
            pdf_buffer = await self.pdf_generator.generate_pdf_report(report_data)
            
            filename = f"monthly_security_report_{now.strftime('%Y%m')}.pdf"
            
            for chat_id in recipients:
                try:
                    await self.bot.send_message(chat_id=chat_id, text=summary_text, parse_mode='Markdown')
                    pdf_buffer.seek(0)
                    await self.bot.send_document(
                        chat_id=chat_id, document=pdf_buffer, filename=filename,
                        caption="📅 Automated Monthly Security Assessment"
                    )
                    logger.info(f"✅ Monthly report sent to chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to send monthly report to chat {chat_id}: {e}")
            
            logger.info(f"📅 Monthly report sent to {len(recipients)} recipients")
            
        except Exception as e:
            logger.error(f"Error in automated monthly report: {e}")
    
    def _create_automated_summary(self, report_data: Dict[str, Any], report_type: str) -> str:
        """Create automated report summary"""
        config = report_data.get('report_config', {})
        statistics = report_data.get('statistics', {})
        summary = statistics.get('summary', {})
        ai_analysis = report_data.get('ai_analysis', {})
        
        summary_text = f"""
🤖 **AUTOMATED SECURITY REPORT**

{config.get('emoji', '📊')} **{config.get('name', 'Security Report')}**

📅 **Period:** {report_data.get('period', 'Unknown')}
⏰ **Generated:** {datetime.now().strftime('%d/%m/%Y %H:%M WIB')}

🚨 **Alert Level:** {ai_analysis.get('risk_level', 'Unknown')}

📊 **Key Statistics:**
• Total Events: `{summary.get('total_events', 0):,}`
• Critical (Level 7): `{statistics.get('critical_events', 0)}`
• High (Level 6): `{statistics.get('high_events', 0)}`  
• Active Agents: `{report_data.get('agent_status', {}).get('active_agents', 0)}/{report_data.get('agent_status', {}).get('total_agents', 0)}`
• Risk Score: `{ai_analysis.get('risk_score', 'N/A')}/10`

🔍 **Quick Analysis:**
{self._extract_summary_from_ai(ai_analysis.get('ai_analysis', ''))}

📄 **Detailed PDF report attached**

---
*This is an automated report. Reply to this chat for security questions.*
        """
        
        return summary_text
    
    def _extract_summary_from_ai(self, ai_analysis: str) -> str:
        """Extract brief summary from AI analysis"""
        if not ai_analysis:
            return "Sistem berjalan normal, tidak ada ancaman critical terdeteksi."
        
        # Extract first meaningful sentence
        sentences = ai_analysis.split('.')
        for sentence in sentences:
            if len(sentence.strip()) > 30:
                return sentence.strip()[:150] + "..."
        
        return ai_analysis[:150] + "..." if len(ai_analysis) > 150 else ai_analysis
    
    def start_scheduler(self):
        """Start the scheduler in background thread"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("⏰ Scheduler started in background thread")
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("⏰ Scheduler stopped")
    
    def _run_scheduler(self):
        """Run scheduler loop in background thread"""
        logger.info("⏰ Scheduler loop started")
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Continue after error
        
        logger.info("⏰ Scheduler loop stopped")
    
    def get_schedule_status(self) -> Dict[str, Any]:
        """Get current schedule status"""
        return {
            'is_running': self.is_running,
            'scheduled_jobs': len(schedule.jobs),
            'authorized_chats': {
                group: len(chats) for group, chats in self.authorized_chats.items()
            },
            'next_run': str(schedule.next_run()) if schedule.jobs else None,
            'report_schedules': {
                report_type: config['enabled'] 
                for report_type, config in self.config.REPORT_SCHEDULES.items()
            }
        }
