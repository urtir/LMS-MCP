#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test check_wazuh_log tool melalui MCP bridge
"""

import asyncio
import sys
import json
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

# Import MCP bridge
try:
    from src.api import FastMCPBridge
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

async def test_check_wazuh_log_via_mcp():
    """Test check_wazuh_log tool via MCP bridge"""
    
    print("🧪 Testing check_wazuh_log via MCP bridge")
    print("=" * 50)
    
    try:
        # Initialize MCP bridge
        print("🔧 Initializing MCP bridge...")
        mcp_bridge = FastMCPBridge()
        print("✅ MCP bridge initialized")
        
        # Test parameters
        test_prompt = "apakah ada riwayat serangan xss?"
        test_days_range = 7
        
        print(f"\n📋 Test Parameters:")
        print(f"   User Prompt: '{test_prompt}'")
        print(f"   Days Range: {test_days_range}")
        print()
        
        # Prepare arguments
        arguments = {
            "user_prompt": test_prompt,
            "days_range": test_days_range
        }
        
        print("🚀 Calling check_wazuh_log via MCP...")
        print("-" * 30)
        
        # Execute tool via MCP bridge
        result = await mcp_bridge.execute_tool("check_wazuh_log", arguments)
        
        print("-" * 30)
        print("✅ Tool execution completed!")
        print()
        
        # Display result
        print("📊 RESULT:")
        print("=" * 40)
        print(f"Result type: {type(result)}")
        print()
        
        if isinstance(result, dict):
            print(f"Status: {result.get('status', 'N/A')}")
            print(f"Tool name: {result.get('tool_name', 'N/A')}")
            
            content = result.get('content', '')
            if content:
                print(f"Content length: {len(content)}")
                print("\n📝 Content preview:")
                print("-" * 20)
                # Show first 300 characters
                preview = content[:300] + "..." if len(content) > 300 else content
                print(preview)
                print("-" * 20)
                
                # Check if result looks valid
                if content.strip() and len(content) > 50:
                    print("✅ Result appears valid (has content)")
                else:
                    print("⚠️  Result may be invalid (too short or empty)")
            else:
                print("❌ No content in result")
                
        elif isinstance(result, str):
            print(f"String result length: {len(result)}")
            preview = result[:300] + "..." if len(result) > 300 else result
            print(f"Preview: {preview}")
        else:
            print(f"Result: {result}")
        
        # Save result to file for inspection
        output_file = project_root / "test_check_wazuh_log_mcp_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_prompt": test_prompt,
                "days_range": test_days_range,
                "result_type": str(type(result)),
                "result": result
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Result saved to: {output_file}")
        
        # Additional validation
        if isinstance(result, dict) and result.get('status') == 'success' and result.get('content'):
            print("\n🎉 SUCCESS: Tool returned valid formatted response!")
            return True
        else:
            print("\n⚠️  WARNING: Tool response may have issues")
            return False
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        print(f"📋 Error type: {type(e).__name__}")
        import traceback
        print("🔍 Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_check_wazuh_log_via_mcp())
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")