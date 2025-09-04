#!/usr/bin/env python3
"""
Direct demonstration of the Wazuh RAG threat hunting system
"""

import asyncio
import json
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly from the module
from wazuh_fastmcp_server import WazuhLangChainRAG

class MockContext:
    """Mock context for testing"""
    
    async def info(self, message):
        print(f"ℹ️  {message}")
    
    async def error(self, message):
        print(f"❌ {message}")

async def hunt_for_network_threats():
    """Demonstrate finding suspicious network connections"""
    
    print("🔍 WAZUH AI THREAT HUNTING - Network Security Analysis")
    print("=" * 65)
    
    # Initialize the RAG system
    rag = WazuhLangChainRAG()
    ctx = MockContext()
    
    # Threat hunting query for network connections
    query = "suspicious network connections"
    
    await ctx.info(f"🎯 Hunting for: '{query}'")
    await ctx.info("🔄 Initializing vector store with latest security events...")
    
    try:
        # Search for network threats
        results = await rag.search(query, k=5)
        
        if results:
            print(f"\n🚨 NETWORK THREATS DETECTED: {len(results)} suspicious events found")
            print("=" * 65)
            
            for i, result in enumerate(results, 1):
                metadata = result['metadata']
                
                print(f"\n🔍 SECURITY EVENT #{i}")
                print(f"   Threat Confidence: {result['similarity_score']:.3f}")
                print(f"   Relevance Level: {result['relevance'].upper()}")
                
                print(f"\n   📋 Event Details:")
                print(f"   • Event ID: {metadata['id']}")
                print(f"   • Timestamp: {metadata['timestamp']}")
                print(f"   • Agent: {metadata['agent_name']} (ID: {metadata['agent_id']})")
                print(f"   • Rule: {metadata['rule_id']} (Level {metadata['rule_level']})")
                
                if metadata.get('rule_description'):
                    print(f"   • Description: {metadata['rule_description']}")
                
                print(f"   • Location: {metadata.get('location', 'N/A')}")
                print(f"   • Decoder: {metadata.get('decoder_name', 'N/A')}")
                
                print(f"\n   📄 Log Content Analysis:")
                # Show relevant parts of the log
                content = result['content']
                lines = content.split('\\n')
                for line in lines[:8]:  # Show first 8 lines
                    if line.strip():
                        print(f"   | {line}")
                if len(lines) > 8:
                    print(f"   | ... ({len(lines)-8} more lines)")
                
                print("-" * 65)
            
            # Provide threat analysis summary
            print(f"\n🎯 THREAT ANALYSIS SUMMARY:")
            high_relevance = sum(1 for r in results if r['relevance'] == 'high')
            medium_relevance = sum(1 for r in results if r['relevance'] == 'medium')
            low_relevance = sum(1 for r in results if r['relevance'] == 'low')
            
            print(f"   • High Relevance Threats: {high_relevance}")
            print(f"   • Medium Relevance Threats: {medium_relevance}")
            print(f"   • Low Relevance Threats: {low_relevance}")
            
            # Get unique agents involved
            agents = set(r['metadata']['agent_name'] for r in results)
            print(f"   • Affected Systems: {', '.join(agents)}")
            
            # Show time range
            timestamps = [r['metadata']['timestamp'] for r in results if r['metadata']['timestamp']]
            if timestamps:
                print(f"   • Time Range: {min(timestamps)} to {max(timestamps)}")
        
        else:
            print("✅ No network threats detected in current dataset")
            print("💡 This could indicate:")
            print("   • Your network is secure")
            print("   • No recent network-related security events")
            print("   • Different search terms may be needed")
        
    except Exception as e:
        await ctx.error(f"Threat hunting failed: {str(e)}")
        print(f"🔧 Debug Info: {type(e).__name__}")
        
    print(f"\n🎉 Network threat hunting complete!")

if __name__ == "__main__":
    asyncio.run(hunt_for_network_threats())
