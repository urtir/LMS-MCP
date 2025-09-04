#!/usr/bin/env python3
"""
Test script for the improved Wazuh RAG threat hunting system
"""

import asyncio
from wazuh_fastmcp_server import rag_system, check_wazuh_log
from fastmcp import Context

async def test_rag_system():
    """Test the RAG system with various threat hunting queries"""
    
    print("🔍 Testing Wazuh AI Threat Hunting RAG System")
    print("=" * 60)
    
    # Test queries based on Wazuh documentation examples
    test_queries = [
        "suspicious network connections",
        "SSH brute-force attempts",
        "failed login attempts", 
        "authentication failures",
        "PowerShell data exfiltration",
        "network port scanning",
        "malware detection",
        "privilege escalation"
    ]
    
    for query in test_queries:
        print(f"\n🎯 Query: '{query}'")
        print("-" * 40)
        
        results = await rag_system.search(query, k=3)
        
        if results:
            print(f"✅ Found {len(results)} relevant security events")
            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                score = result.get('similarity_score', 0)
                relevance = result.get('relevance', 'unknown')
                
                print(f"\n📊 Result #{i}")
                print(f"   Confidence Score: {score:.3f}")
                print(f"   Relevance: {relevance}")
                print(f"   Rule ID: {metadata.get('rule_id', 'N/A')}")
                print(f"   Rule Level: {metadata.get('rule_level', 'N/A')}")
                print(f"   Description: {metadata.get('rule_description', 'N/A')[:100]}...")
                print(f"   Agent: {metadata.get('agent_name', 'N/A')}")
                print(f"   Timestamp: {metadata.get('timestamp', 'N/A')}")
                
                content_preview = result.get('content', '')[:200].replace('\n', ' ')
                print(f"   Content: {content_preview}...")
        else:
            print("❌ No matching security events found")
    
    print(f"\n🧪 Testing MCP Tool Integration")
    print("-" * 40)
    
    # Create a mock context for testing the MCP tool
    class MockContext:
        async def info(self, message):
            print(f"ℹ️  {message}")
        
        async def error(self, message):
            print(f"❌ {message}")
    
    ctx = MockContext()
    
    # Test the MCP tool
    result = await check_wazuh_log(
        ctx=ctx,
        query="suspicious network connections",
        max_results=3,
        rebuild_index=False
    )
    
    print("\n📋 MCP Tool Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(test_rag_system())
