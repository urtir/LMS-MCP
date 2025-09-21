#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script untuk memastikan admin error logging berfungsi
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from config.config_manager import ConfigManager
from src.webapp.admin import validate_variable, CONFIG_CATEGORIES

def test_admin_error_logging():
    """Test various error scenarios untuk memastikan logging bekerja"""
    
    print("🧪 Testing Admin Error Logging...")
    
    # Test 1: ConfigManager error
    try:
        print("\n1. Testing ConfigManager errors...")
        config = ConfigManager()
        # Try to get non-existent config
        result = config.get("non_existent.VARIABLE", None)
        print(f"   Non-existent config result: {result}")
    except Exception as e:
        print(f"   ConfigManager error logged: {e}")
    
    # Test 2: Validation errors
    try:
        print("\n2. Testing validation errors...")
        
        # Test invalid number
        var_config = {
            "type": "number",
            "validation": {"min": 10, "max": 100},
            "required": True
        }
        errors = validate_variable("TEST_NUMBER", "5", var_config)
        print(f"   Validation errors for number < min: {errors}")
        
        # Test invalid URL
        var_config = {
            "type": "url",
            "required": True
        }
        errors = validate_variable("TEST_URL", "not-a-url", var_config)
        print(f"   Validation errors for invalid URL: {errors}")
        
        # Test required field empty
        var_config = {
            "type": "text",
            "required": True
        }
        errors = validate_variable("TEST_REQUIRED", "", var_config)
        print(f"   Validation errors for empty required field: {errors}")
        
    except Exception as e:
        print(f"   Validation testing error: {e}")
    
    # Test 3: Simulasi JSON config error
    try:
        print("\n3. Testing JSON config save error...")
        config = ConfigManager()
        
        # Test dengan data yang valid
        test_data = {
            "security": {
                "FLASK_SECRET_KEY": "test-key-12345678901234567890123",
                "TELEGRAM_BOT_TOKEN": "123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
            }
        }
        
        # Try to save
        from src.webapp.admin import save_config_data
        result = save_config_data(test_data)
        print(f"   Config save result: {result}")
        
    except Exception as e:
        print(f"   Config save error logged: {e}")
    
    # Test 4: Load config error
    try:
        print("\n4. Testing config load...")
        from src.webapp.admin import load_current_config
        current_config = load_current_config()
        print(f"   Config loaded with {len(current_config)} categories")
        
    except Exception as e:
        print(f"   Config load error logged: {e}")
    
    print("\n✅ Admin error logging test completed!")
    print("Check terminal output and logs/admin.log for detailed error logging")

if __name__ == "__main__":
    test_admin_error_logging()