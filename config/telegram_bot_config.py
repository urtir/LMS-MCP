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
    
    # Bot Token from JSON config
    BOT_TOKEN = config.get('security.TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    
    # Chat IDs for different user groups (akan diisi saat bot dijalankan)
    AUTHORIZED_USERS = {
        'admin': [],        # Admin chat IDs
        'security_team': [], # Security team chat IDs  
        'management': []     # Management chat IDs
    }
    
    # Report Schedule Configuration
    REPORT_SCHEDULES = {
        'daily': {
            'time': '08:00',
            'enabled': True,
            'recipients': ['admin', 'security_team']
        },
        'three_daily': {
            'time': '20:00',
            'enabled': True,
            'recipients': ['admin', 'security_team']
        },
        'weekly': {
            'time': '09:00',  # Senin pagi
            'enabled': True,
            'recipients': ['admin', 'security_team', 'management']
        },
        'monthly': {
            'time': '10:00',  # Tanggal 1 setiap bulan
            'enabled': True,
            'recipients': ['admin', 'security_team', 'management']
        }
    }
    
    # Report Types Configuration using JSON config
    REPORT_TYPES = {
        'daily_summary': {
            'name': '📊 Daily Summary Report',
            'description': 'Summary of last 24 hours security events',
            'function': 'get_daily_summary',
            'max_events': int(config.get('reports.DAILY_MAX_EVENTS', '50'))
        },
        'agent_activity': {
            'name': '👥 Agent Activity Report', 
            'description': 'Activity summary of Wazuh agents',
            'function': 'get_agent_activity',
            'max_events': int(config.get('reports.THREE_DAY_MAX_EVENTS', '100'))
        },
        'threat_trends': {
            'name': '🔥 Threat Trends (7 Days)',
            'description': 'Trending security threats over 7 days',
            'function': 'get_threat_trends',
            'max_events': int(config.get('reports.WEEKLY_MAX_EVENTS', '200'))
        },
        'monthly_overview': {
            'name': '📈 Monthly Security Overview',
            'description': 'Comprehensive monthly security overview', 
            'function': 'get_monthly_overview',
            'max_events': int(config.get('reports.MONTHLY_MAX_EVENTS', '500'))
        }
    }

# LM Studio Configuration using JSON config
LM_STUDIO_CONFIG = {
    'base_url': config.get('ai_model.LM_STUDIO_BASE_URL', "http://192.168.56.1:1234/v1"),
    'api_key': config.get('ai_model.LM_STUDIO_API_KEY', "lm-studio"),
    'model': config.get('ai_model.LM_STUDIO_MODEL', "qwen/qwen3-1.7b"),
    'max_tokens': int(config.get('ai_model.AI_MAX_TOKENS', '2000')),
    'temperature': float(config.get('ai_model.AI_TEMPERATURE', '0.3'))
}

# Database Configuration using JSON config
DATABASE_CONFIG = {
    'wazuh_db': f"{config.get('database.DATABASE_DIR', './data')}/{config.get('database.WAZUH_DB_NAME', 'wazuh_archives.db')}",
    'chat_db': f"{config.get('database.DATABASE_DIR', './data')}/{config.get('database.CHAT_DB_NAME', 'chat_history.db')}"
}

# Model Configuration
MODEL_CONFIG = {
    'model_name': 'all-MiniLM-L6-v2',
    'device': 'cuda'  # Use GPU if available
}

# FastMCP Server Configuration
FASTMCP_SERVER = {
    'module': 'src.api.wazuh_fastmcp_server',
    'host': 'localhost',
    'port': 3000
}

# Performance Configuration using JSON config
PERFORMANCE_CONFIG = {
    'max_log_length': int(config.get('performance.MAX_LOG_LENGTH', '1000')),
    'max_rag_content': int(config.get('performance.MAX_RAG_CONTENT', '3000')),
    'default_max_results': int(config.get('performance.DEFAULT_MAX_RESULTS', '100')),
    'cache_build_limit': int(config.get('performance.CACHE_BUILD_LIMIT', '1000'))
}

# Security Thresholds using JSON config
SECURITY_THRESHOLDS = {
    'critical_rule_level': int(config.get('security_thresholds.CRITICAL_RULE_LEVEL', '6')),
    'high_rule_level': int(config.get('security_thresholds.HIGH_RULE_LEVEL', '7')),
    'emergency_rule_level': int(config.get('security_thresholds.EMERGENCY_RULE_LEVEL', '8')),
    'agent_active_threshold': int(config.get('security_thresholds.AGENT_ACTIVE_THRESHOLD', '100')),
    'default_days_range': int(config.get('security_thresholds.DEFAULT_DAYS_RANGE', '7'))
}

# PDF Report Configuration using JSON config
PDF_CONFIG = {
    'title_font_size': int(config.get('reports.PDF_TITLE_FONT_SIZE', '24')),
    'body_font_size': int(config.get('reports.PDF_BODY_FONT_SIZE', '12')),
    'max_events_per_page': 50,
    'include_charts': True,
    'watermark': 'LMS MCP Security Report'
}

# Alert Configuration
ALERT_CONFIG = {
    'enable_realtime': True,
    'critical_alert_chat_ids': [],  # Will be populated at runtime
    'alert_cooldown': 300,  # 5 minutes cooldown between same alerts
    'max_alerts_per_hour': 20
}

# Command Configuration
COMMAND_CONFIG = {
    'enable_admin_commands': True,
    'enable_user_commands': True,
    'command_timeout': 30,  # seconds
    'max_concurrent_commands': 5
}