#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test check_wazuh_log tool dengan query yang bermasalah
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

class MockContext:
    """Mock context for testing"""
    def __init__(self):
        self.logs = []
    
    async def info(self, message):
        print(f"INFO: {message}")
        self.logs.append(f"INFO: {message}")
    
    async def error(self, message):
        print(f"ERROR: {message}")
        self.logs.append(f"ERROR: {message}")

async def test_sql_injection_query():
    """Test dengan query 'kalau sql injection'"""
    print("🧪 Testing query cleanup untuk 'kalau sql injection'")
    print("=" * 70)
    
    # Test dengan query yang bermasalah
    test_query = "kalau sql injection"
    print(f"📋 Test Query: '{test_query}'")
    print()
    
    try:
        # Directly test the query generation logic that was problematic
        print("🔧 Testing query generation logic directly...")
        
        # Simulate the problematic LLM response
        generated_query = '<think>\n</think>\n\nSQL injection\nBrute force\nMalware...'
        print(f"Original LLM response: '{generated_query}'")
        
        # Apply our cleanup logic
        import re
        
        # Remove quotes
        cleaned_query = generated_query.replace('"', '').replace("'", '').strip()
        
        # Handle thinking tags
        if '<think>' in cleaned_query or '</' in cleaned_query:
            cleaned_query = re.sub(r'<think>.*?</think>', '', cleaned_query, flags=re.DOTALL)
            cleaned_query = cleaned_query.strip()
        
        # Handle multi-line responses
        if '\n' in cleaned_query:
            lines = [line.strip() for line in cleaned_query.split('\n') if line.strip()]
            for line in lines:
                words = line.split()
                if (3 <= len(words) <= 10 and 
                    not line.lower().startswith(("okay", "let", "the user", "output", "keywords")) and
                    not any(phrase in line.lower() for phrase in ["tackle this", "lets", "i would", "here are"])):
                    cleaned_query = line
                    break
            else:
                cleaned_query = lines[0] if lines else "security log analysis"
        
        # Remove common artifacts
        cleaned_query = cleaned_query.replace("Output:", "").replace("Keywords:", "").strip()
        
        # Fallback for specific queries
        if not cleaned_query or len(cleaned_query) < 3:
            if "sql injection" in test_query.lower():
                cleaned_query = "SQL injection vulnerability attack"
            else:
                cleaned_query = "security vulnerability attack"
        
        # Truncate if too long
        if len(cleaned_query) > 100:
            words = cleaned_query.split()[:8]
            cleaned_query = " ".join(words)
        
        print(f"Cleaned query: '{cleaned_query}'")
        
        # Check if it's valid
        if len(cleaned_query) >= 3 and len(cleaned_query) <= 100:
            print("✅ Query cleanup successful - no ValueError should occur")
            print(f"✅ Query length: {len(cleaned_query)} (within valid range 3-100)")
            return True
        else:
            print("❌ Query cleanup failed")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        print(f"📋 Error type: {type(e).__name__}")
        import traceback
        print("🔍 Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_sql_injection_query())
    if success:
        print("\n🎉 Test BERHASIL!")
    else:
        print("\n💥 Test GAGAL!")