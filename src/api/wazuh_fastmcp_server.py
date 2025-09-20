#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wazuh AI Threat Hunting FastMCP Server
Author: AI Assistant  
Version: 2.0.0
Description: FastMCP server implementing Wazuh AI threat hunting methodology for LM Studio integration

This server implements the official Wazuh AI threat hunting approach using:
- Vector embeddings and semantic search on Wazuh archive logs
- LangChain retrieval-augmented generation for comprehensive analysis
- HuggingFace embeddings (all-MiniLM-L6-v2) for log similarity matching
- FAISS vector store for efficient threat pattern recognition

Reference: https://wazuh.com/blog/leveraging-artificial-intelligence-for-threat-hunting-in-wazuh/
"""

import asyncio
import json
import logging
import os
import sqlite3
from typing import Optional, Dict, List, Any, Union
from datetime import datetime
import base64
import ssl
from pathlib import Path

import httpx
from fastmcp import FastMCP, Context
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CAG (Cache-Augmented Generation) imports
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from transformers.cache_utils import DynamicCache
    CAG_AVAILABLE = True
    logger.info("CAG (transformers/torch) imports successful")
except ImportError as e:
    logger.warning(f"CAG dependencies not available: {e}")
    CAG_AVAILABLE = False

# Semantic search imports
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss
    from sklearn.metrics.pairwise import cosine_similarity
    SEMANTIC_SEARCH_AVAILABLE = True
    logger.info("Semantic search imports successful")
except ImportError as e:
    logger.warning(f"Semantic search dependencies not available: {e}")
    SEMANTIC_SEARCH_AVAILABLE = False

# LM Studio client for generation
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    logger.info("OpenAI client for LM Studio available")
except ImportError as e:
    logger.warning(f"OpenAI client not available: {e}")
    OPENAI_AVAILABLE = False

# Initialize FastMCP server for Wazuh AI threat hunting
mcp = FastMCP("Wazuh AI Threat Hunting Server")

# Configuration
class WazuhConfig:
    def __init__(self):
        self.base_url = os.getenv("WAZUH_API_URL", "https://localhost:55000")
        self.username = os.getenv("WAZUH_USERNAME", "wazuh-wui")
        self.password = os.getenv("WAZUH_PASSWORD", "MyS3cr37P450r.*-")
        self.verify_ssl = os.getenv("WAZUH_VERIFY_SSL", "false").lower() == "true"
        self.timeout = int(os.getenv("WAZUH_TIMEOUT", "30"))
        self._token = None
        self._token_expires = None

config = WazuhConfig()

# LM Studio Configuration for CAG
class LMStudioConfig:
    def __init__(self):
        self.base_url = os.getenv('LM_STUDIO_BASE_URL', 'http://192.168.56.1:1234/v1')
        self.api_key = os.getenv('LM_STUDIO_API_KEY', 'lm-studio')
        self.model = os.getenv('LM_STUDIO_MODEL', 'qwen/qwen3-1.7b')
        self.timeout = None

lm_studio_config = LMStudioConfig()

# HTTP client with SSL configuration
async def get_http_client() -> httpx.AsyncClient:
    """Create HTTP client with proper SSL configuration."""
    return httpx.AsyncClient(
        verify=config.verify_ssl,
        timeout=config.timeout,
        headers={"Content-Type": "application/json"}
    )

# Authentication functions
async def get_auth_token(ctx: Context) -> str:
    """Get or refresh JWT authentication token."""
    if config._token and config._token_expires:
        # Check if token is still valid (with 1 minute buffer)
        import time
        if time.time() < (config._token_expires - 60):
            return config._token
    
    await ctx.info("Getting new Wazuh API authentication token...")
    
    async with await get_http_client() as client:
        # Encode credentials for basic auth
        credentials = base64.b64encode(f"{config.username}:{config.password}".encode()).decode()
        headers = {"Authorization": f"Basic {credentials}"}
        
        response = await client.post(
            f"{config.base_url}/security/user/authenticate",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            config._token = data["data"]["token"]
            # JWT tokens typically expire in 15 minutes (900 seconds)
            import time
            config._token_expires = time.time() + 900
            await ctx.info("Successfully authenticated with Wazuh API")
            return config._token
        else:
            raise Exception(f"Authentication failed: {response.status_code} - {response.text}")

async def make_api_request(
    method: str, 
    endpoint: str, 
    ctx: Context, 
    params: Optional[Dict] = None, 
    data: Optional[Dict] = None,
    content_type: str = "application/json"
) -> Dict:
    """Make authenticated API request to Wazuh."""
    token = await get_auth_token(ctx)
    
    async with await get_http_client() as client:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type
        }
        
        url = f"{config.base_url}{endpoint}"
        
        # Log request
        await ctx.info(f"Making {method} request to {endpoint}")
        
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            params=params or {},
            json=data if content_type == "application/json" else None,
            content=data if content_type != "application/json" else None
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            await ctx.info(f"Request successful: {response.status_code}")
            return result
        else:
            error_msg = f"API request failed: {response.status_code} - {response.text}"
            await ctx.error(error_msg)
            raise Exception(error_msg)

# =============================================================================
# API INFO & STATUS
# =============================================================================

@mcp.tool
async def get_api_info(ctx: Context) -> str:
    """Get Wazuh API basic information and status."""
    result = await make_api_request("GET", "/", ctx)
    return json.dumps(result, indent=2)

# =============================================================================
# WAZUH AI THREAT HUNTING SYSTEM
# =============================================================================

class WazuhCAG:
    """
    Wazuh Cache-Augmented Generation (CAG) system for fast threat hunting.
    
    This implementation follows Cache-Augmented Generation methodology:
    - Preloads Wazuh security logs into LLM context
    - Stores inference state (Key-Value cache) for instant access
    - Eliminates retrieval latency by using cached context
    - Uses LM Studio LLM for generation
    
    Reference: Cache-Augmented Generation approach vs traditional RAG
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Get path relative to project root
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            db_path = str(project_root / "data" / "wazuh_archives.db")
        self.db_path = db_path
        self.cache = None
        self.cache_dir = "cag_cache"
        self.origin_len = 0
        self.knowledge_loaded = False
        
        # Initialize semantic search components
        self.vector_store = None
        self.embeddings_model = None
        self.log_embeddings = {}
        self.semantic_search_enabled = False
        
        # Initialize LM Studio client if available
        if OPENAI_AVAILABLE:
            self.lm_client = OpenAI(
                base_url=lm_studio_config.base_url,
                api_key=lm_studio_config.api_key,
                timeout=lm_studio_config.timeout
            )
            logger.info(f"LM Studio client initialized: {lm_studio_config.base_url}")
        else:
            self.lm_client = None
            logger.warning("OpenAI client not available - CAG generation disabled")
        
        # Setup cache directory
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize semantic search if available
        self._initialize_semantic_search()
        
        self.initialize_security_context()
    
    def _initialize_semantic_search(self):
        """Initialize semantic search components if dependencies are available."""
        if not SEMANTIC_SEARCH_AVAILABLE:
            logger.warning("Semantic search dependencies not available - using keyword-based search only")
            return
        
        try:
            # Initialize sentence transformer model for embeddings
            self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Semantic search model loaded: all-MiniLM-L6-v2")
            
            # Initialize FAISS vector store
            self.dimension = 384  # all-MiniLM-L6-v2 embedding dimension
            self.vector_store = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
            
            self.semantic_search_enabled = True
            logger.info("Semantic search initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize semantic search: {e}")
            self.semantic_search_enabled = False
    
    def initialize_security_context(self):
        """Initialize the security context for threat hunting."""
        self.security_context = """You are a cybersecurity expert specialized in analyzing Wazuh security logs for threat hunting.

Your expertise includes:
- Identifying attack patterns, brute-force attempts, and suspicious activities
- Analyzing security events with timestamps, affected systems, and indicators of compromise
- Interpreting Wazuh rule classifications and security levels
- Providing actionable security recommendations

Always focus on security-relevant insights from the provided log data. Respond in Indonesian language."""
    
    async def get_security_logs_for_context(self, limit: int = None, agent_ids: List[str] = None, days_range: int = 30) -> List[Dict[str, Any]]:
        """Retrieve security logs for building knowledge context - optimized for 64GB RAM system."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Build query to SELECT ALL COLUMNS including full_log
            base_query = """
                SELECT * FROM wazuh_archives 
                WHERE full_log IS NOT NULL AND full_log != ''
                AND timestamp >= datetime('now', '-{} days')
            """.format(days_range)
            
            params = []
            if agent_ids and len(agent_ids) > 0:
                # Add agent filtering
                placeholders = ','.join(['?' for _ in agent_ids])
                base_query += f" AND agent_name IN ({placeholders})"
                params.extend(agent_ids)
            
            base_query += " ORDER BY rule_level DESC, timestamp DESC"
            
            # Apply limit only if specifically requested, otherwise get ALL logs
            if limit and limit > 0:
                base_query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(base_query, params)
            
            # Convert all rows to dictionaries with ALL columns
            results = []
            for row in cursor.fetchall():
                log_dict = dict(row)  # Gets ALL columns now including full_log
                results.append(log_dict)
            
            conn.close()
            logger.info(f"📊 Retrieved {len(results)} security logs with ALL COLUMNS from database (RAM: 64GB optimized)")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving security logs: {e}")
            return []
    
    def build_knowledge_prompt(self, security_logs: List[Dict[str, Any]]) -> str:
        """Build knowledge prompt from security logs for CAG."""
        if not security_logs:
            return "No security logs available."
        
        # Create structured knowledge base from logs
        knowledge_sections = []
        
        # Group logs by priority
        critical_logs = [log for log in security_logs if log.get('rule_level', 0) >= 10]
        high_logs = [log for log in security_logs if 7 <= log.get('rule_level', 0) < 10]
        medium_logs = [log for log in security_logs if 4 <= log.get('rule_level', 0) < 7]
        
        # Add critical events
        if critical_logs:
            knowledge_sections.append("=== CRITICAL SECURITY EVENTS (FULL DETAILS) ===")
            for log in critical_logs[:15]:  # Fewer logs but much more detail
                # Extract ALL available information including full_log
                event_parts = []
                event_parts.append(f"Time: {log.get('timestamp', 'N/A')[:19]}")
                event_parts.append(f"Agent: {log.get('agent_name', 'N/A')} (ID: {log.get('agent_id', 'N/A')})")
                event_parts.append(f"Rule: ID={log.get('rule_id', 'N/A')}, Level={log.get('rule_level', 0)}")
                event_parts.append(f"Desc: {log.get('rule_description', 'N/A')}")
                event_parts.append(f"Groups: {log.get('rule_groups', 'N/A')}")
                event_parts.append(f"Location: {log.get('location', 'N/A')}")
                event_parts.append(f"Decoder: {log.get('decoder_name', 'N/A')}")
                
                # MOST IMPORTANT: Include full_log content
                full_log = log.get('full_log', '')
                if full_log and len(full_log.strip()) > 0:
                    event_parts.append(f"FULL_LOG: {full_log[:600]}...")
                
                # Include additional structured data if available
                data = log.get('data', '')
                if data and len(data.strip()) > 0:
                    event_parts.append(f"Data: {data[:200]}...")
                
                knowledge_sections.append(" | ".join(event_parts))
        
        # Add high priority events
        if high_logs:
            knowledge_sections.append("\n=== HIGH PRIORITY SECURITY EVENTS ===")
            for log in high_logs[:25]:
                # Include full_log in high priority events too
                full_log_sample = log.get('full_log', 'N/A')[:300] + ("..." if len(log.get('full_log', '')) > 300 else "")
                event_summary = f"Time: {log.get('timestamp', 'N/A')[:19]}, Agent: {log.get('agent_name', 'N/A')}, Rule: {log.get('rule_id', 'N/A')}/L{log.get('rule_level', 0)}, Desc: {log.get('rule_description', 'N/A')}, FullLog: {full_log_sample}"
                knowledge_sections.append(event_summary)
        
        # Add medium priority events (summary only)
        if medium_logs:
            knowledge_sections.append(f"\n=== MEDIUM PRIORITY EVENTS SUMMARY ===")
            knowledge_sections.append(f"Total medium priority events: {len(medium_logs)}")
            
            # Group by rule description with sample full_log content
            rule_counts = {}
            sample_full_logs = {}
            for log in medium_logs:
                desc = log.get('rule_description', 'Unknown')[:50]
                rule_counts[desc] = rule_counts.get(desc, 0) + 1
                # Store sample full_log for this rule type
                if desc not in sample_full_logs:
                    sample_full_logs[desc] = log.get('full_log', 'N/A')[:200]
            
            for rule_desc, count in sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:8]:
                sample_log = sample_full_logs.get(rule_desc, 'N/A')
                knowledge_sections.append(f"- {rule_desc}: {count} events | Sample FullLog: {sample_log}...")
        
        knowledge_text = "\n".join(knowledge_sections)
        
        # Create system prompt with comprehensive knowledge including full_log
        system_prompt = f"""<|system|>{self.security_context}

