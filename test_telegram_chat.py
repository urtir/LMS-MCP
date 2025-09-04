#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Telegram Security Bot Q&A functionality
Debug: Compare web app vs telegram bot results
"""

import asyncio
import json
import logging
from mcp_tool_bridge import FastMCPBridge

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_telegram_vs_webapp():
    """Test both web app and telegram queries to compare results"""
    
    print("=" * 80)
    print("🔍 DEBUGGING: Web App vs Telegram Bot Query Comparison")
    print("=" * 80)
    
    # Initialize MCP Bridge (same as Telegram bot)
    mcp_bridge = FastMCPBridge()
    
    try:
        print("📡 Connecting to FastMCP server...")
        
        # Test 1: Web App query (exactly as web app uses)
        print("\n🌐 TEST 1: Web App Query")
        print("-" * 40)
        webapp_query = "XSS"
        print(f"Query: '{webapp_query}'")
        
        webapp_response = await mcp_bridge.execute_tool(
            "check_wazuh_log",
            {
                "query": webapp_query,
                "max_results": 5,
                "days_range": 7
            }
        )
        
        print(f"Status: {webapp_response.get('status')}")
        if webapp_response.get('status') == 'success':
            content = webapp_response.get('content', '{}')
            try:
                parsed = json.loads(content)
                if 'security_events' in parsed:
                    events = parsed['security_events']
                    print(f"Events found: {len(events)}")
                    if events:
                        first_event = events[0]
                        print(f"First event log preview: {first_event.get('log_preview', 'N/A')[:100]}...")
                        print(f"First event location: {first_event.get('location', 'N/A')}")
            except:
                print("Failed to parse JSON response")
        
        # Test 2: Telegram query (Indonesian)
        print("\n📱 TEST 2: Telegram Query (Indonesian)")
        print("-" * 40)
        telegram_query = "apakah ada riwayat serangan XSS yang terjadi?"
        print(f"Query: '{telegram_query}'")
        
        telegram_response = await mcp_bridge.execute_tool(
            "check_wazuh_log",
            {
                "query": telegram_query,
                "max_results": 10,
                "days_range": 7
            }
        )
        
        print(f"Status: {telegram_response.get('status')}")
        if telegram_response.get('status') == 'success':
            content = telegram_response.get('content', '{}')
            try:
                parsed = json.loads(content)
                if 'security_events' in parsed:
                    events = parsed['security_events']
                    print(f"Events found: {len(events)}")
                    if events:
                        first_event = events[0]
                        print(f"First event log preview: {first_event.get('log_preview', 'N/A')[:100]}...")
                        print(f"First event location: {first_event.get('location', 'N/A')}")
            except:
                print("Failed to parse JSON response")
        
        # Test 3: English XSS query
        print("\n🔍 TEST 3: Simple XSS Query (English)")
        print("-" * 40)
        simple_query = "XSS attack"
        print(f"Query: '{simple_query}'")
        
        simple_response = await mcp_bridge.execute_tool(
            "check_wazuh_log",
            {
                "query": simple_query,
                "max_results": 5,
                "days_range": 7
            }
        )
        
        print(f"Status: {simple_response.get('status')}")
        if simple_response.get('status') == 'success':
            content = simple_response.get('content', '{}')
            try:
                parsed = json.loads(content)
                if 'security_events' in parsed:
                    events = parsed['security_events']
                    print(f"Events found: {len(events)}")
                    if events:
                        first_event = events[0]
                        print(f"First event log preview: {first_event.get('log_preview', 'N/A')[:100]}...")
                        print(f"First event location: {first_event.get('location', 'N/A')}")
            except:
                print("Failed to parse JSON response")
        
        print("\n" + "=" * 80)
        print("📊 ANALYSIS:")
        
        # Compare results
        webapp_events = 0
        telegram_events = 0
        
        try:
            webapp_parsed = json.loads(webapp_response.get('content', '{}'))
            webapp_events = len(webapp_parsed.get('security_events', []))
        except:
            pass
            
        try:
            telegram_parsed = json.loads(telegram_response.get('content', '{}'))
            telegram_events = len(telegram_parsed.get('security_events', []))
        except:
            pass
        
        print(f"Web App Events: {webapp_events}")
        print(f"Telegram Events: {telegram_events}")
        
        if webapp_events != telegram_events:
            print("⚠️  INCONSISTENCY DETECTED!")
            print("   - Different results for similar queries")
            print("   - Semantic search may be language/context sensitive")
            print("   - Need to optimize query enhancement")
        else:
            print("✅ Results are consistent")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logger.error(f"Test error: {e}")
    
    finally:
        # Cleanup
        try:
            await mcp_bridge.close()
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting Query Comparison Test...")
    asyncio.run(test_telegram_vs_webapp())
