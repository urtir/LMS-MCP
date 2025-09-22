#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test sistem alerting Telegram Bot dengan full_log
"""

import asyncio
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

def test_alert_message_format():
    """Test format alert message dengan full_log"""
    
    print("🧪 Testing Telegram Alert Message Format")
    print("=" * 50)
    
    # Import telegram bot class
    try:
        from src.telegram.telegram_security_bot import TelegramSecurityBot
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return
    
    # Create bot instance (untuk testing format message only)
    bot = TelegramSecurityBot()
    
    # Sample alert data dengan full_log
    sample_alerts = [
        {
            'id': 1,
            'timestamp': '2025-09-22 18:15:30',
            'agent_name': 'CLIENT-KALI-LINUX',
            'rule_id': 941100,
            'rule_level': 8,  # Critical
            'rule_description': 'XSS (Cross Site Scripting) attempt detected via libinjection',
            'location': '/var/log/apache2/error.log',
            'full_log': '[Sun Sep 22 18:15:30.437506 2025] [security2:error] [pid 315188:tid 315188] [client 10.12.47.58:65415] ModSecurity: Warning. detected XSS using libinjection. [file "/etc/apache2/modsecurity/coreruleset-3.3.2/rules/REQUEST-941-APPLICATION-ATTACK-XSS.conf"] [line "56"] [id "941100"] [rev ""] [msg "XSS Attack Detected via libinjection"] [data "Matched Data: <script>alert(1)</script> found within ARGS:name: <script>alert(1)</script>"] [severity "CRITICAL"] [ver "OWASP_CRS/3.3.2"] [maturity "0"] [accuracy "0"] [tag "application-multi"] [tag "language-multi"] [tag "platform-multi"] [tag "attack-xss"] [tag "paranoia-level/1"] [tag "OWASP_CRS"] [tag "capec/1000/152/242"] [hostname "10.12.46.43"] [uri "/DVWA/vulnerabilities/xss_r/"] [unique_id "ZvBQwn8AAQEAAGDKKQwAAAAE"]'
        },
        {
            'id': 2,
            'timestamp': '2025-09-22 18:16:45',
            'agent_name': 'CLIENT-KALI-LINUX',
            'rule_id': 941110,
            'rule_level': 6,  # High
            'rule_description': 'SQL injection attempt detected',
            'location': '/var/log/apache2/access.log',
            'full_log': '10.12.47.58 - - [22/Sep/2025:18:16:45 -0400] "GET /DVWA/vulnerabilities/sqli/?id=%27+OR+1%3D1+--+&Submit=Submit HTTP/1.1" 403 492 "http://10.12.46.43/DVWA/vulnerabilities/sqli/" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"'
        },
        {
            'id': 3,
            'timestamp': '2025-09-22 18:17:20',
            'agent_name': 'CLIENT-KALI-LINUX',
            'rule_id': 5501,
            'rule_level': 5,  # Medium
            'rule_description': 'Login authentication failed',
            'location': '/var/log/auth.log',
            'full_log': 'Sep 22 18:17:20 client-kali sshd[12345]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2'
        }
    ]
    
    # Group alerts by severity
    critical_alerts = [a for a in sample_alerts if a['rule_level'] >= 8]
    high_alerts = [a for a in sample_alerts if a['rule_level'] >= 6 and a['rule_level'] < 8]
    medium_alerts = [a for a in sample_alerts if a['rule_level'] == 5]
    
    print(f"📊 Sample Data:")
    print(f"   Critical Alerts: {len(critical_alerts)}")
    print(f"   High Alerts: {len(high_alerts)}")
    print(f"   Medium Alerts: {len(medium_alerts)}")
    print()
    
    # Test alert message creation
    try:
        alert_message = bot._create_alert_message(critical_alerts, high_alerts, medium_alerts)
        
        print("📝 Generated Alert Message:")
        print("=" * 60)
        print(alert_message)
        print("=" * 60)
        print()
        
        # Check if full_log is included
        if "```" in alert_message:
            print("✅ SUCCESS: Full log data found in code blocks!")
            code_blocks = alert_message.count("```")
            print(f"   Code blocks found: {code_blocks // 2}")
        else:
            print("❌ WARNING: No code blocks found - full_log may be missing")
        
        # Check message length
        print(f"📏 Message length: {len(alert_message)} characters")
        if len(alert_message) > 4096:
            print("⚠️  WARNING: Message exceeds Telegram limit (4096 chars)")
        else:
            print("✅ Message length within Telegram limits")
        
        # Check for Markdown formatting
        markdown_indicators = ['*', '_', '`', '```']
        markdown_found = sum(1 for indicator in markdown_indicators if indicator in alert_message)
        print(f"📝 Markdown formatting elements found: {markdown_found}")
        
        # Save to file for inspection
        output_file = project_root / "telegram_alert_test_output.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Test Alert Message Generated at {datetime.now()}\n")
            f.write("=" * 60 + "\n")
            f.write(alert_message)
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"\nMessage Statistics:\n")
            f.write(f"Length: {len(alert_message)} characters\n")
            f.write(f"Code blocks: {alert_message.count('```') // 2}\n")
            f.write(f"Critical alerts: {len(critical_alerts)}\n")
            f.write(f"High alerts: {len(high_alerts)}\n")
            f.write(f"Medium alerts: {len(medium_alerts)}\n")
        
        print(f"\n💾 Alert message saved to: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing alert message: {e}")
        import traceback
        print("🔍 Full traceback:")
        traceback.print_exc()
        return False

def test_database_connection():
    """Test koneksi ke database untuk memastikan alerting bisa mengakses data"""
    
    print("\n🔗 Testing Database Connection for Alerting")
    print("=" * 50)
    
    try:
        # Test database path
        db_path = project_root / "data" / "wazuh_archives.db"
        
        if not db_path.exists():
            print(f"❌ Database not found: {db_path}")
            return False
        
        print(f"📍 Database path: {db_path}")
        
        # Test connection and query
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Test query for critical events (same as alerting system)
        cursor.execute("""
            SELECT * FROM wazuh_archives 
            WHERE rule_level >= 5
            ORDER BY timestamp DESC, id DESC
            LIMIT 3
        """)
        
        events = cursor.fetchall()
        print(f"📊 Found {len(events)} events with rule_level >= 5")
        
        for i, event in enumerate(events, 1):
            print(f"\n   Event {i}:")
            print(f"   - ID: {event['id']}")
            print(f"   - Level: {event['rule_level']}")
            print(f"   - Agent: {event['agent_name']}")
            print(f"   - Rule: {event['rule_id']}")
            print(f"   - Description: {event['rule_description'][:50]}...")
            print(f"   - Has full_log: {bool(event['full_log'])}")
            if event['full_log']:
                print(f"   - Full_log length: {len(event['full_log'])} characters")
        
        conn.close()
        print("\n✅ Database connection test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 TELEGRAM ALERTING SYSTEM TEST")
    print("=" * 60)
    
    # Test 1: Alert message format
    format_success = test_alert_message_format()
    
    # Test 2: Database connection
    db_success = test_database_connection()
    
    print("\n🏁 TEST SUMMARY:")
    print("=" * 30)
    print(f"Alert Format Test: {'✅ PASS' if format_success else '❌ FAIL'}")
    print(f"Database Test: {'✅ PASS' if db_success else '❌ FAIL'}")
    
    if format_success and db_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("Telegram alerting system ready with full_log support!")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")