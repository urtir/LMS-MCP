#!/usr/bin/env python3
"""
Configuration file for Wazuh Real-time Server
"""

import os
from pathlib import Path

# Database Configuration
DATABASE_CONFIG = {
    'db_path': 'wazuh_archives.db',
    'wal_mode': True,
    'backup_enabled': True,
    'backup_interval_hours': 24
}

# Docker Configuration
DOCKER_CONFIG = {
    'container_name': 'single-node-wazuh.manager-1',
    'archives_path': '/var/ossec/logs/archives/archives.json',
    'connection_timeout': 30,
    'max_retries': 3
}

# Fetching Configuration
FETCH_CONFIG = {
    'interval_seconds': 5,
    'batch_size': 100,
    'max_file_size_mb': 1000,  # Skip if file is larger than this
    'enable_compression': False
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'log_file': 'wazuh_realtime.log',
    'max_file_size_mb': 10,
    'backup_count': 5,
    'console_output': True
}

# Alert Thresholds
ALERT_CONFIG = {
    'high_level_threshold': 10,
    'critical_level_threshold': 15,
    'notification_enabled': False,
    'notification_webhook': None
}

# Performance Settings
PERFORMANCE_CONFIG = {
    'use_threading': True,
    'max_workers': 2,
    'memory_limit_mb': 512,
    'sqlite_pragma': {
        'journal_mode': 'WAL',
        'synchronous': 'NORMAL',
        'cache_size': 10000,
        'temp_store': 'MEMORY'
    }
}

def get_config():
    """Get complete configuration dictionary."""
    return {
        'database': DATABASE_CONFIG,
        'docker': DOCKER_CONFIG,
        'fetch': FETCH_CONFIG,
        'logging': LOGGING_CONFIG,
        'alerts': ALERT_CONFIG,
        'performance': PERFORMANCE_CONFIG
    }

def validate_config():
    """Validate configuration settings."""
    errors = []
    
    # Check if Docker is available
    try:
        import docker
        client = docker.from_env()
        client.ping()
    except Exception as e:
        errors.append(f"Docker not available: {e}")
    
    # Check database path is writable
    db_path = DATABASE_CONFIG['db_path']
    db_dir = Path(db_path).parent
    if not db_dir.exists():
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create database directory: {e}")
    
    # Check log file path is writable
    log_path = LOGGING_CONFIG['log_file']
    log_dir = Path(log_path).parent
    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create log directory: {e}")
    
    return errors

if __name__ == "__main__":
    print("Wazuh Real-time Server Configuration")
    print("=" * 40)
    
    config = get_config()
    for section, settings in config.items():
        print(f"\n[{section.upper()}]")
        for key, value in settings.items():
            print(f"  {key}: {value}")
    
    print("\nValidating configuration...")
    errors = validate_config()
    
    if errors:
        print("Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Configuration is valid!")
