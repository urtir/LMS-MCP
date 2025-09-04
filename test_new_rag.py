#!/usr/bin/env python3

import asyncio
from wazuh_fastmcp_server import WazuhLangChainRAG

async def test_wazuh_methodology():
    """Test the new Wazuh AI threat hunting methodology implementation."""
    rag = WazuhLangChainRAG()
    
    print("🚀 Testing Wazuh AI Threat Hunting Methodology")
    print("=" * 60)
    
    # Test 1: Create vector store with Wazuh methodology
    print("\n📦 Creating Wazuh AI vector store...")
    result = await rag.create_vector_store(limit=500)
    print(f"✅ Vector store created with {result} enhanced security log chunks")
    
    # Test 2: Test brute-force detection query (following Wazuh example)
    print("\n🔍 Testing: SSH brute-force detection")
    query1 = "Are there any SSH brute-force attempts against my endpoints or any other suspicious SSH events, such as multiple failed logins by valid or invalid users?"
    results1 = await rag.search(query1, k=3)
    
    print(f"Found {len(results1)} threat events:")
    for i, event in enumerate(results1[:2], 1):  # Show top 2
        print(f"\n--- Threat Event {i} ---")
        print(f"ID: {event.get('id')}")
        print(f"Priority: {event.get('threat_priority', 'Unknown')}")
        print(f"Threat Score: {event.get('threat_score', 'N/A')}")
        print(f"Indicators: {event.get('threat_indicators', [])}")
        print(f"Agent: {event.get('agent_name', 'Unknown')}")
        print(f"Rule Description: {event.get('rule_description', 'N/A')}")
    
    # Test 3: Test data exfiltration query (following Wazuh example)  
    print("\n🔍 Testing: Data exfiltration detection")
    query2 = "Look through the logs and identify any attempt to exfiltrate files to remote systems using binaries such as invoke-webrequest or similar events"
    results2 = await rag.search(query2, k=2)
    
    print(f"Found {len(results2)} potential exfiltration events:")
    for i, event in enumerate(results2, 1):
        print(f"\n--- Exfiltration Event {i} ---")
        print(f"ID: {event.get('id')}")
        print(f"Priority: {event.get('threat_priority', 'Unknown')}")  
        print(f"Security Assessment: Investigation Required = {event.get('security_assessment', {}).get('requires_investigation', False)}")
        full_log = event.get('full_log', 'N/A')
        print(f"Log Preview: {full_log[:150]}...")
    
    print(f"\n🎯 Wazuh AI Threat Hunting Test Complete!")
    print("Methodology: https://wazuh.com/blog/leveraging-artificial-intelligence-for-threat-hunting-in-wazuh/")

if __name__ == "__main__":
    asyncio.run(test_wazuh_methodology())
