#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot Configuration Module
Centralized configuration management for Telegram bot
"""

import sys
from pathlib import Path
from typing import Dict, List

# Add config directory to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / 'config'))
from config_manager import config

class TelegramBotConfig:
    """Configuration for Telegram bot and reporting system using JSON config"""
    
    # Bot Token from JSON config - NO FALLBACKS!
    BOT_TOKEN = config.get('security.TELEGRAM_BOT_TOKEN')
    
    # Chat IDs for different user groups (akan diisi saat bot dijalankan)
    AUTHORIZED_USERS = {
        'admin': [],        # Admin chat IDs
        'security_team': [], # Security team chat IDs  
        'management': []     # Management chat IDs
    }
    
    # Report Schedule Configuration - Using JSON config - NO FALLBACKS!
    REPORT_SCHEDULES = {
        'daily': {
            'time': config.get('telegram_reports.DAILY_REPORT_TIME'),
            'enabled': config.get('telegram_reports.DAILY_REPORT_ENABLED').lower() == 'true',
            'recipients': config.get('telegram_reports.DAILY_REPORT_RECIPIENTS').split(',')
        },
        'three_daily': {
            'time': config.get('telegram_reports.THREE_DAILY_REPORT_TIME'),
            'enabled': config.get('telegram_reports.THREE_DAILY_REPORT_ENABLED').lower() == 'true',
            'recipients': config.get('telegram_reports.THREE_DAILY_REPORT_RECIPIENTS').split(',')
        },
        'weekly': {
            'time': config.get('telegram_reports.WEEKLY_REPORT_TIME'),
            'enabled': config.get('telegram_reports.WEEKLY_REPORT_ENABLED').lower() == 'true',
            'recipients': config.get('telegram_reports.WEEKLY_REPORT_RECIPIENTS').split(',')
        },
        'monthly': {
            'time': config.get('telegram_reports.MONTHLY_REPORT_TIME'),
            'enabled': config.get('telegram_reports.MONTHLY_REPORT_ENABLED').lower() == 'true',
            'recipients': config.get('telegram_reports.MONTHLY_REPORT_RECIPIENTS').split(',')
        }
    }
    
    # Report Types Configuration using JSON config
    REPORT_TYPES = {
        'daily': {
            'name': '📊 Daily Summary Report',
            'description': 'Summary of last 24 hours security events',
            'emoji': '📊',
            'priority_levels': list(range(5, 17)),  # Rule levels 5-16
            'read_all_events': False,
            'max_events': int(config.get('reports.DAILY_MAX_EVENTS', '100'))
        },
        'three_daily': {
            'name': '� 3-Day Trend Report',
            'description': 'Security trends over last 3 days',
            'emoji': '📈',
            'priority_levels': list(range(5, 17)),  # Rule levels 5-16
            'read_all_events': True,
            'max_events': int(config.get('reports.THREE_DAY_MAX_EVENTS', '300'))
        },
        'weekly': {
            'name': '� Weekly Summary Report',
            'description': 'Weekly security overview',
            'emoji': '📅',
            'priority_levels': list(range(5, 17)),  # Rule levels 5-16
            'read_all_events': False,
            'max_events': int(config.get('reports.WEEKLY_MAX_EVENTS', '500'))
        },
        'monthly': {
            'name': '📈 Monthly Security Overview',
            'description': 'Comprehensive monthly security overview',
            'emoji': '📈',
            'priority_levels': list(range(5, 17)),  # Rule levels 5-16
            'read_all_events': True,
            'max_events': int(config.get('reports.MONTHLY_MAX_EVENTS', '1000'))
        }
    }

    # LM Studio Configuration using JSON config - NO FALLBACKS!
    LM_STUDIO_CONFIG = {
        'base_url': config.get('network.LM_STUDIO_BASE_URL'),
        'api_key': config.get('ai_model.LM_STUDIO_API_KEY'),
        'model': config.get('ai_model.LM_STUDIO_MODEL'),
        'max_tokens': int(config.get('ai_model.AI_MAX_TOKENS')),
        'temperature': float(config.get('ai_model.AI_TEMPERATURE'))
    }

    # Database Configuration using JSON config - NO FALLBACKS!
    DATABASE_CONFIG = {
        'wazuh_db': f"{config.get('database.DATABASE_DIR')}/{config.get('database.WAZUH_DB_NAME')}",
        'chat_db': f"{config.get('database.DATABASE_DIR')}/{config.get('database.CHAT_DB_NAME')}"
    }

    # Model Configuration using JSON config - NO FALLBACKS!
    MODEL_CONFIG = {
        'model_name': config.get('ml_models.SENTENCE_TRANSFORMER_MODEL'),
        'device': config.get('ml_models.ML_DEVICE'),
        'cache_size': int(config.get('ml_models.EMBEDDING_CACHE_SIZE'))
    }

    # FastMCP Server Configuration using JSON config - NO FALLBACKS!
    FASTMCP_SERVER = {
        'module': config.get('fastmcp.FASTMCP_MODULE'),
        'host': config.get('fastmcp.FASTMCP_HOST'),
        'port': int(config.get('fastmcp.FASTMCP_PORT')),
        'timeout': int(config.get('fastmcp.FASTMCP_TIMEOUT'))
    }

    # Performance Configuration using JSON config - NO FALLBACKS!
    PERFORMANCE_CONFIG = {
        'max_log_length': int(config.get('performance.MAX_LOG_LENGTH')),
        'max_rag_content': int(config.get('performance.MAX_RAG_CONTENT')),
        'default_max_results': int(config.get('performance.DEFAULT_MAX_RESULTS')),
        'cache_build_limit': int(config.get('performance.CACHE_BUILD_LIMIT'))
    }

    # Security Thresholds using JSON config - NO FALLBACKS!
    SECURITY_THRESHOLDS = {
        'critical_rule_level': int(config.get('security_thresholds.CRITICAL_RULE_LEVEL')),
        'high_rule_level': int(config.get('security_thresholds.HIGH_RULE_LEVEL')),
        'emergency_rule_level': int(config.get('security_thresholds.EMERGENCY_RULE_LEVEL')),
        'agent_active_threshold': int(config.get('security_thresholds.AGENT_ACTIVE_THRESHOLD')),
        'default_days_range': int(config.get('security_thresholds.DEFAULT_DAYS_RANGE'))
    }

    # PDF Report Configuration using JSON config - NO FALLBACKS!
    PDF_CONFIG = {
        'title_font_size': int(config.get('reports.PDF_TITLE_FONT_SIZE')),
        'body_font_size': int(config.get('reports.PDF_BODY_FONT_SIZE')),
        'max_events_per_page': int(config.get('pdf_reports.PDF_MAX_EVENTS_PER_PAGE')),
        'include_charts': config.get('pdf_reports.PDF_INCLUDE_CHARTS').lower() == 'true',
        'watermark': config.get('pdf_reports.PDF_WATERMARK_TEXT'),
        'compression_level': int(config.get('pdf_reports.PDF_COMPRESSION_LEVEL'))
    }

    # Alert Configuration using JSON config - NO FALLBACKS!
    ALERT_CONFIG = {
        'enable_realtime': config.get('alerts.ENABLE_REALTIME_ALERTS').lower() == 'true',
        'critical_alert_chat_ids': [],  # Will be populated at runtime
        'alert_cooldown': int(config.get('alerts.ALERT_COOLDOWN_SECONDS')),
        'max_alerts_per_hour': int(config.get('alerts.MAX_ALERTS_PER_HOUR'))
    }

    # Command Configuration using JSON config - NO FALLBACKS!
    COMMAND_CONFIG = {
        'enable_admin_commands': config.get('alerts.ENABLE_ADMIN_COMMANDS').lower() == 'true',
        'enable_user_commands': config.get('alerts.ENABLE_USER_COMMANDS').lower() == 'true',
        'command_timeout': int(config.get('alerts.COMMAND_TIMEOUT_SECONDS')),
        'max_concurrent_commands': int(config.get('alerts.MAX_CONCURRENT_COMMANDS'))
    }