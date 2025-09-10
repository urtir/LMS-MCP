#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot Configuration for Security Report System
"""

import os
from typing import Dict, List

class TelegramBotConfig:
    """Configuration for Telegram bot and reporting system"""
    
    # Bot Token (sudah disediakan user)
    BOT_TOKEN = "8289779353:AAG5TLJJP8JjwUJzQXMILAOG-7ufQA9ueM8"
    
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
            'time': '08:00',
            'interval_days': 3,
            'enabled': True,
            'recipients': ['admin', 'security_team']
        },
        'weekly': {
            'time': 'MON 08:00',
            'enabled': True,
            'recipients': ['admin', 'security_team', 'management']
        },
        'monthly': {
            'time': '1 08:00',  # 1st of month
            'enabled': True,
            'recipients': ['admin', 'security_team', 'management']
        }
    }
    
    # Report Types Configuration
    REPORT_TYPES = {
        'daily': {
            'name': 'Daily Security Report',
            'description': 'Laporan harian aktivitas keamanan',
            'emoji': '📊',
            'priority_levels': [6, 7],  # Critical events
            'max_events': 50
        },
        'three_daily': {
            'name': '3-Day Security Trend Report', 
            'description': 'Laporan tren keamanan 3 hari',
            'emoji': '📈',
            'priority_levels': [3, 6, 7],
            'max_events': 100
        },
        'weekly': {
            'name': 'Weekly Security Summary',
            'description': 'Ringkasan keamanan mingguan',
            'emoji': '📋',
            'priority_levels': [2, 3, 6, 7],
            'max_events': 200
        },
        'monthly': {
            'name': 'Monthly Security Assessment',
            'description': 'Penilaian keamanan bulanan',
            'emoji': '📅',
            'priority_levels': [1, 2, 3, 6, 7],
            'max_events': 500
        }
    }
    
    # LM Studio Configuration (existing)
    LM_STUDIO_CONFIG = {
        'base_url': "http://172.29.160.1:1234/v1",
        'api_key': "lm-studio",
        'model': "qwen/qwen3-1.7b",
        'max_tokens': 2000,
        'temperature': 0.3
    }
    
    # Database Configuration (existing)
    DATABASE_CONFIG = {
        'wazuh_db': 'wazuh_archives.db',
        'chat_db': 'chat_history.db'
    }
    
    # PDF Report Configuration
    PDF_CONFIG = {
        'page_size': 'A4',
        'font_family': 'Helvetica',
        'title_font_size': 24,
        'header_font_size': 16,
        'body_font_size': 12,
        'margin': 72  # 1 inch
    }
    
    # AI Analysis Configuration
    AI_CONFIG = {
        'threat_keywords': [
            'failed', 'denied', 'blocked', 'unauthorized', 'malware', 
            'virus', 'trojan', 'backdoor', 'brute', 'attack', 
            'suspicious', 'anomaly', 'intrusion', 'compromise'
        ],
        'critical_rule_levels': [6, 7],
        'high_frequency_threshold': 10,  # Events per hour
        'analysis_context_window': 7  # Days
    }
    
    # Bot Commands Configuration
    BOT_COMMANDS = [
        ('start', 'Memulai bot dan menampilkan menu utama'),
        ('daily_report', 'Generate laporan harian'),
        ('weekly_report', 'Generate laporan mingguan'),
        ('monthly_report', 'Generate laporan bulanan'),
        ('enable_alerts', 'Aktifkan alert realtime untuk critical events'),
        ('disable_alerts', 'Matikan alert realtime'),
        ('alert_status', 'Cek status sistem alert'),
        ('status', 'Cek status sistem'),
        ('help', 'Bantuan penggunaan bot'),
        ('settings', 'Pengaturan bot'),
        ('authorize', 'Otorisasi pengguna baru')
    ]
    
    # Security Keywords for RAG Enhancement
    SECURITY_KEYWORDS = {
        'authentication': ['login', 'ssh', 'rdp', 'authentication', 'logon'],
        'malware': ['malware', 'virus', 'trojan', 'backdoor', 'rootkit'],
        'network': ['connection', 'port', 'firewall', 'traffic', 'bandwidth'],
        'brute_force': ['brute', 'force', 'multiple', 'repeated', 'failed'],
        'data_exfiltration': ['download', 'upload', 'transfer', 'exfiltration', 'copy'],
        'system_compromise': ['privilege', 'escalation', 'exploit', 'vulnerability', 'compromise']
    }
