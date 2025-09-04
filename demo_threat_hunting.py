#!/usr/bin/env python3
"""
Demonstrate using the improved Wazuh RAG MCP tool for threat hunting
"""

import asyncio
import json
from wazuh_fastmcp_server import check_wazuh_log
from fastmcp import Context

class MockContext:
    """Mock context for testing MCP tool"""
    
    def __init__(self):
        self.messages = []
    
    async def info(self, message):
        print(f"ℹ️  {message}")
        self.messages.append(f"INFO: {message}")
    
    async def error(self, message):
        print(f"❌ {message}")
        self.messages.append(f"ERROR: {message}")

async def demonstrate_threat_hunting():
    """Demonstrate AI-powered threat hunting with the MCP tool"""
    
    print("🚨 Wazuh AI Threat Hunting Demonstration")
    print("=" * 60)
    
    # Create mock context
    ctx = MockContext()
    
    # Test cases based on the Wazuh documentation examples
    threat_scenarios = [
        {
            "name": "Network Security Analysis", 
            "query": "suspicious network connections and port scanning activity",
            "description": "Looking for unusual network activity that could indicate reconnaissance or lateral movement"
        },
        {
            "name": "Authentication Threat Hunting",
            "query": "SSH brute-force attempts and authentication failures", 
            "description": "Searching for credential-based attacks and unauthorized access attempts"
        },
        {
            "name": "System Process Analysis",
            "query": "unusual system processes and privilege escalation attempts",
            "description": "Identifying potentially malicious processes or privilege abuse"
        }
    ]
    
    for scenario in threat_scenarios:
        print(f"\n🎯 Threat Scenario: {scenario['name']}")
        print(f"📝 Description: {scenario['description']}")
        print(f"🔍 Query: '{scenario['query']}'")
        print("-" * 50)
        
        try:
            # Get the actual function from the MCP tool
            tool_func = check_wazuh_log.func  # Access the underlying function
            
            # Execute the threat hunting query
            result = await tool_func(
                ctx=ctx,
                query=scenario['query'],
                max_results=5,
                rebuild_index=False
            )
            
            # Parse and display results
            threat_data = json.loads(result)
            
            if threat_data['status'] == 'threats_identified':
                print(f"🚨 THREATS DETECTED: {threat_data['total_security_events']} security events found")
                print(f"⏰ Analysis Time: {threat_data['analysis_timestamp']}")
                
                for event in threat_data['security_events']:
                    print(f"\n   📊 Rank #{event['rank']} - {event['threat_relevance']} relevance")
                    print(f"   🎯 Confidence: {event['confidence_score']:.3f}")
                    print(f"   🏷️  Rule: {event['security_event']['security_rule']['rule_id']} (Level {event['security_event']['security_rule']['severity_level']})")
                    print(f"   📋 Description: {event['security_event']['security_rule']['description']}")
                    print(f"   🖥️  Agent: {event['security_event']['agent_info']['name']}")
                    print(f"   ⏱️  Time: {event['security_event']['timestamp']}")
                    print(f"   📂 Source: {event['security_event']['event_source']}")
                    
                    # Show content preview
                    content = event['log_analysis']['full_content'][:300]
                    print(f"   📄 Content Preview: {content}...")
                    
            else:
                print("✅ No immediate threats detected for this scenario")
                print(f"💡 Recommendation: {threat_data.get('recommendation', 'Try different search terms')}")
                
        except Exception as e:
            print(f"❌ Error during threat hunting: {str(e)}")
            
        print("\n" + "="*50)
    
    print(f"\n🎉 Threat Hunting Demonstration Complete!")
    print(f"💡 The Wazuh AI RAG system successfully analyzed your security logs")
    print(f"   using LangChain embeddings and FAISS vector similarity search.")

if __name__ == "__main__":
    asyncio.run(demonstrate_threat_hunting())
