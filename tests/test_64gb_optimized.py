#!/usr/bin/env python3
"""
Test script for 64GB RAM optimized Wazuh CAG + Semantic Search system
No limits, no fallbacks - pure performance testing
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.wazuh_fastmcp_server import WazuhCAG

async def main():
    print("=" * 60)
    print("🚀 TESTING 64GB RAM OPTIMIZED WAZUH CAG SYSTEM")
    print("=" * 60)
    print("Features:")
    print("- No artificial limits on security logs")
    print("- 32K token context window optimized")
    print("- Batch processing for unlimited embeddings")
    print("- No fallback mechanisms (fail fast)")
    print("- Enhanced semantic search results")
    print("=" * 60)
    
    # Initialize CAG system
    print("\n🔄 Initializing 64GB optimized Wazuh CAG system...")
    start_time = time.time()
    
    cag = WazuhCAG()
    
    print(f"Semantic search enabled: {cag.semantic_search_enabled}")
    if cag.semantic_search_enabled:
        print(f"Vector store dimension: {cag.dimension}")
        print(f"Embeddings model: {type(cag.embeddings_model).__name__}")
    
    # Build knowledge cache with NO LIMITS
    print("\n🔄 Building unlimited knowledge cache...")
    cache_start = time.time()
    success = await cag.create_knowledge_cache(limit=None, days_range=60)  # 60 days of data
    cache_time = time.time() - cache_start
    
    if success:
        print(f"✅ Knowledge cache built in {cache_time:.2f} seconds")
    else:
        print("❌ Failed to build knowledge cache")
        return
    
    init_time = time.time() - start_time
    print(f"✅ System initialized in {init_time:.2f} seconds")
    
    # Test queries with larger result sets
    test_queries = [
        ("advanced persistent threat", 50),
        ("malware infection patterns", 30),
        ("brute force authentication attempts", 40),
        ("network intrusion detection", 25),
        ("privilege escalation activities", 35),
        ("data exfiltration indicators", 20),
        ("suspicious file modifications", 45),
        ("lateral movement techniques", 30)
    ]
    
    print(f"\n🔍 Testing {len(test_queries)} advanced security queries...")
    print("=" * 60)
    
    total_results = 0
    total_query_time = 0
    
    for i, (query, k) in enumerate(test_queries, 1):
        print(f"\n--- Query {i}: '{query}' (requesting {k} results) ---")
        
        query_start = time.time()
        try:
            results = await cag.search(query, k=k)  # No agent filtering - search ALL
            query_time = time.time() - query_start
            total_query_time += query_time
            
            print(f"Found {len(results)} results in {query_time:.3f}s")
            total_results += len(results)
            
            # Show top results
            for j, result in enumerate(results[:5], 1):
                search_type = result.get("search_type", "unknown")
                if search_type == "semantic":
                    score = result.get("similarity_score", 0.0)
                    print(f"  {j}. [semantic] Similarity: {score:.3f} - Rule: {result.get('rule_description', 'N/A')[:80]}...")
                else:
                    score = result.get("threat_score", 0.0)
                    print(f"  {j}. [keyword] Threat Score: {score:.3f} - Rule: {result.get('rule_description', 'N/A')[:80]}...")
            
            if len(results) > 5:
                print(f"  ... and {len(results) - 5} more results")
                
        except Exception as e:
            query_time = time.time() - query_start
            print(f"❌ Query failed in {query_time:.3f}s: {str(e)}")
    
    # Performance summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Total initialization time: {init_time:.2f} seconds")
    print(f"Total query time: {total_query_time:.3f} seconds")
    print(f"Average query time: {total_query_time/len(test_queries):.3f} seconds")
    print(f"Total results found: {total_results}")
    print(f"Average results per query: {total_results/len(test_queries):.1f}")
    
    # Memory usage estimation
    if cag.semantic_search_enabled and cag.log_embeddings:
        embedding_count = len(cag.log_embeddings)
        estimated_memory = (embedding_count * cag.dimension * 4) / (1024**3)  # 4 bytes per float32, convert to GB
        print(f"Vector embeddings: {embedding_count:,} logs")
        print(f"Estimated embedding memory: {estimated_memory:.2f} GB")
    
    print("\n✅ 64GB RAM optimized system test completed!")

if __name__ == "__main__":
    asyncio.run(main())