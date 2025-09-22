#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script untuk check_wazuh_log tool
"""

import asyncio
import sys
import json
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

# Import the tool function
try:
    from src.api.wazuh_fastmcp_server import check_wazuh_log
    from fastmcp import Context
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

class MockContext:
    """Mock context for testing"""
    def __init__(self):
        self.logs = []
    
    async def info(self, message):
        print(f"ℹ️  {message}")
        self.logs.append(f"INFO: {message}")
    
    async def error(self, message):
        print(f"❌ {message}")
        self.logs.append(f"ERROR: {message}")

async def test_check_wazuh_log():
    """Test the check_wazuh_log tool"""
    
    print("🧪 Testing check_wazuh_log tool")
    print("=" * 50)
    
    # Create mock context
    ctx = MockContext()
    
    # Test parameters
    test_prompt = "apakah ada riwayat serangan xss?"
    test_days_range = 7
    
    print(f"📋 Test Parameters:")
    print(f"   User Prompt: '{test_prompt}'")
    print(f"   Days Range: {test_days_range}")
    print()
    
    try:
        print("🚀 Calling check_wazuh_log...")
        print("-" * 30)
        
        # Call the tool function
        result = await check_wazuh_log(ctx, test_prompt, test_days_range)
        
        print("-" * 30)
        print("✅ Tool execution completed!")
        print()
        
        # Display result
        print("📊 RESULT:")
        print("=" * 40)
        print(f"Result type: {type(result)}")
        print(f"Result length: {len(result) if isinstance(result, str) else 'N/A'}")
        print()
        
        if isinstance(result, str):
            print("📝 Result content:")
            print("-" * 20)
            # Show first 500 characters
            preview = result[:500] + "..." if len(result) > 500 else result
            print(preview)
            print("-" * 20)
            
            # Check if result looks valid
            if result.strip() and len(result) > 50:
                print("✅ Result appears valid (has content)")
            else:
                print("⚠️  Result may be invalid (too short or empty)")
        else:
            print(f"Result: {result}")
        
        print()
        print("📋 Context Logs:")
        for log in ctx.logs:
            print(f"   {log}")
        
        # Save result to file for inspection
        output_file = project_root / "test_check_wazuh_log_result.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Test Prompt: {test_prompt}\n")
            f.write(f"Days Range: {test_days_range}\n")
            f.write(f"Result Type: {type(result)}\n")
            f.write(f"Result Length: {len(result) if isinstance(result, str) else 'N/A'}\n")
            f.write("\n" + "="*50 + "\n")
            f.write("RESULT CONTENT:\n")
            f.write("="*50 + "\n")
            f.write(str(result))
        
        print(f"\n💾 Result saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        print(f"📋 Error type: {type(e).__name__}")
        import traceback
        print("🔍 Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_check_wazuh_log())