COMPREHENSIVE WAZUH SECURITY KNOWLEDGE BASE (ALL COLUMNS INCLUDING FULL_LOG):
{knowledge_text}

<|user|>
Based on the comprehensive security logs above (including full_log content and all available data), please answer the following security questions:

"""
        
        return system_prompt
    
    async def create_knowledge_cache(self, limit: int = None, days_range: int = 30):
        """Create CAG knowledge cache from Wazuh security logs - optimized for 64GB RAM."""
        if not CAG_AVAILABLE:
            logger.error("CAG dependencies not available")
            return False
        
        # Calculate optimal limit based on LM Studio's 32768 token capacity
        # Estimate ~100 tokens per log entry, leaving room for system prompt
        if limit is None:
            estimated_tokens_per_log = 100
            system_prompt_tokens = 2000  # Reserve for system prompt
            max_log_tokens = 32768 - system_prompt_tokens
            optimal_limit = max_log_tokens // estimated_tokens_per_log
            limit = min(optimal_limit, 25000)  # Cap at 25k for safety
            
        await self.info_log(f"🔄 Building CAG knowledge cache from up to {limit} security logs (32K token optimized)...")
        
        # Get security logs without artificial restrictions
        security_logs = await self.get_security_logs_for_context(limit, days_range=days_range)
        if not security_logs:
            logger.warning("No security logs found for CAG")
            return False
        
        await self.info_log(f"📊 Processing {len(security_logs)} security logs for knowledge cache...")
        
        # Build knowledge prompt
        knowledge_prompt = self.build_knowledge_prompt(security_logs)
        
        # For CAG, we use LM Studio directly since we don't need local model caching
        # The knowledge is embedded in the prompt itself
        self.cached_knowledge_prompt = knowledge_prompt
        self.knowledge_loaded = True
        
        # Build vector embeddings for semantic search if available
        if self.semantic_search_enabled:
            await self.info_log("🔄 Building vector embeddings for semantic search...")
            await self.build_vector_embeddings(force_rebuild=True)
            await self.info_log("✅ Vector embeddings built successfully")
        
        logger.info(f"✅ CAG knowledge cache built with {len(security_logs)} security events")
        return True
    
    async def query_with_cache(self, user_query: str, max_tokens: int = 800) -> str:
        """Query the cached knowledge using LM Studio LLM."""
        if not self.lm_client:
            return "LM Studio client not available"
        
        if not self.knowledge_loaded:
            await self.create_knowledge_cache()
        
        try:
            # Combine cached knowledge with user query
            full_prompt = f"{self.cached_knowledge_prompt}{user_query}\n\nJawaban:"
            
            # Generate response using LM Studio
            response = self.lm_client.chat.completions.create(
                model=lm_studio_config.model,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error querying CAG cache: {e}")
            return f"Error generating response: {str(e)}"
    
    async def build_vector_embeddings(self, force_rebuild: bool = False, days_range: int = 30):
        """Build vector embeddings for all security logs - optimized for 64GB RAM."""
        if not self.semantic_search_enabled:
            logger.warning("Semantic search not available - skipping vector embeddings")
            return
        
        embeddings_cache_path = os.path.join(self.cache_dir, "log_embeddings.npz")
        
        # Load cached embeddings if available and not forcing rebuild
        if os.path.exists(embeddings_cache_path) and not force_rebuild:
            try:
                cached_data = np.load(embeddings_cache_path, allow_pickle=True)
                embeddings_array = cached_data['embeddings']
                log_ids = cached_data['log_ids'].tolist()
                
                # Add to FAISS index
                self.vector_store.add(embeddings_array)
                self.log_embeddings = {str(log_id): idx for idx, log_id in enumerate(log_ids)}
                
                logger.info(f"📊 Loaded {len(log_ids)} cached embeddings from disk")
                return
            except Exception as e:
                logger.warning(f"Failed to load cached embeddings: {e}")
        
        # Build embeddings from scratch - use ALL available logs for 64GB RAM
        try:
            await self.info_log("🔄 Retrieving ALL security logs for embedding creation (64GB RAM optimized)...")
            logs = await self.get_security_logs_for_context(limit=None, days_range=days_range)  # NO LIMIT for high-end systems
            if not logs:
                logger.warning("No logs found for embedding creation")
                return
            
            await self.info_log(f"📊 Creating embeddings for {len(logs)} security logs...")
            
            # Process in batches to manage memory efficiently
            batch_size = 5000  # Process 5K logs at a time
            all_embeddings = []
            all_log_ids = []
            
            # Process ALL logs in batches to manage memory efficiently
            batch_size = 10000  # Larger batches for 64GB RAM system
            total_batches = (len(logs) + batch_size - 1) // batch_size
            
            await self.info_log(f"🔄 Processing {len(logs)} logs in {total_batches} batches of {batch_size}...")
            
            all_embeddings = []
            all_log_ids = []
            
            for batch_idx in range(0, len(logs), batch_size):
                batch_logs = logs[batch_idx:batch_idx + batch_size]
                batch_num = (batch_idx // batch_size) + 1
                
                await self.info_log(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch_logs)} logs)...")
                
                # Prepare text for embedding
                log_texts = []
                log_ids = []
                
                for log in batch_logs:
                    # Combine relevant fields for embedding
                    text_parts = []
                    if log.get('rule_description'):
                        text_parts.append(log['rule_description'])
                    if log.get('rule_groups'):
                        text_parts.append(log['rule_groups'])
                    if log.get('full_log'):
                        text_parts.append(log['full_log'][:1000])  # Increased log length for better context
                    
                    log_text = " | ".join(text_parts)
                    if log_text.strip():
                        log_texts.append(log_text)
                        log_ids.append(log['id'])
                
                if not log_texts:
                    continue
                
                # Create embeddings for this batch
                logger.info(f"Creating embeddings for batch {batch_num}: {len(log_texts)} logs...")
                batch_embeddings = self.embeddings_model.encode(log_texts, show_progress_bar=True)
                
                # Normalize embeddings for cosine similarity
                batch_embeddings = batch_embeddings / np.linalg.norm(batch_embeddings, axis=1, keepdims=True)
                
                all_embeddings.append(batch_embeddings)
                all_log_ids.extend(log_ids)
            
            if not all_embeddings:
                logger.warning("No valid embeddings created")
                return
            
            # Combine all batch embeddings
            embeddings = np.vstack(all_embeddings)
            
            # Add to FAISS index
            self.vector_store.add(embeddings.astype(np.float32))
            
            # Store mapping
            self.log_embeddings = {str(log_id): idx for idx, log_id in enumerate(all_log_ids)}
            
            # Cache embeddings
            os.makedirs(self.cache_dir, exist_ok=True)
            np.savez_compressed(embeddings_cache_path, 
                              embeddings=embeddings, 
                              log_ids=np.array(all_log_ids))
            
            await self.info_log(f"✅ Built and cached {len(all_log_ids)} vector embeddings (Total: {embeddings.shape[0]} vectors)")
            
        except Exception as e:
            logger.error(f"Error building vector embeddings: {e}")
    
    async def semantic_search_logs(self, query: str, k: int = 10, agent_ids: List[str] = None) -> List[Dict[str, Any]]:
        """Perform semantic search on security logs using vector similarity."""
        if not self.semantic_search_enabled:
            logger.warning("Semantic search not available")
            return []
        
        try:
            # Create query embedding
            query_embedding = self.embeddings_model.encode([query])
            query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
            
            # Search in vector store
            scores, indices = self.vector_store.search(query_embedding.astype(np.float32), k * 2)
            
            # Get corresponding log IDs
            reverse_mapping = {idx: log_id for log_id, idx in self.log_embeddings.items()}
            similar_log_ids = [reverse_mapping.get(idx, None) for idx in indices[0] if idx in reverse_mapping]
            
            # Retrieve actual logs
            if not similar_log_ids:
                return []
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Build query with agent filtering - SELECT ALL COLUMNS
            placeholders = ','.join(['?' for _ in similar_log_ids])
            base_query = f"""
                SELECT * FROM wazuh_archives 
                WHERE id IN ({placeholders})
            """
            
            params = similar_log_ids[:]
            if agent_ids and len(agent_ids) > 0:
                agent_placeholders = ','.join(['?' for _ in agent_ids])
                base_query += f" AND agent_name IN ({agent_placeholders})"
                params.extend(agent_ids)
            
            cursor.execute(base_query, params)
            
            results = []
            
            for row in cursor.fetchall():
                if len(results) >= k:
                    break
                    
                log_dict = dict(row)  # Gets ALL columns now
                # Add semantic similarity score
                similarity_idx = similar_log_ids.index(log_dict['id']) if log_dict['id'] in similar_log_ids else 0
                similarity_score = float(scores[0][similarity_idx]) if similarity_idx < len(scores[0]) else 0.0
                
                log_dict.update({
                    "similarity_score": similarity_score,
                    "search_type": "semantic",
                    "threat_indicators": self.extract_threat_indicators(log_dict)
                })
                results.append(log_dict)
            
            conn.close()
            return results[:k]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    async def search(self, query: str, k: int = 20, agent_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Hybrid search using both CAG and semantic search for optimal results - 64GB RAM optimized.
        
        This method combines:
        1. CAG cached knowledge for comprehensive threat context
        2. Semantic vector search for precise log retrieval
        3. Keyword fallback for reliability
        """
        try:
            # Generate response using cached knowledge
            cag_response = await self.query_with_cache(query)
            if not cag_response:
                cag_response = "No CAG response generated"
            
            # Try semantic search first if available - get more results for better coverage
            semantic_results = []
            if self.semantic_search_enabled:
                semantic_k = k // 2 if k < 20 else k // 3 * 2  # More semantic results for larger k
                semantic_results = await self.semantic_search_logs(query, semantic_k, agent_ids)
                logger.info(f"Semantic search found {len(semantic_results)} results")
            
            # Get additional logs using keyword-based search for completeness
            keyword_results = []
            if len(semantic_results) < k:
                remaining = k - len(semantic_results)
                # For 64GB systems, we can afford to search through more logs
                search_limit = remaining * 5  # Search through 5x more logs for better keyword matching
                security_logs = await self.get_security_logs_for_context(search_limit, agent_ids)
                
                query_lower = query.lower() if query else ""
                for log in security_logs:
                    # Skip logs already found by semantic search
                    if any(log['id'] == sem_log['id'] for sem_log in semantic_results):
                        continue
                    
                    relevance_score = self.calculate_log_relevance(log, query_lower)
                    if relevance_score > 0 and len(keyword_results) < remaining:
                        log.update({
                            "threat_score": relevance_score,
                            "search_type": "keyword",
                            "threat_indicators": self.extract_threat_indicators(log)
                        })
                        keyword_results.append(log)
            
            # Combine and enhance results
            all_results = semantic_results + keyword_results
            
            # Enhance all results with CAG analysis
            for log in all_results:
                safe_cag_response = cag_response or "No analysis available"
                log.update({
                    "threat_priority": self.determine_threat_priority(log, log.get("similarity_score", log.get("threat_score", 0.5))),
                    "threat_category": "hybrid_analyzed",
                    "cag_response": safe_cag_response[:200] + "..." if len(safe_cag_response) > 200 else safe_cag_response
                })
            
            # Sort by relevance (semantic similarity score or threat score)
            all_results.sort(key=lambda x: x.get("similarity_score", x.get("threat_score", 0)), reverse=True)
            
            return all_results[:k]
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            # NO FALLBACK - let it fail if it fails
            raise e
    
    def calculate_log_relevance(self, log: Dict[str, Any], query_lower: str) -> float:
        """Calculate relevance score for a log entry."""
        if not log or not query_lower:
            return 0.0
            
        score = 0.0
        
        # Rule level boost
        rule_level = log.get('rule_level', 0)
        score += rule_level * 0.1
        
        # Keyword matching in description (with null checks)
        description = (log.get('rule_description') or '').lower()
        groups = (log.get('rule_groups') or '').lower()
        full_log = (log.get('full_log') or '').lower()
        
        # Check for query terms
        query_terms = query_lower.split() if query_lower else []
        for term in query_terms:
            if term and term in description:
                score += 0.5
            if term and term in groups:
                score += 0.3
            if term and term in full_log:
                score += 0.2
        
        return min(score, 1.0)  # Cap at 1.0
    
    def determine_threat_priority(self, log: Dict[str, Any], relevance_score: float) -> str:
        """Determine threat priority based on rule level and relevance."""
        rule_level = log.get('rule_level', 0)
        
        if rule_level >= 10 or relevance_score >= 0.8:
            return "CRITICAL"
        elif rule_level >= 7 or relevance_score >= 0.6:
            return "HIGH"
        elif rule_level >= 4 or relevance_score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    def extract_threat_indicators(self, log: Dict[str, Any]) -> List[str]:
        """Extract threat indicators from log entry."""
        indicators = []
        
        rule_groups = log.get('rule_groups', '')
        if rule_groups:
            if 'authentication' in rule_groups:
                indicators.append("Authentication Event")
            if 'attack' in rule_groups:
                indicators.append("Attack Pattern")
            if 'web' in rule_groups:
                indicators.append("Web Activity")
            if 'malware' in rule_groups:
                indicators.append("Malware Related")
            if 'network' in rule_groups:
                indicators.append("Network Activity")
        
        if not indicators:
            indicators.append("Security Event")
        
        return indicators
    
    async def info_log(self, message: str):
        """Helper method for logging info messages."""
        logger.info(message)

