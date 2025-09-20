#!/usr/bin/env python3
"""
Test script to verify ALL columns including full_log are being used
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.wazuh_fastmcp_server import WazuhCAG

async def main():
    print("=" * 60)
    print("🔍 TESTING ALL COLUMNS INCLUDING FULL_LOG USAGE")
    print("=" * 60)
    
    # Initialize CAG system
    cag = WazuhCAG()
    
    print("\n1. Testing database column retrieval...")
    logs = await cag.get_security_logs_for_context(limit=5)
    
    if logs:
        print(f"✅ Retrieved {len(logs)} logs")
        print("\n🔍 Sample log columns:")
        first_log = logs[0]
        for key, value in first_log.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
        
        # Check if full_log is present and not empty
        full_log_present = any(log.get('full_log') for log in logs)
        print(f"\n✅ full_log column present and populated: {full_log_present}")
        
        if full_log_present:
            # Show full_log samples
            print("\n📄 Sample full_log entries:")
            for i, log in enumerate(logs[:3], 1):
                full_log = log.get('full_log', '')
                if full_log:
                    print(f"  {i}. {full_log[:150]}...")
    
    print("\n2. Testing knowledge prompt creation with full_log...")
    knowledge_prompt = cag.build_knowledge_prompt(logs[:3])
    
    # Check if full_log content appears in knowledge prompt
    has_full_log_in_prompt = 'FULL_LOG:' in knowledge_prompt or 'FullLog:' in knowledge_prompt
    print(f"✅ Knowledge prompt contains full_log content: {has_full_log_in_prompt}")
    
    if has_full_log_in_prompt:
        print("\n📝 Sample knowledge prompt excerpt:")
        lines = knowledge_prompt.split('\n')
        for line in lines:
            if 'FULL_LOG:' in line or 'FullLog:' in line:
                print(f"  {line[:200]}...")
                break
    
    print("\n3. Testing CAG cache creation with full data...")
    success = await cag.create_knowledge_cache(limit=50)
    if success:
        print("✅ CAG cache created successfully with full column data")
        
        # Test a query to see if full_log data improves responses
        print("\n4. Testing query with full_log enhanced context...")
        query = "show me detailed information about brute force attacks"
        response = await cag.query_with_cache(query)
        
        if response and len(response) > 100:
            print("✅ Query response generated with enhanced context")
            print(f"📝 Response preview: {response[:300]}...")
        else:
            print("❌ Query response seems limited")
    
    print("\n" + "=" * 60)
    print("✅ ALL COLUMNS TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())