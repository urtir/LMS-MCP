#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Hybrid CAG + Semantic Search System
Author: AI Assistant
Version: 1.0.0

Tests the new hybrid approach that combines:
1. Cache-Augmented Generation (CAG) for threat context
2. Semantic search for precise log retrieval
3. Keyword fallback for reliability
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.wazuh_fastmcp_server import WazuhCAG

async def test_hybrid_system():
    """Test the hybrid CAG + semantic search system."""
    print("🚀 Starting Hybrid CAG + Semantic Search Test")
    print("=" * 50)
    
    # Initialize CAG system
    cag = WazuhCAG()
    print(f"✅ WazuhCAG initialized")
    print(f"   - Semantic search enabled: {cag.semantic_search_enabled}")
    
    # Build knowledge cache and embeddings
    print("\n📚 Building knowledge cache and vector embeddings...")
    success = await cag.create_knowledge_cache(limit=1000)
    
    if not success:
        print("❌ Failed to build knowledge cache")
        return
    
    print("✅ Knowledge cache and embeddings built successfully")
    
    # Test queries
    test_queries = [
        "brute force attack",
        "authentication failure", 
        "suspicious network activity",
        "malware detection",
        "user login anomaly"
    ]
    
    print("\n🔍 Testing hybrid search capabilities:")
    print("-" * 40)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔎 Test {i}: '{query}'")
        
        try:
            # Perform hybrid search
            results = await cag.search(query, k=3)
            
            print(f"   Found {len(results)} results")
            
            for j, log in enumerate(results, 1):
                search_type = log.get('search_type', 'unknown')
                score = log.get('similarity_score', log.get('threat_score', 0))
                
                print(f"   {j}. [{search_type.upper()}] Rule: {log.get('rule_description', 'N/A')}")
                print(f"      Score: {score:.3f} | Level: {log.get('rule_level', 'N/A')}")
                print(f"      Agent: {log.get('agent_name', 'N/A')}")
                
                # Show CAG response snippet
                cag_response = log.get('cag_response', '')
                if cag_response:
                    snippet = cag_response[:100] + "..." if len(cag_response) > 100 else cag_response
                    print(f"      CAG: {snippet}")
                
                print()
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Test semantic vs keyword comparison
    print("\n📊 Comparing Search Methods:")
    print("-" * 40)
    
    test_query = "authentication failure"
    
    # Test semantic only if available
    if cag.semantic_search_enabled:
        print(f"\n🧠 Semantic Search Results for: '{test_query}'")
        semantic_results = await cag.semantic_search_logs(test_query, k=3)
        
        for i, log in enumerate(semantic_results, 1):
            similarity = log.get('similarity_score', 0)
            print(f"   {i}. Similarity: {similarity:.3f} - {log.get('rule_description', 'N/A')}")
    
    # Test CAG response
    print(f"\n💬 CAG Response for: '{test_query}'")
    cag_response = await cag.query_with_cache(test_query)
    response_snippet = cag_response[:200] + "..." if len(cag_response) > 200 else cag_response
    print(f"   {response_snippet}")
    
    print("\n✅ Hybrid system test completed!")
    print("=" * 50)

async def test_vector_embeddings():
    """Test vector embeddings specifically."""
    print("\n🔬 Testing Vector Embeddings...")
    
    cag = WazuhCAG()
    
    if not cag.semantic_search_enabled:
        print("⚠️ Semantic search not available - skipping embedding test")
        return
    
    # Build embeddings
    print("Building embeddings...")
    await cag.build_vector_embeddings(force_rebuild=True)
    
    print(f"✅ Vector store size: {cag.vector_store.ntotal if cag.vector_store else 0}")
    print(f"✅ Embeddings mapping: {len(cag.log_embeddings)} entries")

if __name__ == "__main__":
    print("🔧 Hybrid CAG + Semantic Search Test Suite")
    print("Testing new implementation with vector embeddings")
    print()
    
    # Run tests
    asyncio.run(test_hybrid_system())
    asyncio.run(test_vector_embeddings())