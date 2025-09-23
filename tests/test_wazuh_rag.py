#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Wazuh Archives RAG function
Tests the wazuh_archives_rag function with SQL injection query
"""

import asyncio
import sys
import json
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

# Import the RAG function
try:
    from src.api.wazuh_fastmcp_server import wazuh_archives_rag
except ImportError:
    # Alternative import path
    import sys
    sys.path.insert(0, str(project_root / "src" / "api"))
    from wazuh_fastmcp_server import wazuh_archives_rag

async def test_rag_function():
    """Test the Wazuh Archives RAG function with SQL injection query"""
    
    print("🧪 Testing Wazuh Archives RAG Function")
    print("=" * 50)
    
    # Test parameters
    test_query = "SQL injection"
    test_days_range = 30  # Look back 30 days for more results
    
    print(f"📋 Test Parameters:")
    print(f"   Query: '{test_query}'")
    print(f"   Days Range: {test_days_range}")
    print()
    
    try:
        print("🚀 Starting RAG search...")
        print("-" * 30)
        
        # Call the RAG function
        results = await wazuh_archives_rag(
            query=test_query,
            days_range=test_days_range
        )
        
        print("-" * 30)
        print(f"✅ RAG search completed!")
        print()
        
        # Display results
        if results:
            print(f"📊 RESULTS SUMMARY:")
            print(f"   Total relevant logs found: {len(results)}")
            print(f"   Similarity score range: {results[0]['similarity_score']:.4f} to {results[-1]['similarity_score']:.4f}")
            print()
            
            print("🔍 TOP 5 MOST RELEVANT LOGS:")
            print("=" * 60)
            
            for i, log in enumerate(results[:5], 1):
                print(f"\n📝 LOG #{i} (Similarity: {log['similarity_score']:.4f})")
                print("-" * 40)
                
                # Display key fields
                print(f"🕒 Timestamp: {log.get('timestamp', 'N/A')}")
                print(f"🖥️  Agent: {log.get('agent_name', 'N/A')} (ID: {log.get('agent_id', 'N/A')})")
                print(f"📏 Rule Level: {log.get('rule_level', 'N/A')}")
                print(f"🔍 Rule ID: {log.get('rule_id', 'N/A')}")
                print(f"📄 Rule Description: {log.get('rule_description', 'N/A')}")
                print(f"🏷️  Rule Groups: {log.get('rule_groups', 'N/A')}")
                print(f"📍 Location: {log.get('location', 'N/A')}")
                
                # Show partial full_log if available
                full_log = log.get('full_log', '')
                if full_log:
                    preview = full_log[:200] + "..." if len(full_log) > 200 else full_log
                    print(f"📋 Full Log Preview: {preview}")
                
                # Show search text preview
                search_text = log.get('search_text', '')
                if search_text:
                    print(f"🔎 Search Text: {search_text}")
            
            # Show all available columns from first result
            if results:
                print(f"\n📊 ALL AVAILABLE COLUMNS IN RESULTS:")
                print("-" * 40)
                columns = list(results[0].keys())
                for i, col in enumerate(columns, 1):
                    print(f"{i:2d}. {col}")
            
            # Save detailed results to JSON file
            output_file = project_root / "test_rag_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str, ensure_ascii=False)
            
            print(f"\n💾 Detailed results saved to: {output_file}")
            
        else:
            print("❌ No relevant logs found!")
            print("💡 Possible reasons:")
            print("   - No logs in the specified date range")
            print("   - No logs match the query semantically")
            print("   - Database connection issues")
            print("   - Semantic search dependencies not installed")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        print(f"📋 Error type: {type(e).__name__}")
        import traceback
        print("🔍 Full traceback:")
        traceback.print_exc()

async def test_multiple_queries():
    """Test with multiple different queries"""
    
    print("\n🧪 TESTING MULTIPLE QUERIES")
    print("=" * 50)
    
    test_queries = [
        "SQL injection",
        "brute force attack",
        "failed login",
        "suspicious activity",
        "malware detection"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        print("-" * 30)
        
        try:
            results = await wazuh_archives_rag(query, days_range=7)
            
            if results:
                print(f"✅ Found {len(results)} relevant logs")
                print(f"🎯 Top similarity: {results[0]['similarity_score']:.4f}")
            else:
                print("❌ No results found")
                
        except Exception as e:
            print(f"❌ Error: {e}")

async def main():
    """Main test function"""
    
    print("🧪 WAZUH ARCHIVES RAG FUNCTION TEST")
    print("=" * 60)
    print()
    
    # Test 1: Main SQL injection test
    await test_rag_function()
    
    # Test 2: Multiple queries test
    await test_multiple_queries()
    
    print("\n🏁 Testing completed!")

if __name__ == "__main__":
    asyncio.run(main())