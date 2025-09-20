#!/usr/bin/env python3
"""
Test script for hybrid CAG + Semantic Search implementation
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.api.wazuh_fastmcp_server import WazuhCAG

async def test_hybrid_search():
    """Test the hybrid CAG + semantic search functionality."""
    print("=" * 60)
    print("🔍 TESTING HYBRID CAG + SEMANTIC SEARCH SYSTEM")
    print("=" * 60)
    
    # Initialize CAG system
    cag = WazuhCAG()
    
    print("\n1. Testing semantic search availability...")
    print(f"Semantic search enabled: {cag.semantic_search_enabled}")
    
    if cag.semantic_search_enabled:
        print("✅ Semantic search dependencies loaded successfully")
        print(f"Embeddings model: {type(cag.embeddings_model).__name__}")
        print(f"Vector store dimension: {cag.dimension}")
    else:
        print("⚠️ Semantic search not available - will use keyword search only")
    
    print("\n2. Building knowledge cache and vector embeddings...")
    success = await cag.create_knowledge_cache(limit=500)
    
    if success:
        print("✅ Knowledge cache created successfully")
        if cag.semantic_search_enabled:
            print(f"✅ Vector embeddings built: {len(cag.log_embeddings)} logs indexed")
    else:
        print("❌ Failed to create knowledge cache")
        return
    
    # Test queries
    test_queries = [
        "brute force attack",
        "failed login attempts",
        "suspicious network activity",
        "malware detection",
        "authentication failures"
    ]
    
    print("\n3. Testing hybrid search with various queries...")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Query {i}: '{query}' ---")
        
        # Test with different agent filtering
        agent_filters = [None, ["agent1", "agent2"]]
        
        for j, agents in enumerate(agent_filters):
            agent_desc = f"with agents {agents}" if agents else "all agents"
            print(f"\nTesting {agent_desc}:")
            
            results = await cag.search(query, k=3, agent_ids=agents)
            
            print(f"Found {len(results)} results")
            
            for idx, result in enumerate(results, 1):
                search_type = result.get('search_type', 'unknown')
                similarity = result.get('similarity_score', 0)
                threat_score = result.get('threat_score', 0)
                
                print(f"  {idx}. [{search_type}] Rule: {result.get('rule_description', 'N/A')[:50]}...")
                if similarity > 0:
                    print(f"      Similarity: {similarity:.3f}")
                if threat_score > 0:
                    print(f"      Threat Score: {threat_score:.3f}")
                print(f"      Agent: {result.get('agent_name', 'N/A')}")
                print(f"      Level: {result.get('rule_level', 'N/A')}")
    
    print("\n4. Testing semantic search directly...")
    if cag.semantic_search_enabled:
        semantic_results = await cag.semantic_search_logs("failed authentication", k=5)
        print(f"Direct semantic search found {len(semantic_results)} results")
        
        for idx, result in enumerate(semantic_results, 1):
            print(f"  {idx}. Similarity: {result.get('similarity_score', 0):.3f}")
            print(f"      Rule: {result.get('rule_description', 'N/A')[:60]}...")
    else:
        print("⚠️ Semantic search not available for direct testing")
    
    print("\n5. Testing CAG response generation...")
    cag_response = await cag.query_with_cache("Analisis serangan brute force yang terdeteksi")
    print(f"CAG Response length: {len(cag_response)} characters")
    print(f"Response preview: {cag_response[:200]}...")
    
    print("\n" + "=" * 60)
    print("✅ HYBRID SYSTEM TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_hybrid_search())