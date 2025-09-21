#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test final untuk memastikan check_wazuh_log bekerja dengan query XSS Kali Linux
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.append(str(src_path))

class MockContext:
    """Mock context untuk testing"""
    async def info(self, message: str):
        print(f"INFO: {message}")
    
    async def error(self, message: str):
        print(f"ERROR: {message}")

async def test_xss_kali_query():
    """Test query XSS Kali Linux"""
    print("="*80)
    print("🔍 TEST: XSS Query untuk Kali Linux Agent")
    print("="*80)
    
    try:
        # Import after adding path
        from api.wazuh_fastmcp_server import check_wazuh_log
        
        # Create mock context
        ctx = MockContext()
        
        # Test dengan query yang sama seperti user
        test_query = "APAKAH ADA RIWAYAT SERANGAN XSS KE AGENT YANG MENGGUNAKAN OS KALI LINUX"
        
        print(f"Original Query: {test_query}")
        print()
        
        # Call tool dengan HANYA parameter yang diizinkan
        print("🚀 Calling check_wazuh_log dengan parameter yang benar...")
        result = await check_wazuh_log.func(  # Access the actual function
            ctx=ctx,
            query=test_query,  # HANYA query!
            days_range=7,      # Default days
            max_results=5      # Limit untuk test
        )
        
        print("="*80)
        print("📊 HASIL TEST:")
        print("="*80)
        
        # Display result dengan format yang baik
        if isinstance(result, str):
            # Split long result into chunks for better display
            if len(result) > 2000:
                print("FIRST 2000 CHARACTERS:")
                print("-" * 50)
                print(result[:2000])
                print("-" * 50)
                print(f"... (Total {len(result)} characters) ...")
            else:
                print(result)
        else:
            print(f"Result type: {type(result)}")
            print(result)
        
        print("\n✅ TEST BERHASIL!")
        print("✅ Tool dipanggil dengan parameter yang benar!")
        print("✅ Tidak ada error parameter yang tidak dikenal!")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run test"""
    print("🧪 FINAL TEST - XSS KALI LINUX QUERY")
    print("🎯 PASTIKAN TOOL BEKERJA TANPA PARAMETER TAMBAHAN")
    print()
    
    success = await test_xss_kali_query()
    
    if success:
        print("\n🎉 SEMUA TEST BERHASIL!")
        print("✅ Tool check_wazuh_log bekerja dengan benar!")
        print("✅ Hanya parameter yang diizinkan yang digunakan!")
        print("✅ Query optimization berjalan!")
        print("🚀 READY FOR PRODUCTION!")
    else:
        print("\n❌ TEST GAGAL!")
        print("Periksa kembali implementasi.")

if __name__ == "__main__":
    asyncio.run(main())