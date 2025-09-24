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

    def _ensure_config_exists(self):
        """Ensure configuration file exists - NO DEFAULTS!"""
        if not self.config_file.exists():
            self.config_file.parent.mkdir(exist_ok=True)
            # NO DEFAULT CONFIG - USER MUST PROVIDE ALL VALUES!
            raise ValueError(f"Configuration file does not exist: {self.config_file}. Please create it with all required values.")
    
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
        """Get configuration value by key (supports dot notation) - NO DEFAULTS ALLOWED!"""
        try:
            config = self._read_config()
            
            # Support dot notation (e.g., "security.FLASK_SECRET_KEY")
            keys = key.split('.')
            value = config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    raise ValueError(f"Configuration key '{key}' not found! Please add it to config.json")
            
            if value is None or value == "":
                raise ValueError(f"Configuration key '{key}' is empty! Please set a value in config.json")
            
            return value
        except Exception as e:
            if "not found" in str(e) or "is empty" in str(e):
                raise e
            raise ValueError(f"Error reading configuration key '{key}': {e}")
    
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
        """Reset configuration to default values - DISABLED"""
        # NO DEFAULT CONFIG - USER MUST PROVIDE ALL VALUES!
        raise ValueError("Reset to defaults disabled - no default configuration exists!")
    
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