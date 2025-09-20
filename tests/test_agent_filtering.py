#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test CAG with agent_ids parameter
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.wazuh_fastmcp_server import cag_system

async def test_agent_filtering():
    """Test CAG with agent filtering."""
    print("🧪 Testing CAG with Agent Filtering")
    print("=" * 50)
    
    query = "Identifikasi upaya eksekusi query SQL mencurigakan"
    agent_ids = ["CLIENT-KALI-LINUX"]
    
    print(f"Query: {query}")
    print(f"Agent IDs: {agent_ids}")
    print("-" * 50)
    
    try:
        # Test CAG search with agent filtering
        threat_events = await cag_system.search(query, k=10, agent_ids=agent_ids)
        
        print("✅ CAG search with agent filtering successful!")
        print(f"Threat events found: {len(threat_events)}")
        
        if threat_events:
            print("\nSample events:")
            for i, event in enumerate(threat_events[:3], 1):
                agent_name = event.get('agent_name', 'N/A')
                rule_id = event.get('rule_id', 'N/A')
                priority = event.get('threat_priority', 'N/A')
                print(f"   {i}. Agent: {agent_name}, Rule: {rule_id}, Priority: {priority}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_agent_filtering())
    if success:
        print("\n🎉 Agent filtering test completed successfully!")
    else:
        print("\n💥 Agent filtering test failed!")