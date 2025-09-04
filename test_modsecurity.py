#!/usr/bin/env python3
"""
Test untuk mencari ModSecurity XSS logs yang sebenarnya
"""

import asyncio
import json
from mcp_tool_bridge import FastMCPBridge

async def test_modsecurity_logs():
    """Test specific ModSecurity XSS logs"""
    
    print("🔍 Testing ModSecurity XSS Logs")
    print("=" * 40)
    
    bridge = FastMCPBridge()
    
    # Start and connect
    await bridge.start_mcp_server()
    await bridge.connect_to_server()
    await bridge.load_tools()
    
    print("🎯 Searching for ModSecurity XSS logs...")
    try:
        result = await bridge.execute_tool(
            tool_name='check_wazuh_log',
            arguments={
                'query': 'ModSecurity XSS libinjection script alert',
                'max_results': 3,
                'rebuild_index': True  # Rebuild to get fresh data
            }
        )
        
        # Handle result format
        if isinstance(result, dict) and result.get('status') == 'success':
            content = result.get('content', '{}')
            if isinstance(content, str):
                result_data = json.loads(content)
            else:
                result_data = content
        else:
            print(f"❌ Error: {result}")
            return
        
        status = result_data.get('status', 'unknown')
        
        if status == 'threats_identified':
            print(f"✅ Found {result_data.get('total_security_events', 0)} ModSecurity events")
            
            events = result_data.get('security_events', [])
            if events:
                first_event = events[0]
                print(f"\n📋 Event #{first_event['security_event']['event_id']}:")
                print(f"   Agent: {first_event['security_event']['agent_info']['name']}")
                print(f"   Rank: #{first_event['rank']}")
                
                # Check original_log_data for ModSecurity format
                if 'original_log_data' in first_event:
                    orig_data = first_event['original_log_data']
                    full_log = orig_data.get('full_log', 'N/A')
                    
                    if full_log != 'N/A':
                        print(f"\n🚨 ORIGINAL FULL_LOG CONTENT:")
                        print(f"   Length: {len(full_log)} characters")
                        
                        # Check if it contains ModSecurity format
                        if 'ModSecurity' in full_log:
                            print(f"   ✅ Contains ModSecurity alerts!")
                            print(f"\n📝 Full Log Content:")
                            print(f"{full_log}")
                        elif '[security2:error]' in full_log:
                            print(f"   ✅ Contains security2 error logs!")
                            print(f"\n📝 Full Log Content:")
                            print(f"{full_log}")
                        else:
                            print(f"   ❌ Does NOT contain expected ModSecurity format")
                            print(f"   First 300 chars: {full_log[:300]}...")
                    else:
                        print(f"   ❌ full_log is N/A")
                else:
                    print(f"   ❌ original_log_data missing")
                    
        else:
            print(f"Status: {status}")
            print(f"Message: {result_data.get('message', 'No message')}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    try:
        await bridge.client.__aexit__(None, None, None)
    except:
        pass
    
    print(f"\n🏁 ModSecurity test done!")

if __name__ == "__main__":
    asyncio.run(test_modsecurity_logs())
