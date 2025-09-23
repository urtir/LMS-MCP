"""
Telegram Bot Con        self.BOT_TOKEN = config_manager.get('security.TELEGRAM_BOT_TOKEN')
        
        # LM Studio configuration - NO FALLBACKS!
        self.LM_STUDIO = {
            'base_url': config_manager.get('network.LM_STUDIO_BASE_URL'),
            'api_key': config_manager.get('ai_model.LM_STUDIO_API_KEY'),
            'model': config_manager.get('ai_model.LM_STUDIO_MODEL'),
            'temperature': float(config_manager.get('ai_model.AI_TEMPERATURE')),on Module
Centralized configuration for telegram bot functionality
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add config directory to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
from config.config_manager import ConfigManager
config_manager = ConfigManager()

class TelegramBotConfig:
    """Configuration class for Telegram Bot"""
    
    def __init__(self):
        # Bot Token from JSON config - NO FALLBACKS!
        self.BOT_TOKEN = config_manager.get('security.TELEGRAM_BOT_TOKEN')
        
        # LM Studio Configuration - NO FALLBACKS!
        self.LM_STUDIO_CONFIG = {
            'base_url': config_manager.get('network.LM_STUDIO_BASE_URL'),
            'api_key': config_manager.get('ai_model.LM_STUDIO_API_KEY'),
            'model': config_manager.get('ai_model.LM_STUDIO_MODEL'),
            'temperature': float(config_manager.get('ai_model.AI_TEMPERATURE')),
            'timeout': None
        }
        
        # Database Configuration - Using JSON config
        self.DATABASE_CONFIG = {
            'chat_db': f"{config_manager.get('database.DATABASE_DIR')}/{config_manager.get('database.CHAT_DB_NAME')}",
            'wazuh_db': f"{config_manager.get('database.DATABASE_DIR')}/{config_manager.get('database.WAZUH_DB_NAME')}"
        }
        
        # PDF Configuration - Using JSON config - NO FALLBACKS!
        self.PDF_CONFIG = {
            'title_font_size': int(config_manager.get('reports.PDF_TITLE_FONT_SIZE')),
            'header_font_size': int(config_manager.get('pdf_reports.PDF_HEADER_FONT_SIZE')),
            'body_font_size': int(config_manager.get('reports.PDF_BODY_FONT_SIZE')),
            'page_size': config_manager.get('pdf_reports.PDF_PAGE_SIZE'),
            'margins': {
                'top': int(config_manager.get('pdf_reports.PDF_MARGIN_TOP')),
                'bottom': int(config_manager.get('pdf_reports.PDF_MARGIN_BOTTOM')),
                'left': int(config_manager.get('pdf_reports.PDF_MARGIN_LEFT')),
                'right': int(config_manager.get('pdf_reports.PDF_MARGIN_RIGHT'))
            }
        }
        
        # Authorized Users (loaded from config)
        self.AUTHORIZED_USERS = set()
        
        # Report Configuration - Using JSON config - NO FALLBACKS!
        self.REPORT_CONFIG = {
            'max_alerts_per_report': int(config_manager.get('pdf_reports.MAX_ALERTS_PER_REPORT')),
            'default_time_range_hours': int(config_manager.get('performance.DEFAULT_DAYS_RANGE')) * 24,
            'chart_colors': config_manager.get('pdf_reports.CHART_COLORS').split(','),
            'export_formats': config_manager.get('pdf_reports.EXPORT_FORMATS').split(',')
        }
        
        # Bot Commands Configuration
        self.BOT_COMMANDS = [
            ("start", "🚀 Show main menu"),
            ("menu", "📋 Return to main menu"),
            ("status", "🔧 Check system status"),
            ("help", "📖 Show help and commands"),
            ("enable_alerts", "🚨 Enable realtime alerts"),
            ("disable_alerts", "🔕 Disable realtime alerts"),
            ("alert_status", "📊 Check alert system status")
        ]

# Global instance
telegram_config = TelegramBotConfig()

# Export for backward compatibility
BOT_TOKEN = telegram_config.BOT_TOKEN
LM_STUDIO_CONFIG = telegram_config.LM_STUDIO_CONFIG
DATABASE_CONFIG = telegram_config.DATABASE_CONFIG
PDF_CONFIG = telegram_config.PDF_CONFIG
AUTHORIZED_USERS = telegram_config.AUTHORIZED_USERS
REPORT_CONFIG = telegram_config.REPORT_CONFIG
