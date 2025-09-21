#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test SIMPLE dan LANGSUNG untuk check_wazuh_log tanpa kompleksitas
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.append(str(src_path))

from api.mcp_tool_bridge import FastMCPBridge

async def test_tool_directly():
    """Test tool secara langsung via MCP bridge"""
    print("="*80)
    print("🔍 DIRECT TEST - check_wazuh_log via MCP Bridge")
    print("="*80)
    
    bridge = None
    try:
        # Initialize bridge
        bridge = FastMCPBridge()
        
        # Test query yang bermasalah
        test_query = "xss kali linux attack"
        
        print(f"Query: {test_query}")
        print("Parameters yang akan dikirim:")
        print("  - query: xss kali linux attack")
        print("  - days_range: 7")
        print("  - max_results: 5")
        print()
        
        # Execute tool dengan parameter yang benar
        print("🚀 Executing tool...")
        result = await bridge.execute_tool(
            tool_name="check_wazuh_log",
            arguments={
                "query": test_query,
                "days_range": 7,
                "max_results": 5
            }
        )
        
        print("="*80)
        print("📊 HASIL:")
        print("="*80)
        
        if result["status"] == "success":
            print("✅ BERHASIL!")
            content = result["content"]
            if len(content) > 1500:
                print("FIRST 1500 CHARACTERS:")
                print("-" * 50)
                print(content[:1500])
                print("-" * 50)
                print(f"... [Total: {len(content)} characters] ...")
            else:
                print(content)
        else:
            print("❌ GAGAL!")
            print(f"Error: {result.get('message', 'Unknown error')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if bridge:
            try:
                await bridge.close()
            except:
                pass

async def main():
    """Main test"""
    print("🧪 TEST PERBAIKAN - check_wazuh_log")
    print("🎯 PASTIKAN TIDAK ADA PARAMETER ANEH!")
    print()
    
    success = await test_tool_directly()
    
    if success:
        print("\n🎉 TEST BERHASIL!")
        print("✅ Tool bekerja dengan parameter yang benar!")
        print("✅ Tidak ada error parameter tambahan!")
        print("🚀 SIAP DIGUNAKAN!")
    else:
        print("\n❌ TEST GAGAL!")
        print("Ada masalah yang perlu diperbaiki.")

if __name__ == "__main__":
    asyncio.run(main())