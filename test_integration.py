#!/usr/bin/env python3
"""
Test RAG tool integration with main webapp system
"""

import asyncio
import json
from mcp_tool_bridge import FastMCPBridge

async def test_full_integration():
    """Test if RAG tool works through the main MCP bridge"""
    
    print("🔧 Testing RAG Tool Integration with Main System")
    print("=" * 55)
    
    bridge = FastMCPBridge()
    
    # Start and connect
    await bridge.start_mcp_server()
    await bridge.connect_to_server()
    await bridge.load_tools()
    
    # Find our RAG tool
    rag_tool = None
    for tool in bridge.openai_tools:
        func = tool.get('function', {})
        if func.get('name') == 'check_wazuh_log':
            rag_tool = tool
            break
    
    if rag_tool:
        print("✅ RAG tool found in MCP bridge!")
        func = rag_tool.get('function', {})
        print(f"   Name: {func.get('name')}")
        print(f"   Description: {func.get('description', '')[:100]}...")
        
        # Test execution through bridge
        print("\n🎯 Testing RAG tool execution through MCP bridge...")
        try:
            result = await bridge.execute_tool(
                tool_name='check_wazuh_log',
                arguments={
                    'query': 'suspicious network activity',
                    'max_results': 3,
                    'rebuild_index': False
                }
            )
            
            print("✅ RAG tool executed successfully through MCP bridge!")
            
            # Handle result format - it's already a dict from the bridge
            if isinstance(result, dict):
                result_data = result
                if result_data.get('status') == 'success':
                    # Parse the actual tool result from content
                    content = result_data.get('content', '{}')
                    if isinstance(content, str):
                        result_data = json.loads(content)
                    else:
                        result_data = content
                else:
                    print(f"❌ Bridge execution failed: {result_data.get('message', 'Unknown error')}")
                    return
            else:
                # If it's a string, parse as JSON
                result_data = json.loads(result)
            
            status = result_data.get('status', 'unknown')
            
            if status == 'threats_identified':
                events = result_data.get('total_security_events', 0)
                timestamp = result_data.get('analysis_timestamp', 'N/A')
                print(f"   Status: {status}")
                print(f"   Security Events: {events}")
                print(f"   Analysis Time: {timestamp}")
                
                # Show first event details
                if result_data.get('security_events'):
                    first_event = result_data['security_events'][0]
                    print(f"   First Event: Rank #{first_event['rank']}, Confidence: {first_event['confidence_score']:.3f}")
                    agent_info = first_event['security_event']['agent_info']
                    print(f"   Agent: {agent_info['name']} (ID: {agent_info['id']})")
                    
            else:
                print(f"   Status: {status}")
                print(f"   Message: {result_data.get('message', 'No message')}")
            
        except Exception as e:
            print(f"❌ Error executing RAG tool: {e}")
            print(f"   Error type: {type(e).__name__}")
    
    else:
        print("❌ RAG tool not found in MCP bridge!")
        print("Available tools:")
        for i, tool in enumerate(bridge.openai_tools[:5]):
            func = tool.get('function', {})
            print(f"  {i+1}. {func.get('name', 'unknown')}")
    
    # Cleanup
    try:
        await bridge.client.__aexit__(None, None, None)
    except:
        pass
    
    print(f"\n🎉 Integration test complete!")

if __name__ == "__main__":
    asyncio.run(test_full_integration())
