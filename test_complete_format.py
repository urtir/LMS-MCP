#!/usr/bin/env python3
"""
Complete test to show the new result format with full_log
"""

import asyncio
import json
from mcp_tool_bridge import FastMCPBridge

async def test_complete_result_format():
    """Test complete result format with full_log display"""
    
    print("🚀 Testing Complete Result Format with Full Log")
    print("=" * 55)
    
    bridge = FastMCPBridge()
    
    # Start and connect
    await bridge.start_mcp_server()
    await bridge.connect_to_server()
    await bridge.load_tools()
    
    print("🎯 Executing query: 'XSS attacks malicious payloads injection'")
    try:
        result = await bridge.execute_tool(
            tool_name='check_wazuh_log',
            arguments={
                'query': 'XSS attacks malicious payloads injection attempts',
                'max_results': 2,
                'rebuild_index': False
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
        
        print(f"\n📋 COMPLETE RESULT FORMAT:")
        print("=" * 40)
        print(json.dumps(result_data, indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Cleanup
    try:
        await bridge.client.__aexit__(None, None, None)
    except:
        pass
    
    print(f"\n🏁 Complete format test done!")

if __name__ == "__main__":
    asyncio.run(test_complete_result_format())
