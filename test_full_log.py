#!/usr/bin/env python3
"""
Test RAG tool to check full_log column display
"""

import asyncio
import json
from mcp_tool_bridge import FastMCPBridge

async def test_full_log_display():
    """Test if full_log column is properly displayed in results"""
    
    print("🔍 Testing Full Log Column Display")
    print("=" * 40)
    
    bridge = FastMCPBridge()
    
    # Start and connect
    await bridge.start_mcp_server()
    await bridge.connect_to_server()
    await bridge.load_tools()
    
    # Test execution with specific query
    print("🎯 Testing with specific query...")
    try:
        result = await bridge.execute_tool(
            tool_name='check_wazuh_log',
            arguments={
                'query': 'system processes xorg wazuh-agentd',
                'max_results': 2,
                'rebuild_index': False
            }
        )
        
        print("✅ RAG tool executed successfully!")
        
        # Handle result format
        if isinstance(result, dict) and result.get('status') == 'success':
            content = result.get('content', '{}')
            if isinstance(content, str):
                result_data = json.loads(content)
            else:
                result_data = content
        else:
            print(f"❌ Bridge execution failed: {result}")
            return
        
        status = result_data.get('status', 'unknown')
        
        if status == 'threats_identified':
            print(f"📊 Found {result_data.get('total_security_events', 0)} security events")
            
            # Check if full_log data is present
            events = result_data.get('security_events', [])
            if events:
                first_event = events[0]
                print(f"\n🔎 First Event Details:")
                print(f"   Event ID: {first_event['security_event']['event_id']}")
                print(f"   Rank: #{first_event['rank']}")
                print(f"   Agent: {first_event['security_event']['agent_info']['name']}")
                
                # Check original_log_data
                if 'original_log_data' in first_event:
                    orig_data = first_event['original_log_data']
                    print(f"\n📋 Original Log Data Present:")
                    print(f"   full_log: {'✅ YES' if orig_data.get('full_log') != 'N/A' else '❌ NO'}")
                    print(f"   data: {'✅ YES' if orig_data.get('data') != 'N/A' else '❌ NO'}")
                    print(f"   json_data: {'✅ YES' if orig_data.get('json_data') != 'N/A' else '❌ NO'}")
                    
                    # Show sample of full_log
                    full_log = orig_data.get('full_log', 'N/A')
                    if full_log != 'N/A':
                        print(f"\n📝 Sample Full Log Content (first 200 chars):")
                        print(f"   {full_log[:200]}...")
                    else:
                        print(f"\n❌ No full_log content found!")
                else:
                    print(f"\n❌ original_log_data section missing!")
                    
        else:
            print(f"Status: {status}")
            print(f"Message: {result_data.get('message', 'No message')}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Cleanup
    try:
        await bridge.client.__aexit__(None, None, None)
    except:
        pass
    
    print(f"\n🏁 Full log test complete!")

if __name__ == "__main__":
    asyncio.run(test_full_log_display())
