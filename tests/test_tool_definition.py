#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test untuk memeriksa tool definition yang dikirim ke LM Studio
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.append(str(src_path))

async def test_mcp_tool_definition():
    """Test definition tool yang dikirim ke LM Studio"""
    print("="*80)
    print("🔍 CHECKING MCP TOOL DEFINITION")
    print("="*80)
    
    try:
        from api.mcp_tool_bridge import FastMCPBridge
        
        # Initialize bridge
        bridge = FastMCPBridge()
        
        # Load tools
        tools = await bridge.get_available_tools()
        
        # Find check_wazuh_log tool
        wazuh_tool = None
        for tool in tools:
            if tool["function"]["name"] == "check_wazuh_log":
                wazuh_tool = tool
                break
        
        if wazuh_tool:
            print("✅ Tool check_wazuh_log ditemukan!")
            print("📋 TOOL DEFINITION:")
            print("-" * 50)
            
            import json
            print(json.dumps(wazuh_tool, indent=2))
            
            print("-" * 50)
            print("📋 PARAMETERS:")
            
            properties = wazuh_tool["function"]["parameters"].get("properties", {})
            required = wazuh_tool["function"]["parameters"].get("required", [])
            
            for param_name, param_info in properties.items():
                is_required = "REQUIRED" if param_name in required else "OPTIONAL"
                param_type = param_info.get("type", "unknown")
                param_desc = param_info.get("description", "No description")
                
                print(f"  - {param_name}: {param_type} ({is_required})")
                print(f"    Description: {param_desc}")
            
            # Check for unwanted parameters
            unwanted_params = ["agent_ids", "os_platform", "status", "group"]
            found_unwanted = [p for p in properties.keys() if p in unwanted_params]
            
            if found_unwanted:
                print(f"\n❌ MASALAH DITEMUKAN: Parameter tidak diinginkan: {found_unwanted}")
                return False
            else:
                print(f"\n✅ BAIK: Tidak ada parameter yang tidak diinginkan!")
                
                # Check expected parameters
                expected_params = ["query", "max_results", "days_range", "rebuild_cache"]
                missing_params = [p for p in expected_params if p not in properties]
                
                if missing_params:
                    print(f"⚠️  PERINGATAN: Parameter yang hilang: {missing_params}")
                else:
                    print("✅ Semua parameter yang diharapkan ada!")
                
                return True
        else:
            print("❌ Tool check_wazuh_log TIDAK DITEMUKAN!")
            print("Available tools:")
            for tool in tools:
                print(f"  - {tool['function']['name']}")
            return False
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        try:
            await bridge.close()
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(test_mcp_tool_definition())
    
    if success:
        print("\n🎉 TOOL DEFINITION CORRECT!")
        print("✅ check_wazuh_log hanya memiliki parameter yang benar")
        print("✅ Tidak ada parameter os_platform atau agent_ids")
        print("🚀 SIAP UNTUK TESTING!")
    else:
        print("\n❌ MASALAH DITEMUKAN DALAM TOOL DEFINITION!")
        print("Perlu diperbaiki sebelum testing.")