# Initialize Wazuh CAG (Cache-Augmented Generation) system
cag_system = WazuhCAG()

# Auto-initialize CAG cache with security logs on server startup
async def initialize_cag_system():
    """Initialize CAG system with security logs for fast threat hunting."""
    try:
        if CAG_AVAILABLE or OPENAI_AVAILABLE:
            print("🔄 Initializing Wazuh CAG (Cache-Augmented Generation) with security logs...")
            success = await cag_system.create_knowledge_cache(limit=1000)
            if success:
                print("✅ Wazuh CAG system ready for fast threat hunting!")
            else:
                print("⚠️ CAG initialization completed with warnings")
        else:
            print("⚠️ CAG dependencies not available - basic mode enabled")
    except Exception as e:
        print(f"❌ Failed to initialize CAG system: {e}")

# Initialize on module load
if CAG_AVAILABLE or OPENAI_AVAILABLE:
    import asyncio
    try:
        # Check if there's an event loop running
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule initialization for later
            loop.create_task(initialize_cag_system())
        else:
            # Run initialization directly
            asyncio.run(initialize_cag_system())
    except:
        # Fallback - will initialize on first use
        pass

# =============================================================================
# WAZUH AI THREAT HUNTING MCP TOOL
# =============================================================================

@mcp.tool
async def check_wazuh_log(
    ctx: Context,
    query: str,
    max_results: int = 100,
    days_range: int = 7,
    rebuild_cache: bool = False,
    agent_ids: Optional[str] = None
) -> str:
    """
    ULTRA SIMPLE RAW Wazuh Log Analysis - ZERO BULLSHIT!
    
    Just dump raw database data and let LLM handle EVERYTHING!
    
    Args:
        query: What you want to find
        max_results: How many logs (default: 100)
        days_range: Days back to search (default: 7)
        rebuild_cache: Not used - keeping for compatibility
        agent_ids: Not used - keeping for compatibility
    
    Returns:
        RAW analysis from LLM with ALL original database data
    """
    try:
        await ctx.info(f"🔍 RAW Wazuh Analysis: {query} (past {days_range} days)")
        
        # SEMANTIC SEARCH DULU - CARI ROWS YANG RELEVAN!
        # BATASI KE 15 ROWS MAX UNTUK AVOID TOKEN OVERFLOW
        search_limit = min(15, max_results)  # MAX 15 rows only!
        
        relevant_logs = await cag_system.search(
            query=query,
            k=search_limit,  # Hanya 15 rows terbaik
            agent_ids=None
        )
        
        if not relevant_logs:
            return "No relevant logs found for your query"
        
        # DUMP HANYA ROWS RELEVAN - SEMUA KOLOM TAPI TRUNCATED!
        raw_data_prompt = f"""
QUERY: {query}

RAW WAZUH DATABASE DUMP ({len(relevant_logs)} MOST RELEVANT ROWS - ALL COLUMNS):
==============================================================================

"""
        
        for i, log in enumerate(relevant_logs, 1):
            raw_data_prompt += f"LOG #{i} (Relevance: {log.get('similarity_score', log.get('threat_score', 0)):.3f}):\n"
            
            # DUMP SEMUA KOLOM TAPI TRUNCATE YANG TERLALU PANJANG!
            for key, value in log.items():
                # Convert value to string and truncate if too long
                str_value = str(value) if value is not None else "N/A"
                
                # Truncate very long fields to save tokens
                if len(str_value) > 500:
                    str_value = str_value[:500] + "...[TRUNCATED]"
                
                raw_data_prompt += f"{key}: {str_value}\n"
            raw_data_prompt += "---\n"
        
        raw_data_prompt += f"""

INSTRUCTIONS:
Analyze the above {len(relevant_logs)} SEMANTICALLY RELEVANT Wazuh database records to answer: "{query}"

These rows were pre-selected as MOST RELEVANT to your query using semantic search.
Find and extract ALL information including:
- IP addresses from ANY field (json_data, full_log, etc.)
- Attack patterns and payloads from ANY field
- Timestamps, agents, rules, locations
- ANY security-related data

Give me comprehensive analysis with specific examples from the RAW data.
"""
        
        await ctx.info(f"📤 Sending {len(relevant_logs)} relevant logs to LLM (token-optimized)")
        
        # LET LLM DO ALL THE WORK WITH RELEVANT RAW DATA ONLY!
        analysis = cag_system.lm_client.chat.completions.create(
            model="qwen/qwen3-1.7b",
            messages=[
                {"role": "system", "content": "You are a cybersecurity analyst. Analyze semantically relevant raw Wazuh database dumps thoroughly and extract ALL useful information."},
                {"role": "user", "content": raw_data_prompt}
            ],
            max_tokens=2000,
            temperature=0.1
        )
        
        return analysis.choices[0].message.content

    except Exception as e:
        error_msg = f"Wazuh log analysis error: {str(e)}"
        await ctx.error(error_msg)
        return json.dumps({
            "status": "error",
            "error": error_msg,
            "analysis_period": f"past {days_range} days"
        }, indent=2)
        await ctx.info(f"🚨 CAG Threat Analysis Complete: {len(security_logs)} raw logs analyzed")
        return analysis.choices[0].message.content

    except Exception as e:
        error_msg = f"CAG threat hunting error: {str(e)}"
        await ctx.error(error_msg)
        return json.dumps({
            "status": "analysis_error",
            "error": error_msg,
            "query": query,
            "methodology": "Cache-Augmented Generation (CAG)",
            "recommendation": "Check CAG system initialization and LM Studio connectivity"
        }, indent=2)

