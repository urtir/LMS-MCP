#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test CAG Implementation
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.wazuh_fastmcp_server import WazuhCAG, lm_studio_config

async def test_cag_system():
    """Test the CAG system implementation."""
    print("🧪 Testing Wazuh CAG (Cache-Augmented Generation) System")
    print("=" * 60)
    
    # Initialize CAG system
    cag = WazuhCAG()
    
    # Test configuration
    print(f"📋 Configuration:")
    print(f"   - LM Studio URL: {lm_studio_config.base_url}")
    print(f"   - Model: {lm_studio_config.model}")
    print(f"   - Database: {cag.db_path}")
    print()
    
    # Test knowledge cache creation
    print("🔄 Testing knowledge cache creation...")
    try:
        success = await cag.create_knowledge_cache(limit=100)
        if success:
            print("✅ Knowledge cache created successfully")
        else:
            print("⚠️ Knowledge cache creation completed with warnings")
    except Exception as e:
        print(f"❌ Error creating knowledge cache: {e}")
        return
    
    # Test security log retrieval
    print("\n📊 Testing security logs retrieval...")
    try:
        logs = await cag.get_security_logs_for_context(limit=10)
        print(f"✅ Retrieved {len(logs)} security logs")
        if logs:
            sample_log = logs[0]
            print(f"   - Sample: Rule {sample_log.get('rule_id', 'N/A')} - Level {sample_log.get('rule_level', 0)}")
    except Exception as e:
        print(f"❌ Error retrieving security logs: {e}")
    
    # Test query with cache (if LM Studio available)
    print("\n🔍 Testing CAG query...")
    if cag.lm_client and cag.knowledge_loaded:
        try:
            test_query = "Apakah ada aktivitas keamanan mencurigakan?"
            print(f"   Attempting to connect to LM Studio at {lm_studio_config.base_url}")
            response = await cag.query_with_cache(test_query, max_tokens=200)
            print(f"✅ CAG Query successful")
            print(f"   Query: {test_query}")
            print(f"   Response preview: {response[:100]}...")
        except Exception as e:
            print(f"⚠️ CAG query test failed (LM Studio may not be running): {str(e)[:100]}")
            print(f"   Note: This is normal if LM Studio server is not started")
    else:
        print("⚠️ Skipping CAG query test (LM Studio client not available or cache not loaded)")
    
    # Test search functionality
    print("\n🔎 Testing CAG search...")
    try:
        results = await cag.search("authentication failed", k=5)
        print(f"✅ CAG Search successful - found {len(results)} relevant events")
        for i, result in enumerate(results[:3], 1):
            print(f"   {i}. Rule {result.get('rule_id', 'N/A')} - Priority: {result.get('threat_priority', 'N/A')}")
    except Exception as e:
        print(f"❌ Error in CAG search: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 CAG System Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_cag_system())