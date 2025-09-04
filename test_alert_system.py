#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script for Telegram Alert System
Test the realtime alert functionality for critical events (rule level 7+)
"""

import sqlite3
import json
import time
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_critical_events():
    """Insert test critical events into database to trigger alerts"""
    try:
        # Connect to database
        conn = sqlite3.connect('wazuh_archives.db')
        cursor = conn.cursor()
        
        # Test events data with rule level 5+
        test_events = [
            {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'agent_name': 'TestAgent-001',
                'rule_id': 5715,
                'rule_level': 8,  # Critical
                'rule_description': 'Multiple failed login attempts detected',
                'location': '(test-agent) /var/log/auth.log',
                'full_log': 'Feb 10 12:34:56 test sshd[1234]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2'
            },
            {
                'timestamp': (datetime.now() + timedelta(seconds=30)).strftime('%Y-%m-%d %H:%M:%S'),
                'agent_name': 'TestAgent-002', 
                'rule_id': 31101,
                'rule_level': 6,  # High
                'rule_description': 'Web server attack detected - SQL Injection attempt',
                'location': '(test-agent) /var/log/apache2/access.log',
                'full_log': '192.168.1.200 - - [10/Feb/2025:12:35:30] "GET /login.php?id=1\'%20OR%201=1-- HTTP/1.1" 200 1234'
            },
            {
                'timestamp': (datetime.now() + timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S'),
                'agent_name': 'TestAgent-003',
                'rule_id': 52501,
                'rule_level': 9,  # Critical
                'rule_description': 'Malware detection - Trojan.Win32.Generic found',
                'location': '(test-agent) /var/log/antivirus.log',
                'full_log': '[ALERT] Trojan.Win32.Generic detected in C:\\Users\\test\\Downloads\\malicious.exe - Action: Quarantined'
            },
            {
                'timestamp': (datetime.now() + timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S'),
                'agent_name': 'TestAgent-004',
                'rule_id': 40111,
                'rule_level': 5,  # Medium - NEW LEVEL TO TEST
                'rule_description': 'Suspicious file access - unauthorized directory listing',
                'location': '(test-agent) /var/log/system.log',
                'full_log': 'Feb 10 12:37:00 system: WARNING - User attempted to access restricted directory /etc/shadow'
            },
            {
                'timestamp': (datetime.now() + timedelta(minutes=3)).strftime('%Y-%m-%d %H:%M:%S'),
                'agent_name': 'TestAgent-005',
                'rule_id': 18105,
                'rule_level': 7,  # High
                'rule_description': 'File integrity monitoring - critical file modified',
                'location': '(test-agent) /var/log/ossec.log',
                'full_log': 'Feb 10 12:38:00 ossec: File /etc/passwd has been modified by user root'
            }
        ]
        
        # Insert test events
        for event in test_events:
            cursor.execute("""
                INSERT INTO wazuh_archives 
                (timestamp, agent_name, rule_id, rule_level, rule_description, location, full_log, json_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event['timestamp'],
                event['agent_name'], 
                event['rule_id'],
                event['rule_level'],
                event['rule_description'],
                event['location'],
                event['full_log'],
                json.dumps(event)  # Store as JSON too
            ))
            
            logger.info(f"✅ Inserted test event: Level {event['rule_level']} - {event['rule_description']}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"🎯 Successfully inserted {len(test_events)} test critical events (rule level 5+)")
        logger.info("🚨 These events should trigger alerts in the Telegram bot!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating test events: {e}")
        return False

def check_recent_critical_events():
    """Check for recent critical events in database"""
    try:
        conn = sqlite3.connect('wazuh_archives.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check for events in last 10 minutes with rule level >= 5
        cutoff_time = (datetime.now() - timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            SELECT timestamp, agent_name, rule_level, rule_description 
            FROM wazuh_archives 
            WHERE rule_level >= 5 
            AND timestamp > ?
            ORDER BY timestamp DESC
        """, (cutoff_time,))
        
        events = cursor.fetchall()
        conn.close()
        
        if events:
            logger.info(f"📊 Found {len(events)} critical events (rule level 5+) in last 10 minutes:")
            for event in events:
                logger.info(f"  • Level {event['rule_level']} - {event['agent_name']} - {event['rule_description']}")
        else:
            logger.info("📭 No critical events (rule level 5+) found in last 10 minutes")
            
        return events
        
    except Exception as e:
        logger.error(f"❌ Error checking events: {e}")
        return []

def main():
    """Main test function"""
    print("=" * 60)
    print("🧪 Testing Telegram Alert System")
    print("=" * 60)
    print()
    
    # Check current state
    print("1️⃣ Checking existing critical events...")
    existing_events = check_recent_critical_events()
    
    print()
    print("2️⃣ Creating test critical events...")
    
    if create_test_critical_events():
        print()
        print("3️⃣ Verifying test events were created...")
        time.sleep(2)  # Wait a bit
        new_events = check_recent_critical_events()
        
        print()
        print("🎯 **Test Results:**")
        print(f"• Events before test: {len(existing_events)}")
        print(f"• Events after test: {len(new_events)}")
        print(f"• New test events: {len(new_events) - len(existing_events)}")
        
        print()
        print("🚨 **Alert Testing Instructions:**")
        print("1. Make sure Telegram bot is running")
        print("2. Enable alerts with /enable_alerts command")
        print("3. Wait 10 seconds for alert monitoring cycle (REALTIME)")
        print("4. You should receive alert notifications!")
        
        print()
        print("📱 **Expected Alert Message:**")
        print("🚨 SECURITY ALERT 🚨")
        print("⏰ Time: [current time]") 
        print("💥 CRITICAL Events (L8+): 2")
        print("⚠️ HIGH Events (L6-7): 2")
        print("🔍 MEDIUM Events (L5): 1") 
        print("🔍 Action Required...")
        
    else:
        print("❌ Failed to create test events")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        logger.exception("Test error")
