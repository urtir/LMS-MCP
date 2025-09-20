#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test specific SQL query CAG issue
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastmcp import Context
from src.api.wazuh_fastmcp_server import cag_system

class MockContext:
    async def info(self, message):
        print(f"INFO: {message}")
    
    async def error(self, message):
        print(f"ERROR: {message}")

async def test_sql_query():
    """Test the specific SQL query that caused the error."""
    print("🧪 Testing SQL Query CAG Issue")
    print("=" * 50)
    
    ctx = MockContext()
    
    # Test the exact query that failed
    query = "Identifikasi upaya eksekusi query SQL mencurigakan"
    
    print(f"Testing query: {query}")
    print("-" * 50)
    
    try:
        # Test the CAG system directly
        threat_events = await cag_system.search(query, k=10)
        
        print("✅ CAG search completed successfully!")
        print(f"Threat events found: {len(threat_events)}")
        
        # Test CAG query with cache
        if cag_system.knowledge_loaded:
            print("\n🔍 Testing CAG query generation...")
            cag_response = await cag_system.query_with_cache(
                f"Analisis ancaman keamanan berdasarkan query: '{query}'. Berikan analisis mendalam dan rekomendasi aksi.",
                max_tokens=500
            )
            print("✅ CAG query generation successful!")
            print(f"Response preview: {cag_response[:100] if cag_response else 'No response'}...")
        
        return True
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sql_query())