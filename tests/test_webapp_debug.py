#!/usr/bin/env python3
"""
Test script untuk debug webapp chatbot dengan enhanced logging
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("🔧 Starting webapp with debug logging...")
print(f"Project root: {project_root}")
print(f"Python path: {sys.path}")

try:
    # Import dan jalankan webapp
    from src.webapp.webapp_chatbot import app, logger
    
    print("\n✅ Webapp imported successfully!")
    print(f"Flask app: {app}")
    print(f"Logger: {logger}")
    
    # Print konfigurasi
    from src.webapp.webapp_chatbot import LM_STUDIO_CONFIG, FLASK_CONFIG
    print(f"\n📋 Configuration:")
    print(f"LM Studio: {LM_STUDIO_CONFIG}")
    print(f"Flask: {FLASK_CONFIG}")
    
    # Test basic route
    with app.test_client() as client:
        print("\n🧪 Testing basic routes...")
        
        # Test landing page
        response = client.get('/')
        print(f"GET / -> Status: {response.status_code}")
        
        # Test API status
        response = client.get('/api/status')
        print(f"GET /api/status -> Status: {response.status_code}")
        
    print("\n🚀 Starting Flask development server...")
    print("Logs akan muncul di terminal ini dan di logs/webapp_chatbot.log")
    print("Ctrl+C untuk stop server")
    
    # Jalankan Flask app
    app.run(
        host=FLASK_CONFIG['host'],
        port=FLASK_CONFIG['port'],
        debug=FLASK_CONFIG['debug']
    )
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()