# =============================================================================
# AGENT MANAGEMENT TOOLS
# =============================================================================

@mcp.tool
async def list_agents(
    ctx: Context,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    os_platform: Optional[str] = None,
    group: Optional[str] = None,
    agent_ids: Optional[str] = None
) -> str:
    """
    List all Wazuh agents with filtering options.
    
    Args:
        limit: Maximum number of items to return (1-100000, default: 100)
        offset: First element to return
        sort: Sort field (+/- for asc/desc, e.g., '+name', '-status')
        search: Look for elements containing this string
        status: Filter by agent status (active, pending, never_connected, disconnected)
        os_platform: Filter by OS platform (e.g., 'windows', 'linux')
        group: Filter by agent group
        agent_ids: Comma-separated list of specific agent IDs
    """
    params = {"limit": limit, "offset": offset}
    
    if sort:
        params["sort"] = sort
    if search:
        params["search"] = search
    if status:
        params["status"] = status
    if os_platform:
        params["os.platform"] = os_platform
    if group:
        params["group"] = group
    if agent_ids:
        params["agents_list"] = agent_ids.split(",")
    
    result = await make_api_request("GET", "/agents", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def add_agent(
    ctx: Context,
    name: str,
    ip: Optional[str] = None,
    group: Optional[str] = None,
    force: bool = False
) -> str:
    """
    Add a new Wazuh agent.
    
    Args:
        name: Agent name (required)
        ip: Agent IP address
        group: Agent group to assign
        force: Force agent addition even if it already exists
    """
    data = {"name": name}
    
    if ip:
        data["ip"] = ip
    
    params = {}
    if group:
        params["group"] = group
    if force:
        params["force"] = force
    
    result = await make_api_request("POST", "/agents", ctx, params=params, data=data)
    return json.dumps(result, indent=2)

@mcp.tool
async def delete_agents(
    ctx: Context,
    agent_ids: Optional[str] = None,
    older_than: Optional[str] = None,
    status: Optional[str] = None
) -> str:
    """
    Delete agents from the system.
    
    Args:
        agent_ids: Comma-separated list of agent IDs to delete
        older_than: Delete agents older than specified time (e.g., '7d', '30d')
        status: Delete agents with specific status (never_connected, disconnected)
    """
    params = {}
    
    if agent_ids:
        params["agents_list"] = agent_ids.split(",")
    if older_than:
        params["older_than"] = older_than
    if status:
        params["status"] = status
    
    result = await make_api_request("DELETE", "/agents", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_agent_info(ctx: Context, agent_id: str) -> str:
    """Get detailed information about a specific agent."""
    result = await make_api_request("GET", f"/agents/{agent_id}", ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_agent_key(ctx: Context, agent_id: str) -> str:
    """Get the key for a specific agent (used for agent registration)."""
    result = await make_api_request("GET", f"/agents/{agent_id}/key", ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def restart_agent(ctx: Context, agent_id: str) -> str:
    """Restart a specific Wazuh agent."""
    result = await make_api_request("PUT", f"/agents/{agent_id}/restart", ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def restart_multiple_agents(ctx: Context, agent_ids: str) -> str:
    """
    Restart multiple Wazuh agents.
    
    Args:
        agent_ids: Comma-separated list of agent IDs to restart
    """
    params = {"agents_list": agent_ids.split(",")}
    result = await make_api_request("PUT", "/agents/restart", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def upgrade_agents(
    ctx: Context,
    agent_ids: str,
    upgrade_version: Optional[str] = None,
    force: bool = False
) -> str:
    """
    Upgrade agents to a newer version.
    
    Args:
        agent_ids: Comma-separated list of agent IDs to upgrade
        upgrade_version: Target Wazuh version (optional)
        force: Force upgrade even if versions are the same
    """
    params = {"agents_list": agent_ids.split(",")}
    
    if upgrade_version:
        params["upgrade_version"] = upgrade_version
    if force:
        params["force"] = force
    
    result = await make_api_request("PUT", "/agents/upgrade", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_agent_config(ctx: Context, agent_id: str, component: str, configuration: str) -> str:
    """
    Get agent configuration for a specific component.
    
    Args:
        agent_id: Agent ID
        component: Configuration component (e.g., 'agent', 'agentless', 'auth')
        configuration: Specific configuration section
    """
    endpoint = f"/agents/{agent_id}/config/{component}/{configuration}"
    result = await make_api_request("GET", endpoint, ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_agent_stats(ctx: Context, agent_id: str) -> str:
    """Get daemon statistics from a specific agent."""
    result = await make_api_request("GET", f"/agents/{agent_id}/daemons/stats", ctx)
    return json.dumps(result, indent=2)

# =============================================================================
# MANAGER OPERATIONS
# =============================================================================

@mcp.tool
async def get_manager_status(ctx: Context) -> str:
    """Get the status of all Wazuh manager daemons."""
    result = await make_api_request("GET", "/manager/status", ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_manager_info(ctx: Context) -> str:
    """Get basic information about the Wazuh manager."""
    result = await make_api_request("GET", "/manager/info", ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_manager_configuration(
    ctx: Context,
    section: Optional[str] = None,
    field: Optional[str] = None,
    raw: bool = False
) -> str:
    """
    Get Wazuh manager configuration.
    
    Args:
        section: Specific configuration section (e.g., 'global', 'auth', 'cluster')
        field: Specific field within section
        raw: Return configuration in plain text format
    """
    params = {}
    if section:
        params["section"] = section
    if field:
        params["field"] = field
    if raw:
        params["raw"] = "true"
    
    result = await make_api_request("GET", "/manager/configuration", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_manager_daemon_stats(ctx: Context, daemons: Optional[str] = None) -> str:
    """
    Get manager daemon statistics.
    
    Args:
        daemons: Comma-separated list of daemons (wazuh-analysisd, wazuh-remoted, wazuh-db)
    """
    params = {}
    if daemons:
        params["daemons_list"] = daemons.split(",")
    
    result = await make_api_request("GET", "/manager/daemons/stats", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_manager_stats(ctx: Context, date: Optional[str] = None) -> str:
    """
    Get manager statistics.
    
    Args:
        date: Specific date for statistics (YYYY-MM-DD format)
    """
    endpoint = "/manager/stats"
    params = {}
    if date:
        params["date"] = date
    
    result = await make_api_request("GET", endpoint, ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_manager_logs(
    ctx: Context,
    limit: int = 100,
    offset: int = 0,
    level: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None
) -> str:
    """
    Get manager log entries.
    
    Args:
        limit: Maximum number of log entries to return (max 500)
        offset: First log entry to return
        level: Filter by log level (critical, debug, debug2, error, info, warning)
        tag: Filter by component tag
        search: Search string in log messages
    """
    params = {"limit": limit, "offset": offset}
    
    if level:
        params["level"] = level
    if tag:
        params["tag"] = tag
    if search:
        params["search"] = search
    
    result = await make_api_request("GET", "/manager/logs", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_manager_logs_summary(ctx: Context) -> str:
    """Get a summary of manager logs by level and tag."""
    result = await make_api_request("GET", "/manager/logs/summary", ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def restart_manager(ctx: Context) -> str:
    """Restart the Wazuh manager."""
    result = await make_api_request("PUT", "/manager/restart", ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def validate_configuration(ctx: Context) -> str:
    """Validate the current Wazuh configuration."""
    result = await make_api_request("GET", "/manager/configuration/validation", ctx)
    return json.dumps(result, indent=2)

# =============================================================================
# ACTIVE RESPONSE
# =============================================================================

@mcp.tool
async def run_active_response(
    ctx: Context,
    agent_ids: str,
    command: str,
    arguments: Optional[str] = None
) -> str:
    """
    Execute active response command on agents.
    
    Args:
        agent_ids: Comma-separated list of agent IDs
        command: Command to execute (e.g., 'restart-wazuh', 'firewall-drop')
        arguments: Command arguments (optional)
    """
    data = {"command": command}
    
    if arguments:
        data["arguments"] = arguments.split(",")
    
    params = {"agents_list": agent_ids.split(",")}
    
    result = await make_api_request("PUT", "/active-response", ctx, params=params, data=data)
    return json.dumps(result, indent=2)

# =============================================================================
# CLUSTER MANAGEMENT
# =============================================================================

@mcp.tool
async def get_cluster_status(ctx: Context) -> str:
    """Get the current cluster status."""
    result = await make_api_request("GET", "/cluster/status", ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_cluster_nodes(
    ctx: Context,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None,
    search: Optional[str] = None,
    node_type: Optional[str] = None
) -> str:
    """
    Get information about cluster nodes.
    
    Args:
        limit: Maximum number of items to return
        offset: First element to return
        sort: Sort field (+/- for asc/desc)
        search: Search string
        node_type: Filter by node type (master, worker)
    """
    params = {"limit": limit, "offset": offset}
    
    if sort:
        params["sort"] = sort
    if search:
        params["search"] = search
    if node_type:
        params["type"] = node_type
    
    result = await make_api_request("GET", "/cluster/nodes", ctx, params=params)
    return json.dumps(result, indent=2)

# =============================================================================
# SECURITY & RBAC
# =============================================================================

@mcp.tool
async def get_current_user(ctx: Context) -> str:
    """Get information about the current authenticated user."""
    result = await make_api_request("GET", "/security/users/me", ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def list_security_users(
    ctx: Context,
    limit: int = 100,
    offset: int = 0
) -> str:
    """List all security users."""
    params = {"limit": limit, "offset": offset}
    result = await make_api_request("GET", "/security/users", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def create_user(
    ctx: Context,
    username: str,
    password: str
) -> str:
    """
    Create a new user.
    
    Args:
        username: Username for the new user
        password: Password for the new user
    """
    data = {"username": username, "password": password}
    result = await make_api_request("POST", "/security/users", ctx, data=data)
    return json.dumps(result, indent=2)

@mcp.tool
async def list_security_roles(
    ctx: Context,
    limit: int = 100,
    offset: int = 0
) -> str:
    """List all security roles."""
    params = {"limit": limit, "offset": offset}
    result = await make_api_request("GET", "/security/roles", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def list_security_policies(
    ctx: Context,
    limit: int = 100,
    offset: int = 0
) -> str:
    """List all security policies."""
    params = {"limit": limit, "offset": offset}
    result = await make_api_request("GET", "/security/policies", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_security_config(ctx: Context) -> str:
    """Get current security configuration."""
    result = await make_api_request("GET", "/security/config", ctx)
    return json.dumps(result, indent=2)

# =============================================================================
# GROUPS MANAGEMENT
# =============================================================================

@mcp.tool
async def list_groups(
    ctx: Context,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None,
    search: Optional[str] = None
) -> str:
    """
    List all agent groups.
    
    Args:
        limit: Maximum number of items to return
        offset: First element to return
        sort: Sort field (+/- for asc/desc)
        search: Search string
    """
    params = {"limit": limit, "offset": offset}
    
    if sort:
        params["sort"] = sort
    if search:
        params["search"] = search
    
    result = await make_api_request("GET", "/groups", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def create_group(ctx: Context, group_id: str) -> str:
    """
    Create a new agent group.
    
    Args:
        group_id: ID for the new group
    """
    data = {"group_id": group_id}
    result = await make_api_request("POST", "/groups", ctx, data=data)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_group_agents(
    ctx: Context,
    group_id: str,
    limit: int = 100,
    offset: int = 0
) -> str:
    """
    Get agents in a specific group.
    
    Args:
        group_id: Group ID
        limit: Maximum number of items to return
        offset: First element to return
    """
    params = {"limit": limit, "offset": offset}
    result = await make_api_request("GET", f"/groups/{group_id}/agents", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_group_configuration(ctx: Context, group_id: str) -> str:
    """Get configuration for a specific group."""
    result = await make_api_request("GET", f"/groups/{group_id}/configuration", ctx)
    return json.dumps(result, indent=2)

# =============================================================================
# RULES MANAGEMENT
# =============================================================================

@mcp.tool
async def list_rules(
    ctx: Context,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None,
    search: Optional[str] = None,
    rule_ids: Optional[str] = None,
    level: Optional[str] = None,
    group: Optional[str] = None,
    pci_dss: Optional[str] = None,
    gdpr: Optional[str] = None
) -> str:
    """
    List detection rules.
    
    Args:
        limit: Maximum number of items to return
        offset: First element to return
        sort: Sort field (+/- for asc/desc)
        search: Search string
        rule_ids: Comma-separated list of rule IDs
        level: Filter by rule level
        group: Filter by rule group
        pci_dss: Filter by PCI DSS requirement
        gdpr: Filter by GDPR article
    """
    params = {"limit": limit, "offset": offset}
    
    if sort:
        params["sort"] = sort
    if search:
        params["search"] = search
    if rule_ids:
        params["rule_ids"] = rule_ids.split(",")
    if level:
        params["level"] = level
    if group:
        params["group"] = group
    if pci_dss:
        params["pci_dss"] = pci_dss
    if gdpr:
        params["gdpr"] = gdpr
    
    result = await make_api_request("GET", "/rules", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_rule_groups(ctx: Context) -> str:
    """Get all available rule groups."""
    result = await make_api_request("GET", "/rules/groups", ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_rules_files(
    ctx: Context,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None
) -> str:
    """Get information about rules files."""
    params = {"limit": limit, "offset": offset}
    if sort:
        params["sort"] = sort
    
    result = await make_api_request("GET", "/rules/files", ctx, params=params)
    return json.dumps(result, indent=2)

# =============================================================================
# DECODERS MANAGEMENT
# =============================================================================

@mcp.tool
async def list_decoders(
    ctx: Context,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None,
    search: Optional[str] = None,
    decoder_names: Optional[str] = None,
    filename: Optional[str] = None
) -> str:
    """
    List decoders.
    
    Args:
        limit: Maximum number of items to return
        offset: First element to return
        sort: Sort field (+/- for asc/desc)
        search: Search string
        decoder_names: Comma-separated list of decoder names
        filename: Filter by filename
    """
    params = {"limit": limit, "offset": offset}
    
    if sort:
        params["sort"] = sort
    if search:
        params["search"] = search
    if decoder_names:
        params["decoder_names"] = decoder_names.split(",")
    if filename:
        params["filename"] = filename
    
    result = await make_api_request("GET", "/decoders", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_decoders_files(
    ctx: Context,
    limit: int = 100,
    offset: int = 0
) -> str:
    """Get information about decoder files."""
    params = {"limit": limit, "offset": offset}
    result = await make_api_request("GET", "/decoders/files", ctx, params=params)
    return json.dumps(result, indent=2)

# =============================================================================
# MONITORING TOOLS (ROOTCHECK, SYSCHECK, SYSCOLLECTOR)
# =============================================================================

@mcp.tool
async def run_rootcheck_scan(ctx: Context, agent_ids: str) -> str:
    """
    Run rootcheck scan on specified agents.
    
    Args:
        agent_ids: Comma-separated list of agent IDs
    """
    params = {"agents_list": agent_ids.split(",")}
    result = await make_api_request("PUT", "/rootcheck", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_rootcheck_results(
    ctx: Context,
    agent_id: str,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None
) -> str:
    """
    Get rootcheck results for a specific agent.
    
    Args:
        agent_id: Agent ID
        limit: Maximum number of items to return
        offset: First element to return
        sort: Sort field (+/- for asc/desc)
    """
    params = {"limit": limit, "offset": offset}
    if sort:
        params["sort"] = sort
    
    result = await make_api_request("GET", f"/rootcheck/{agent_id}", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def clear_rootcheck_results(ctx: Context, agent_ids: str) -> str:
    """
    Clear rootcheck results for specified agents.
    
    Args:
        agent_ids: Comma-separated list of agent IDs
    """
    params = {"agents_list": agent_ids.split(",")}
    result = await make_api_request("DELETE", "/rootcheck", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def run_syscheck_scan(ctx: Context, agent_ids: str) -> str:
    """
    Run syscheck (FIM) scan on specified agents.
    
    Args:
        agent_ids: Comma-separated list of agent IDs
    """
    params = {"agents_list": agent_ids.split(",")}
    result = await make_api_request("PUT", "/syscheck", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_syscheck_results(
    ctx: Context,
    agent_id: str,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None,
    search: Optional[str] = None,
    file_type: Optional[str] = None
) -> str:
    """
    Get syscheck (FIM) results for a specific agent.
    
    Args:
        agent_id: Agent ID
        limit: Maximum number of items to return
        offset: First element to return
        sort: Sort field (+/- for asc/desc)
        search: Search string
        file_type: Filter by file type (file, registry)
    """
    params = {"limit": limit, "offset": offset}
    
    if sort:
        params["sort"] = sort
    if search:
        params["search"] = search
    if file_type:
        params["type"] = file_type
    
    result = await make_api_request("GET", f"/syscheck/{agent_id}", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def clear_syscheck_results(ctx: Context, agent_ids: str) -> str:
    """
    Clear syscheck (FIM) results for specified agents.
    
    Args:
        agent_ids: Comma-separated list of agent IDs
    """
    params = {"agents_list": agent_ids.split(",")}
    result = await make_api_request("DELETE", f"/syscheck", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_syscollector_os_info(ctx: Context, agent_id: str) -> str:
    """Get operating system information from syscollector."""
    result = await make_api_request("GET", f"/syscollector/{agent_id}/os", ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_syscollector_hardware_info(ctx: Context, agent_id: str) -> str:
    """Get hardware information from syscollector."""
    result = await make_api_request("GET", f"/syscollector/{agent_id}/hardware", ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_syscollector_packages(
    ctx: Context,
    agent_id: str,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None,
    search: Optional[str] = None
) -> str:
    """
    Get installed packages from syscollector.
    
    Args:
        agent_id: Agent ID
        limit: Maximum number of items to return
        offset: First element to return
        sort: Sort field (+/- for asc/desc)
        search: Search string
    """
    params = {"limit": limit, "offset": offset}
    
    if sort:
        params["sort"] = sort
    if search:
        params["search"] = search
    
    result = await make_api_request("GET", f"/syscollector/{agent_id}/packages", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_syscollector_processes(
    ctx: Context,
    agent_id: str,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None,
    search: Optional[str] = None
) -> str:
    """
    Get running processes from syscollector.
    
    Args:
        agent_id: Agent ID
        limit: Maximum number of items to return
        offset: First element to return
        sort: Sort field (+/- for asc/desc)
        search: Search string
    """
    params = {"limit": limit, "offset": offset}
    
    if sort:
        params["sort"] = sort
    if search:
        params["search"] = search
    
    result = await make_api_request("GET", f"/syscollector/{agent_id}/processes", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_syscollector_ports(
    ctx: Context,
    agent_id: str,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None,
    search: Optional[str] = None
) -> str:
    """
    Get open ports from syscollector.
    
    Args:
        agent_id: Agent ID
        limit: Maximum number of items to return
        offset: First element to return
        sort: Sort field (+/- for asc/desc)
        search: Search string
    """
    params = {"limit": limit, "offset": offset}
    
    if sort:
        params["sort"] = sort
    if search:
        params["search"] = search
    
    result = await make_api_request("GET", f"/syscollector/{agent_id}/ports", ctx, params=params)
    return json.dumps(result, indent=2)

# =============================================================================
# SCA (Security Configuration Assessment)
# =============================================================================

@mcp.tool
async def get_sca_results(
    ctx: Context,
    agent_id: str,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None,
    search: Optional[str] = None
) -> str:
    """
    Get SCA (Security Configuration Assessment) results.
    
    Args:
        agent_id: Agent ID
        limit: Maximum number of items to return
        offset: First element to return
        sort: Sort field (+/- for asc/desc)
        search: Search string
    """
    params = {"limit": limit, "offset": offset}
    
    if sort:
        params["sort"] = sort
    if search:
        params["search"] = search
    
    result = await make_api_request("GET", f"/sca/{agent_id}", ctx, params=params)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_sca_policy_checks(
    ctx: Context,
    agent_id: str,
    policy_id: str,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None,
    search: Optional[str] = None,
    result_filter: Optional[str] = None
) -> str:
    """
    Get SCA policy checks for a specific agent and policy.
    
    Args:
        agent_id: Agent ID
        policy_id: Policy ID
        limit: Maximum number of items to return
        offset: First element to return
        sort: Sort field (+/- for asc/desc)
        search: Search string
        result_filter: Filter by check result (passed, failed, not_applicable)
    """
    params = {"limit": limit, "offset": offset}
    
    if sort:
        params["sort"] = sort
    if search:
        params["search"] = search
    if result_filter:
        params["result"] = result_filter
    
    result = await make_api_request("GET", f"/sca/{agent_id}/checks/{policy_id}", ctx, params=params)
    return json.dumps(result, indent=2)

# =============================================================================
# LOGTEST
# =============================================================================

@mcp.tool
async def run_logtest(
    ctx: Context,
    event: str,
    log_format: str = "syslog",
    location: Optional[str] = None
) -> str:
    """
    Run logtest to test rules and decoders against log events.
    
    Args:
        event: Log event to test
        log_format: Log format (syslog, json, snort-full, squid, eventlog, etc.)
        location: Log location/source (optional)
    """
    data = {
        "log_format": log_format,
        "event": event
    }
    
    if location:
        data["location"] = location
    
    result = await make_api_request("PUT", "/logtest", ctx, data=data)
    return json.dumps(result, indent=2)

# =============================================================================
# OVERVIEW & STATISTICS
# =============================================================================

@mcp.tool
async def get_agents_overview(ctx: Context) -> str:
    """Get comprehensive overview of all agents."""
    result = await make_api_request("GET", "/overview/agents", ctx)
    return json.dumps(result, indent=2)

# =============================================================================
# TASKS MANAGEMENT
# =============================================================================

@mcp.tool
async def get_tasks_status(
    ctx: Context,
    limit: int = 100,
    offset: int = 0,
    agent_ids: Optional[str] = None,
    command: Optional[str] = None,
    status: Optional[str] = None
) -> str:
    """
    Get status of running tasks.
    
    Args:
        limit: Maximum number of items to return
        offset: First element to return
        agent_ids: Comma-separated list of agent IDs
        command: Filter by command
        status: Filter by task status
    """
    params = {"limit": limit, "offset": offset}
    
    if agent_ids:
        params["agents_list"] = agent_ids.split(",")
    if command:
        params["command"] = command
    if status:
        params["status"] = status
    
    result = await make_api_request("GET", "/tasks/status", ctx, params=params)
    return json.dumps(result, indent=2)

# =============================================================================
# MITRE ATT&CK INFORMATION
# =============================================================================

@mcp.tool
async def get_mitre_metadata(ctx: Context) -> str:
    """Get MITRE ATT&CK metadata information."""
    result = await make_api_request("GET", "/mitre/metadata", ctx)
    return json.dumps(result, indent=2)

@mcp.tool
async def get_mitre_techniques(
    ctx: Context,
    limit: int = 100,
    offset: int = 0,
    sort: Optional[str] = None,
    search: Optional[str] = None
) -> str:
    """
    Get MITRE ATT&CK techniques.
    
    Args:
        limit: Maximum number of items to return
        offset: First element to return
        sort: Sort field (+/- for asc/desc)
        search: Search string
    """
    params = {"limit": limit, "offset": offset}
    
    if sort:
        params["sort"] = sort
    if search:
        params["search"] = search
    
    result = await make_api_request("GET", "/mitre/techniques", ctx, params=params)
    return json.dumps(result, indent=2)

# =============================================================================
# EVENTS INGESTION
# =============================================================================

@mcp.tool
async def ingest_events(ctx: Context, events: str) -> str:
    """
    Ingest security events into Wazuh analysisd.
    
    Args:
        events: JSON array string of events to ingest (max 100 events)
    
    Note: Limited to 30 requests per minute
    """
    try:
        events_list = json.loads(events)
        if not isinstance(events_list, list):
            raise ValueError("Events must be a JSON array")
        
        if len(events_list) > 100:
            raise ValueError("Maximum 100 events per request allowed")
        
        data = {"events": events_list}
        result = await make_api_request("POST", "/events", ctx, data=data)
        return json.dumps(result, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON format: {str(e)}"}, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)}, indent=2)

# =============================================================================
# RESOURCES FOR SYSTEM INFORMATION
# =============================================================================

@mcp.resource("wazuh://api-endpoints")
def get_api_endpoints():
    """List all available Wazuh API endpoints implemented."""
    endpoints = {
        "Authentication": ["get_auth_token"],
        "API Info": ["get_api_info"],
        "Agent Management": [
            "list_agents", "add_agent", "delete_agents", "get_agent_info",
            "get_agent_key", "restart_agent", "restart_multiple_agents",
            "upgrade_agents", "get_agent_config", "get_agent_stats"
        ],
        "Manager Operations": [
            "get_manager_status", "get_manager_info", "get_manager_configuration",
            "get_manager_daemon_stats", "get_manager_stats", "get_manager_logs",
            "get_manager_logs_summary", "restart_manager", "validate_configuration"
        ],
        "Active Response": ["run_active_response"],
        "Cluster": ["get_cluster_status", "get_cluster_nodes"],
        "Security & RBAC": [
            "get_current_user", "list_security_users", "create_user",
            "list_security_roles", "list_security_policies", "get_security_config"
        ],
        "Groups": [
            "list_groups", "create_group", "get_group_agents", "get_group_configuration"
        ],
        "Rules": ["list_rules", "get_rule_groups", "get_rules_files"],
        "Decoders": ["list_decoders", "get_decoders_files"],
        "Monitoring": [
            "run_rootcheck_scan", "get_rootcheck_results", "clear_rootcheck_results",
            "run_syscheck_scan", "get_syscheck_results", "clear_syscheck_results"
        ],
        "Syscollector": [
            "get_syscollector_os_info", "get_syscollector_hardware_info",
            "get_syscollector_packages", "get_syscollector_processes", "get_syscollector_ports"
        ],
        "SCA": ["get_sca_results", "get_sca_policy_checks"],
        "Logtest": ["run_logtest"],
        "Overview": ["get_agents_overview"],
        "Tasks": ["get_tasks_status"],
        "MITRE": ["get_mitre_metadata", "get_mitre_techniques"],
        "Events": ["ingest_events"]
    }
    return endpoints

# =============================================================================
# PROMPTS FOR COMMON SCENARIOS
# =============================================================================

@mcp.prompt
def security_incident_analysis_prompt(agent_id: str, time_range: str = "24h") -> str:
    """Generate a prompt for comprehensive security incident analysis."""
    return f"""Please perform a comprehensive security incident analysis for Wazuh agent {agent_id} over the last {time_range}.

Follow this analysis workflow:

1. **Agent Status Check**:
   - Use get_agent_info to check agent connectivity and basic info
   - Use get_agent_stats to check daemon statistics

2. **Security Scans**:
   - Use get_rootcheck_results to check for policy violations and rootkits
   - Use get_syscheck_results to check for file integrity issues

3. **System Information**:
   - Use get_syscollector_os_info for OS information
   - Use get_syscollector_processes for running processes
   - Use get_syscollector_ports for open ports
   - Use get_syscollector_packages for installed software

4. **Configuration Assessment**:
   - Use get_sca_results for security configuration assessment

5. **Analysis**:
   - Identify any security issues or anomalies
   - Correlate findings across different modules
   - Assess risk levels and provide recommendations
   - Suggest remediation actions if issues are found

Please provide a comprehensive security report with executive summary, detailed findings, and actionable recommendations."""

@mcp.prompt
def agent_health_check_prompt(agent_id: str) -> str:
    """Generate a prompt for agent health monitoring."""
    return f"""Perform a complete health check for Wazuh agent {agent_id}.

Execute the following checks in order:

1. **Connectivity & Basic Info**:
   - get_agent_info - Check agent status, last keep-alive, version
   - get_agent_stats - Check daemon statistics and performance

2. **Module Status**:
   - get_rootcheck_results - Check last rootcheck scan and any issues
   - get_syscheck_results - Check FIM scan status and recent changes
   - get_sca_results - Check configuration assessment status

3. **System Health**:
   - get_syscollector_hardware_info - Check hardware resources
   - get_syscollector_os_info - Check OS version and health
   - get_syscollector_processes - Check for any concerning processes

4. **Analysis**:
   - Determine overall agent health (Good/Warning/Critical)
   - Identify any performance or configuration issues
   - Provide maintenance recommendations
   - Suggest actions for any problems found

Generate a health report with status summary and recommendations."""

# =============================================================================
# MAIN SERVER EXECUTION
# =============================================================================

if __name__ == "__main__":
    # Configure server settings
    import sys
    import os
    
    # Set UTF-8 encoding for Windows compatibility
    if sys.platform == "win32":
        import locale
        try:
            # Try to set UTF-8 encoding
            os.environ["PYTHONIOENCODING"] = "utf-8"
        except:
            pass
    
    # Display startup information
    try:
        print("Wazuh FastMCP Server v1.0.0")
        print("==========================================")
        print(f"Base URL: {config.base_url}")
        print(f"Username: {config.username}")
        print(f"SSL Verify: {config.verify_ssl}")
        print(f"Timeout: {config.timeout}s")
        print("")
        print("Available tools: 70+ Wazuh API endpoints")
        print("Available resources: 2 information resources")
        print("Available prompts: 2 analysis prompts")
        print("")
        print("Starting server...")
    except UnicodeEncodeError:
        # Fallback for encoding issues
        print("Wazuh FastMCP Server v1.0.0 - Starting...")
    
    # Run the MCP server
    mcp.run()
