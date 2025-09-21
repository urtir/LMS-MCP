"""
Telegram Bot Configuration Module
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
        # Bot Token from JSON config
        self.BOT_TOKEN = config_manager.get('security.TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
        
        # LM Studio Configuration
        self.LM_STUDIO_CONFIG = {
            'base_url': config_manager.get('ai_model.LM_STUDIO_BASE_URL', 'http://192.168.56.1:1234/v1'),
            'api_key': config_manager.get('ai_model.LM_STUDIO_API_KEY', 'lm-studio'),
            'model': config_manager.get('ai_model.LM_STUDIO_MODEL', 'qwen/qwen3-1.7b'),
            'temperature': float(config_manager.get('ai_model.AI_TEMPERATURE', '0.8')),
            'timeout': None  # No timeout
        }
        
        # Database Configuration
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent
        
        self.DATABASE_CONFIG = {
            'chat_db': str(project_root / 'data' / 'chat_history.db'),
            'wazuh_db': str(project_root / 'data' / 'wazuh_archives.db')
        }
        
        # PDF Configuration
        self.PDF_CONFIG = {
            'title_font_size': 18,
            'header_font_size': 14,
            'body_font_size': 10,
            'page_size': 'A4',
            'margins': {
                'top': 72,
                'bottom': 72,
                'left': 72,
                'right': 72
            }
        }
        
        # Authorized Users (can be loaded from database or config file)
        self.AUTHORIZED_USERS = set()
        
        # Report Configuration
        self.REPORT_CONFIG = {
            'max_alerts_per_report': 1000,
            'default_time_range_hours': 24,
            'chart_colors': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'],
            'export_formats': ['pdf', 'json', 'csv']
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
