#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Centralized Configuration Manager
Handles all configuration through JSON file storage
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from threading import Lock

logger = logging.getLogger(__name__)

class ConfigManager:
    """Centralized configuration management using JSON storage"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.config_file = Path(__file__).parent / 'config.json'
            self.initialized = True
            self._ensure_config_exists()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration structure"""
        return {
            "meta": {
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "description": "LMS MCP Centralized Configuration"
            },
            "security": {
                "FLASK_SECRET_KEY": "your-secret-key-change-this-in-production",
                "TELEGRAM_BOT_TOKEN": "YOUR_BOT_TOKEN_HERE",
                "WAZUH_PASSWORD": "MyS3cr37P450r.*-"
            },
            "network": {
                "LM_STUDIO_BASE_URL": "http://192.168.56.1:1234/v1",
                "WAZUH_API_URL": "https://localhost:55000",
                "WAZUH_ARCHIVES_PATH": "/var/ossec/logs/archives/archives.json",
                "DOCKER_CONTAINER_NAME": "single-node-wazuh.manager-1"
            },
            "flask": {
                "FLASK_HOST": "127.0.0.1",
                "FLASK_PORT": "5000",
                "FLASK_DEBUG": "false"
            },
            "database": {
                "DATABASE_DIR": "./data",
                "WAZUH_DB_NAME": "wazuh_archives.db",
                "CHAT_DB_NAME": "chat_history.db",
                "LOG_DIR": "./logs"
            },
            "ai_model": {
                "LM_STUDIO_API_KEY": "lm-studio",
                "LM_STUDIO_MODEL": "qwen/qwen3-1.7b",
                "AI_MAX_TOKENS": "2000",
                "AI_TEMPERATURE": "0.3"
            },
            "performance": {
                "MAX_LOG_LENGTH": "1000",
                "MAX_RAG_CONTENT": "3000",
                "DEFAULT_MAX_RESULTS": "100",
                "CACHE_BUILD_LIMIT": "1000"
            },
            "security_thresholds": {
                "CRITICAL_RULE_LEVEL": "6",
                "HIGH_RULE_LEVEL": "7",
                "EMERGENCY_RULE_LEVEL": "8",
                "AGENT_ACTIVE_THRESHOLD": "100",
                "DEFAULT_DAYS_RANGE": "7"
            },
            "wazuh": {
                "WAZUH_USERNAME": "wazuh-wui",
                "WAZUH_VERIFY_SSL": "false",
                "WAZUH_TIMEOUT": "30"
            },
            "reports": {
                "DAILY_MAX_EVENTS": "50",
                "THREE_DAY_MAX_EVENTS": "100",
                "WEEKLY_MAX_EVENTS": "200",
                "MONTHLY_MAX_EVENTS": "500",
                "PDF_TITLE_FONT_SIZE": "24",
                "PDF_BODY_FONT_SIZE": "12"
            },
            "ml_models": {
                "SENTENCE_TRANSFORMER_MODEL": "all-MiniLM-L6-v2",
                "ML_DEVICE": "cuda",
                "EMBEDDING_CACHE_SIZE": "1000"
            },
            "fastmcp": {
                "FASTMCP_MODULE": "src.api.wazuh_fastmcp_server",
                "FASTMCP_HOST": "localhost",
                "FASTMCP_PORT": "3000",
                "FASTMCP_TIMEOUT": "30"
            },
            "alerts": {
                "ENABLE_REALTIME_ALERTS": "true",
                "ALERT_COOLDOWN_SECONDS": "300",
                "MAX_ALERTS_PER_HOUR": "20",
                "ENABLE_ADMIN_COMMANDS": "true",
                "ENABLE_USER_COMMANDS": "true",
                "COMMAND_TIMEOUT_SECONDS": "30",
                "MAX_CONCURRENT_COMMANDS": "5"
            },
            "pdf_reports": {
                "PDF_MAX_EVENTS_PER_PAGE": "50",
                "PDF_INCLUDE_CHARTS": "true",
                "PDF_WATERMARK_TEXT": "LMS MCP Security Report",
                "PDF_COMPRESSION_LEVEL": "6",
                "PDF_HEADER_FONT_SIZE": "14",
                "PDF_PAGE_SIZE": "A4",
                "PDF_MARGIN_TOP": "72",
                "PDF_MARGIN_BOTTOM": "72",
                "PDF_MARGIN_LEFT": "72",
                "PDF_MARGIN_RIGHT": "72",
                "CHART_COLORS": "#FF6B6B,#4ECDC4,#45B7D1,#96CEB4,#FFEAA7",
                "EXPORT_FORMATS": "pdf,json,csv",
                "MAX_ALERTS_PER_REPORT": "1000"
            },
            "telegram_reports": {
                "DAILY_REPORT_TIME": "08:00",
                "DAILY_REPORT_ENABLED": "true",
                "DAILY_REPORT_RECIPIENTS": "admin,security_team",
                "THREE_DAILY_REPORT_TIME": "20:00",
                "THREE_DAILY_REPORT_ENABLED": "true",
                "THREE_DAILY_REPORT_RECIPIENTS": "admin,security_team",
                "WEEKLY_REPORT_TIME": "09:00",
                "WEEKLY_REPORT_ENABLED": "true",
                "WEEKLY_REPORT_RECIPIENTS": "admin,security_team,management",
                "MONTHLY_REPORT_TIME": "10:00",
                "MONTHLY_REPORT_ENABLED": "true",
                "MONTHLY_REPORT_RECIPIENTS": "admin,security_team,management"
            }
        }
    
    def _ensure_config_exists(self):
        """Ensure configuration file exists with default values"""
        if not self.config_file.exists():
            self.config_file.parent.mkdir(exist_ok=True)
            default_config = self._get_default_config()
            self._write_config(default_config)
            logger.info(f"Created default configuration at {self.config_file}")
    
    def _read_config(self) -> Dict[str, Any]:
        """Read configuration from JSON file"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error reading config: {e}")
            raise
    
    def _write_config(self, config: Dict[str, Any]):
        """Write configuration to JSON file"""
        try:
            config["meta"]["last_updated"] = datetime.now().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error writing config: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)"""
        try:
            config = self._read_config()
            
            # Support dot notation (e.g., "security.FLASK_SECRET_KEY")
            keys = key.split('.')
            value = config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
        except Exception:
            return default
    
    def set(self, key: str, value: Any):
        """Set configuration value by key (supports dot notation)"""
        config = self._read_config()
        
        # Support dot notation
        keys = key.split('.')
        current = config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the value
        current[keys[-1]] = value
        self._write_config(config)
        logger.info(f"Updated config: {key} = {value}")
    
    def get_category(self, category: str) -> Dict[str, Any]:
        """Get entire configuration category"""
        config = self._read_config()
        return config.get(category, {})
    
    def set_category(self, category: str, values: Dict[str, Any]):
        """Set entire configuration category"""
        config = self._read_config()
        config[category] = values
        self._write_config(config)
        logger.info(f"Updated category: {category}")
    
    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration"""
        return self._read_config()
    
    def update_multiple(self, updates: Dict[str, Any]):
        """Update multiple configuration values at once"""
        config = self._read_config()
        
        for key, value in updates.items():
            keys = key.split('.')
            current = config
            
            # Navigate to parent
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # Set value
            current[keys[-1]] = value
        
        self._write_config(config)
        logger.info(f"Updated {len(updates)} configuration values")
    
    def delete(self, key: str):
        """Delete configuration value by key"""
        config = self._read_config()
        
        keys = key.split('.')
        current = config
        
        # Navigate to parent
        for k in keys[:-1]:
            if k not in current:
                return  # Key doesn't exist
            current = current[k]
        
        # Delete the key
        if keys[-1] in current:
            del current[keys[-1]]
            self._write_config(config)
            logger.info(f"Deleted config key: {key}")
    
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        default_config = self._get_default_config()
        self._write_config(default_config)
        logger.info("Configuration reset to defaults")
    
    def backup_config(self) -> str:
        """Create backup of current configuration"""
        backup_file = self.config_file.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        config = self._read_config()
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Configuration backed up to {backup_file}")
        return str(backup_file)

# Global configuration instance
config = ConfigManager()

# Convenience functions for backward compatibility
def get_config(key: str, default: Any = None) -> Any:
    """Get configuration value"""
    return config.get(key, default)

def set_config(key: str, value: Any):
    """Set configuration value"""
    config.set(key, value)

def get_category_config(category: str) -> Dict[str, Any]:
    """Get configuration category"""
    return config.get_category(category)