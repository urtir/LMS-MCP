#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Admin Configuration Backend
Manages JSON configuration through web interface
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Blueprint, request, jsonify, render_template, flash, redirect
from flask_login import login_required, current_user
from functools import wraps

# Add config directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.config_manager import ConfigManager
config = ConfigManager()

# Configure logging dengan detail level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Output ke terminal
        logging.FileHandler('logs/admin.log', mode='a')  # Output ke file log
    ]
)
logger = logging.getLogger(__name__)

# Set logging level to INFO untuk memastikan semua admin errors terlihat
logger.setLevel(logging.INFO)

# Tambahkan handler untuk memastikan error muncul di terminal
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)
console_formatter = logging.Formatter('🚨 ADMIN ERROR: %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

logger.info("Admin module loaded - comprehensive error logging enabled")

# Create Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin authorization decorator
def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            logger.info("User not authenticated, redirecting to login")
            return redirect('/login')
        
        # Debug logging
        logger.info(f"Admin check - Username: {current_user.username}, is_admin: {getattr(current_user, 'is_admin', False)}")
        
        # Check if user is admin
        if not getattr(current_user, 'is_admin', False):
            logger.warning(f"Access denied for user {current_user.username} - not admin")
            flash('Access denied. Admin privileges required.', 'error')
            return redirect('/')
        
        logger.info(f"Admin access granted for user {current_user.username}")
        return f(*args, **kwargs)
    return decorated_function

# Configuration categories and variables
CONFIG_CATEGORIES = {
    "security": {
        "name": "🔐 Security Configuration",
        "description": "Critical security settings and authentication",
        "variables": {
            "FLASK_SECRET_KEY": {
                "type": "password",
                "default": "your-secret-key-change-this-in-production",
                "description": "Flask session secret key - MUST be changed in production",
                "required": True,
                "validation": {"min_length": 32}
            },
            "TELEGRAM_BOT_TOKEN": {
                "type": "password", 
                "default": "YOUR_BOT_TOKEN_HERE",
                "description": "Telegram bot authentication token",
                "required": True,
                "validation": {"pattern": r"^\d+:[A-Za-z0-9_-]+$"}
            },
            "WAZUH_PASSWORD": {
                "type": "password",
                "default": "MyS3cr37P450r.*-",
                "description": "Wazuh API authentication password",
                "required": True,
                "validation": {"min_length": 8}
            }
        }
    },
    "network": {
        "name": "🌐 Network Configuration", 
        "description": "Network endpoints and connection settings",
        "variables": {
            "LM_STUDIO_BASE_URL": {
                "type": "url",
                "default": "http://192.168.56.1:1234/v1",
                "description": "LM Studio API endpoint URL",
                "required": True,
                "validation": {"pattern": r"^https?://.*"}
            },
            "WAZUH_API_URL": {
                "type": "url", 
                "default": "https://localhost:55000",
                "description": "Wazuh Manager API URL",
                "required": True,
                "validation": {"pattern": r"^https?://.*"}
            },
            "WAZUH_ARCHIVES_PATH": {
                "type": "text",
                "default": "/var/ossec/logs/archives/archives.json",
                "description": "Path to Wazuh archives JSON file",
                "required": True
            },
            "DOCKER_CONTAINER_NAME": {
                "type": "text",
                "default": "single-node-wazuh.manager-1", 
                "description": "Docker container name for Wazuh Manager",
                "required": True
            }
        }
    },
    "flask": {
        "name": "🐍 Flask Configuration",
        "description": "Flask application server settings",
        "variables": {
            "FLASK_HOST": {
                "type": "text",
                "default": "127.0.0.1",
                "description": "Flask server host address",
                "required": True,
                "validation": {"pattern": r"^(\d{1,3}\.){3}\d{1,3}$|^localhost$|^0\.0\.0\.0$"}
            },
            "FLASK_PORT": {
                "type": "number",
                "default": "5000",
                "description": "Flask server port number",
                "required": True,
                "validation": {"min": 1024, "max": 65535}
            },
            "FLASK_DEBUG": {
                "type": "boolean",
                "default": "false",
                "description": "Enable Flask debug mode (disable in production)",
                "required": False
            },
            "DASHBOARD_HOST": {
                "type": "text", 
                "default": "127.0.0.1",
                "description": "Dashboard server host address",
                "required": False
            },
            "DASHBOARD_PORT": {
                "type": "number",
                "default": "5000",
                "description": "Dashboard server port number", 
                "required": False,
                "validation": {"min": 1024, "max": 65535}
            },
            "DASHBOARD_DEBUG": {
                "type": "boolean",
                "default": "false",
                "description": "Enable dashboard debug mode",
                "required": False
            }
        }
    },
    "database": {
        "name": "🗄️ Database Configuration",
        "description": "Database paths and connection settings", 
        "variables": {
            "DATABASE_DIR": {
                "type": "text",
                "default": "./data",
                "description": "Directory path for database files",
                "required": True
            },
            "WAZUH_DB_NAME": {
                "type": "text",
                "default": "wazuh_archives.db",
                "description": "Wazuh database filename",
                "required": True
            },
            "CHAT_DB_NAME": {
                "type": "text", 
                "default": "chat_history.db",
                "description": "Chat history database filename",
                "required": True
            },
            "LOG_DIR": {
                "type": "text",
                "default": "./logs",
                "description": "Directory path for log files",
                "required": False
            }
        }
    },
    "ai_model": {
        "name": "🤖 AI Model Configuration",
        "description": "AI model parameters and limits",
        "variables": {
            "LM_STUDIO_API_KEY": {
                "type": "text",
                "default": "lm-studio", 
                "description": "LM Studio API authentication key",
                "required": True
            },
            "LM_STUDIO_MODEL": {
                "type": "text",
                "default": "qwen/qwen3-1.7b",
                "description": "LM Studio model identifier",
                "required": True
            },
            "AI_MAX_TOKENS": {
                "type": "number",
                "default": "2000",
                "description": "Maximum tokens for AI responses",
                "required": False,
                "validation": {"min": 100, "max": 32000}
            },
            "AI_TEMPERATURE": {
                "type": "number",
                "default": "0.3",
                "description": "AI model temperature (0.0-2.0)",
                "required": False,
                "validation": {"min": 0.0, "max": 2.0, "step": 0.1}
            }
        }
    },
    "performance": {
        "name": "⚡ Performance Configuration",
        "description": "Performance limits and optimization settings",
        "variables": {
            "MAX_LOG_LENGTH": {
                "type": "number",
                "default": "1000",
                "description": "Maximum log text length for processing",
                "required": False,
                "validation": {"min": 100, "max": 10000}
            },
            "MAX_RAG_CONTENT": {
                "type": "number",
                "default": "3000",
                "description": "Maximum RAG content length",
                "required": False,
                "validation": {"min": 500, "max": 20000}
            },
            "DEFAULT_MAX_RESULTS": {
                "type": "number",
                "default": "100",
                "description": "Default maximum search results",
                "required": False,
                "validation": {"min": 10, "max": 1000}
            },
            "CACHE_BUILD_LIMIT": {
                "type": "number",
                "default": "1000", 
                "description": "Maximum records for cache building",
                "required": False,
                "validation": {"min": 100, "max": 10000}
            }
        }
    },
    "security_thresholds": {
        "name": "🚨 Security Thresholds",
        "description": "Security monitoring and alerting thresholds",
        "variables": {
            "CRITICAL_RULE_LEVEL": {
                "type": "number",
                "default": "6",
                "description": "Minimum rule level considered critical",
                "required": False,
                "validation": {"min": 1, "max": 10}
            },
            "HIGH_RULE_LEVEL": {
                "type": "number",
                "default": "7", 
                "description": "Minimum rule level considered high priority",
                "required": False,
                "validation": {"min": 1, "max": 10}
            },
            "EMERGENCY_RULE_LEVEL": {
                "type": "number",
                "default": "8",
                "description": "Minimum rule level considered emergency",
                "required": False,
                "validation": {"min": 1, "max": 10}
            },
            "AGENT_ACTIVE_THRESHOLD": {
                "type": "number",
                "default": "100",
                "description": "Minimum alerts to consider agent active",
                "required": False,
                "validation": {"min": 1, "max": 10000}
            },
            "DEFAULT_DAYS_RANGE": {
                "type": "number",
                "default": "7",
                "description": "Default time range in days for queries",
                "required": False, 
                "validation": {"min": 1, "max": 365}
            }
        }
    },
    "wazuh": {
        "name": "🛡️ Wazuh Configuration",
        "description": "Wazuh API and integration settings",
        "variables": {
            "WAZUH_USERNAME": {
                "type": "text",
                "default": "wazuh-wui",
                "description": "Wazuh API username",
                "required": True
            },
            "WAZUH_VERIFY_SSL": {
                "type": "boolean", 
                "default": "false",
                "description": "Verify SSL certificates for Wazuh API",
                "required": False
            },
            "WAZUH_TIMEOUT": {
                "type": "number",
                "default": "30",
                "description": "Wazuh API request timeout in seconds",
                "required": False,
                "validation": {"min": 5, "max": 300}
            }
        }
    },
    "reports": {
        "name": "📊 Report Configuration", 
        "description": "Report generation and formatting settings",
        "variables": {
            "DAILY_MAX_EVENTS": {
                "type": "number",
                "default": "50",
                "description": "Maximum events in daily reports",
                "required": False,
                "validation": {"min": 10, "max": 1000}
            },
            "THREE_DAY_MAX_EVENTS": {
                "type": "number",
                "default": "100",
                "description": "Maximum events in 3-day trend reports",
                "required": False,
                "validation": {"min": 25, "max": 1500}
            },
            "WEEKLY_MAX_EVENTS": {
                "type": "number",
                "default": "200",
                "description": "Maximum events in weekly reports", 
                "required": False,
                "validation": {"min": 50, "max": 2000}
            },
            "MONTHLY_MAX_EVENTS": {
                "type": "number",
                "default": "500",
                "description": "Maximum events in monthly reports",
                "required": False,
                "validation": {"min": 100, "max": 5000}
            },
            "PDF_TITLE_FONT_SIZE": {
                "type": "number",
                "default": "24",
                "description": "PDF report title font size",
                "required": False,
                "validation": {"min": 12, "max": 48}
            },
            "PDF_BODY_FONT_SIZE": {
                "type": "number",
                "default": "12",
                "description": "PDF report body font size",
                "required": False,
                "validation": {"min": 8, "max": 24}
            }
        }
    }
}

def load_current_config() -> Dict[str, Any]:
    """Load current configuration from JSON"""
    try:
        logger.info("Loading current configuration from JSON")
        config_data = config.get_all()
        logger.info(f"Successfully loaded config with {len(config_data)} categories")
        return config_data
    except Exception as e:
        logger.error(f"ADMIN ERROR - Failed to load current configuration: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        return {}

def save_config_data(config_data: Dict[str, Any]) -> bool:
    """Save configuration data to JSON"""
    try:
        logger.info(f"Saving configuration data with {len(config_data)} categories")
        
        # Update each category
        for category, values in config_data.items():
            if category != 'meta':  # Skip meta information
                logger.info(f"Updating category '{category}' with {len(values)} variables")
                config.set_category(category, values)
        
        logger.info("Configuration saved successfully")
        return True
    except Exception as e:
        logger.error(f"ADMIN ERROR - Failed to save config: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        logger.error(f"Config data being saved: {config_data}")
        return False

def validate_variable(var_name: str, value: str, var_config: Dict) -> List[str]:
    """Validate a configuration variable"""
    errors = []
    
    try:
        logger.debug(f"Validating variable {var_name} with value: {value[:50]}..." if len(str(value)) > 50 else f"Validating variable {var_name} with value: {value}")
        
        if var_config.get('required', False) and not value:
            error_msg = f"{var_name} is required"
            errors.append(error_msg)
            logger.warning(f"Validation error: {error_msg}")
            return errors
        
        if not value:
            logger.debug(f"Variable {var_name} is empty but not required")
            return errors
        
        validation = var_config.get('validation', {})
        var_type = var_config.get('type', 'text')
        
        # Type-specific validation
        if var_type == 'number':
            try:
                num_value = float(value)
                if 'min' in validation and num_value < validation['min']:
                    error_msg = f"{var_name} must be at least {validation['min']}"
                    errors.append(error_msg)
                    logger.warning(f"Validation error: {error_msg}")
                if 'max' in validation and num_value > validation['max']:
                    error_msg = f"{var_name} must be at most {validation['max']}"
                    errors.append(error_msg)
                    logger.warning(f"Validation error: {error_msg}")
            except ValueError:
                error_msg = f"{var_name} must be a valid number"
                errors.append(error_msg)
                logger.warning(f"Validation error: {error_msg}")
        
        elif var_type == 'url':
            if not (value.startswith('http://') or value.startswith('https://')):
                error_msg = f"{var_name} must be a valid URL"
                errors.append(error_msg)
                logger.warning(f"Validation error: {error_msg}")
        
        elif var_type in ['text', 'password']:
            if 'min_length' in validation and len(value) < validation['min_length']:
                error_msg = f"{var_name} must be at least {validation['min_length']} characters"
                errors.append(error_msg)
                logger.warning(f"Validation error: {error_msg}")
            if 'pattern' in validation:
                import re
                if not re.match(validation['pattern'], value):
                    error_msg = f"{var_name} has invalid format"
                    errors.append(error_msg)
                    logger.warning(f"Validation error: {error_msg}")
        
        if not errors:
            logger.debug(f"Variable {var_name} validation passed")
            
        return errors
        
    except Exception as e:
        error_msg = f"Exception during validation of {var_name}: {e}"
        logger.error(f"ADMIN ERROR - {error_msg}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        errors.append(f"Validation error for {var_name}")
        return errors

# Routes
@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard"""
    return render_template('admin.html')

@admin_bp.route('/api/config')
@login_required
@admin_required
def get_config():
    """Get current configuration"""
    try:
        logger.info(f"Admin {current_user.username} requesting configuration")
        current_config = load_current_config()
        
        # Structure the response with categories
        result = {}
        for category_id, category in CONFIG_CATEGORIES.items():
            logger.debug(f"Processing category: {category_id}")
            result[category_id] = {
                'name': category['name'],
                'description': category['description'],
                'variables': {}
            }
            
            # Get current values from JSON config
            category_data = current_config.get(category_id, {})
            
            for var_name, var_info in category['variables'].items():
                result[category_id]['variables'][var_name] = {
                    **var_info,
                    'current_value': category_data.get(var_name, var_info['default'])
                }
        
        logger.info("Configuration retrieved successfully")
        return jsonify({
            'success': True,
            'config': result
        })
    
    except Exception as e:
        logger.error(f"ADMIN ERROR - Failed to get config for user {current_user.username}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@admin_bp.route('/api/config', methods=['POST'])
@login_required
@admin_required
def save_config_api():
    """Save configuration changes"""
    try:
        logger.info(f"Admin {current_user.username} attempting to save configuration")
        data = request.get_json()
        
        if not data:
            logger.warning(f"Admin {current_user.username} provided no data")
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        config_changes = data.get('config', {})
        logger.info(f"Received config changes for {len(config_changes)} categories")
        
        validation_errors = []
        
        # Validate all changes
        for category_id, variables in config_changes.items():
            if category_id not in CONFIG_CATEGORIES:
                logger.warning(f"Unknown category: {category_id}")
                continue
                
            logger.debug(f"Validating category '{category_id}' with {len(variables)} variables")
            
            for var_name, value in variables.items():
                if var_name not in CONFIG_CATEGORIES[category_id]['variables']:
                    logger.warning(f"Unknown variable '{var_name}' in category '{category_id}'")
                    continue
                    
                var_config = CONFIG_CATEGORIES[category_id]['variables'][var_name]
                errors = validate_variable(var_name, str(value), var_config)
                if errors:
                    logger.warning(f"Validation errors for {var_name}: {errors}")
                validation_errors.extend(errors)
        
        if validation_errors:
            logger.error(f"ADMIN ERROR - Validation failed for user {current_user.username}: {validation_errors}")
            return jsonify({
                'success': False,
                'errors': validation_errors
            }), 400
        
        # Save to JSON config
        if save_config_data(config_changes):
            logger.info(f"Configuration updated successfully by {current_user.username}")
            return jsonify({
                'success': True,
                'message': 'Configuration saved successfully'
            })
        else:
            logger.error(f"ADMIN ERROR - Failed to save configuration for user {current_user.username}")
            return jsonify({
                'success': False,
                'error': 'Failed to save configuration'
            }), 500
    
    except Exception as e:
        logger.error(f"ADMIN ERROR - Exception while saving config for user {current_user.username}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        logger.error(f"Request data: {request.get_json()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/api/validate')
@login_required
@admin_required
def validate_config():
    """Validate current configuration"""
    try:
        logger.info(f"Admin {current_user.username} validating configuration")
        current_config = load_current_config()
        validation_results = {}
        total_errors = 0
        
        for category_id, category in CONFIG_CATEGORIES.items():
            logger.debug(f"Validating category: {category_id}")
            validation_results[category_id] = {}
            category_data = current_config.get(category_id, {})
            
            for var_name, var_config in category['variables'].items():
                current_value = category_data.get(var_name, var_config['default'])
                errors = validate_variable(var_name, current_value, var_config)
                if errors:
                    total_errors += len(errors)
                    logger.warning(f"Validation errors for {category_id}.{var_name}: {errors}")
                
                validation_results[category_id][var_name] = {
                    'valid': len(errors) == 0,
                    'errors': errors,
                    'value': current_value
                }
        
        logger.info(f"Validation completed with {total_errors} total errors")
        return jsonify({
            'success': True,
            'validation': validation_results
        })
    
    except Exception as e:
        logger.error(f"ADMIN ERROR - Exception during validation for user {current_user.username}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/api/config/<category>', methods=['DELETE'])
@login_required
@admin_required
def delete_category(category):
    """Delete entire configuration category"""
    try:
        logger.info(f"Admin {current_user.username} deleting category: {category}")
        
        if category not in CONFIG_CATEGORIES:
            logger.warning(f"Invalid category deletion attempt: {category}")
            return jsonify({'success': False, 'error': 'Invalid category'}), 400
        
        # Reset category to defaults
        default_values = {}
        for var_name, var_info in CONFIG_CATEGORIES[category]['variables'].items():
            default_values[var_name] = var_info['default']
        
        config.set_category(category, default_values)
        logger.info(f"Category {category} reset to defaults successfully by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Category {category} reset to defaults'
        })
    
    except Exception as e:
        logger.error(f"ADMIN ERROR - Failed to delete category {category} for user {current_user.username}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/api/config/<category>/<variable>', methods=['DELETE'])
@login_required
@admin_required
def delete_variable(category, variable):
    """Delete specific configuration variable (reset to default)"""
    try:
        logger.info(f"Admin {current_user.username} deleting variable: {category}.{variable}")
        
        if category not in CONFIG_CATEGORIES:
            logger.warning(f"Invalid category for variable deletion: {category}")
            return jsonify({'success': False, 'error': 'Invalid category'}), 400
        
        if variable not in CONFIG_CATEGORIES[category]['variables']:
            logger.warning(f"Invalid variable deletion attempt: {category}.{variable}")
            return jsonify({'success': False, 'error': 'Invalid variable'}), 400
        
        # Reset to default value
        default_value = CONFIG_CATEGORIES[category]['variables'][variable]['default']
        config.set(f"{category}.{variable}", default_value)
        
        logger.info(f"Variable {category}.{variable} reset to default successfully by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Variable {variable} reset to default'
        })
    
    except Exception as e:
        logger.error(f"ADMIN ERROR - Failed to delete variable {category}.{variable} for user {current_user.username}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/api/backup', methods=['POST'])
@login_required
@admin_required
def backup_config():
    """Create configuration backup"""
    try:
        logger.info(f"Admin {current_user.username} creating configuration backup")
        backup_file = config.backup_config()
        logger.info(f"Configuration backup created successfully by {current_user.username}: {backup_file}")
        
        return jsonify({
            'success': True,
            'message': 'Configuration backup created',
            'backup_file': backup_file
        })
    
    except Exception as e:
        logger.error(f"ADMIN ERROR - Failed to create backup for user {current_user.username}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/api/restart', methods=['POST'])
@login_required
@admin_required
def restart_application():
    """Restart application (placeholder - implement based on deployment)"""
    try:
        logger.info(f"Admin {current_user.username} requesting application restart")
        
        # This is a placeholder - implement based on your deployment method
        logger.warning("Application restart requested - implement based on deployment method")
        
        return jsonify({
            'success': True,
            'message': 'Restart signal sent. Please manually restart the application.'
        })
    except Exception as e:
        logger.error(f"ADMIN ERROR - Failed to restart application for user {current_user.username}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500