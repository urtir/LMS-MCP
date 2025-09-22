#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wazuh API FastMCP Server
Author: AI Assistant  
Version: 2.0.0
Description: FastMCP server for Wazuh API operations

This server provides comprehensive Wazuh API access including:
- Agent management (list, add, delete, restart, upgrade)
- Manager operations (status, configuration, logs)
- Security & RBAC (users, roles, policies)
- Groups management
- Rules and decoders
- Active response
- Cluster management
- System monitoring tools
"""

import asyncio
import json
import logging
import os
import sys
import sqlite3
from typing import Optional, Dict, List, Any, Union
from datetime import datetime
import base64
import ssl
from pathlib import Path

# Add config directory to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
from config.config_manager import ConfigManager
config = ConfigManager()

import httpx
from fastmcp import FastMCP, Context
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LM Studio client for response formatting
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    logger.info("OpenAI client for LM Studio available")
except ImportError as e:
    logger.warning(f"OpenAI client not available: {e}")
    OPENAI_AVAILABLE = False

# Semantic search dependencies for RAG
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss
    SEMANTIC_SEARCH_AVAILABLE = True
    logger.info("Semantic search dependencies available for RAG")
except ImportError as e:
    logger.warning(f"Semantic search dependencies not available: {e}")
    SEMANTIC_SEARCH_AVAILABLE = False

# Initialize FastMCP server for Wazuh API
mcp = FastMCP("Wazuh API Server")

# Configuration using JSON config
class WazuhConfig:
    def __init__(self):
        self.base_url = config.get("network.WAZUH_API_URL")
        self.username = config.get("wazuh.WAZUH_USERNAME")
        self.password = config.get("security.WAZUH_PASSWORD")
        self.verify_ssl = config.get("wazuh.WAZUH_VERIFY_SSL").lower() == "true"
        self.timeout = int(config.get("wazuh.WAZUH_TIMEOUT"))
        self._token = None
        self._token_expires = None
        
        # Validate required config
        if not all([self.base_url, self.username, self.password]):
            raise ValueError("Missing required Wazuh config in JSON!")

wazuh_config = WazuhConfig()

# LM Studio Configuration for response formatting
class LMStudioConfig:
    def __init__(self):
        self.base_url = config.get('network.LM_STUDIO_BASE_URL')
        self.api_key = config.get('ai_model.LM_STUDIO_API_KEY')
        self.model = config.get('ai_model.LM_STUDIO_MODEL')
        self.max_tokens = int(config.get('ai_model.AI_MAX_TOKENS'))
        self.temperature = float(config.get('ai_model.AI_TEMPERATURE'))
        
        # Validate required config
        if not all([self.base_url, self.api_key, self.model]):
            raise ValueError("Missing required LM Studio config for response formatting!")

lm_studio_config = LMStudioConfig()

# Initialize LM Studio client
if OPENAI_AVAILABLE:
    lm_client = OpenAI(
        base_url=lm_studio_config.base_url,
        api_key=lm_studio_config.api_key
    )
    logger.info(f"LM Studio client initialized: {lm_studio_config.base_url}")
else:
    lm_client = None
    logger.warning("LM Studio client not available - raw responses will be returned")

# HTTP client with SSL configuration
async def get_http_client() -> httpx.AsyncClient:
    """Create HTTP client with proper SSL configuration."""
    return httpx.AsyncClient(
        verify=wazuh_config.verify_ssl,
        timeout=wazuh_config.timeout,
        headers={"Content-Type": "application/json"}
    )

# Authentication functions
async def get_auth_token(ctx: Context) -> str:
    """Get or refresh JWT authentication token."""
    if wazuh_config._token and wazuh_config._token_expires:
        # Check if token is still valid (with 1 minute buffer)
        import time
        if time.time() < (wazuh_config._token_expires - 60):
            return wazuh_config._token
    
    await ctx.info("Getting new Wazuh API authentication token...")
    
    async with await get_http_client() as client:
        # Encode credentials for basic auth
        credentials = base64.b64encode(f"{wazuh_config.username}:{wazuh_config.password}".encode()).decode()
        headers = {"Authorization": f"Basic {credentials}"}
        
        response = await client.post(
            f"{wazuh_config.base_url}/security/user/authenticate",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            wazuh_config._token = data["data"]["token"]
            # JWT tokens typically expire in 15 minutes (900 seconds)
            import time
            wazuh_config._token_expires = time.time() + 900
            await ctx.info("Successfully authenticated with Wazuh API")
            return wazuh_config._token
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
        
        url = f"{wazuh_config.base_url}{endpoint}"
        
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
# LLM POST-PROCESSING SYSTEM
# =============================================================================

async def format_with_llm(raw_json: str, tool_name: str, user_context: str, ctx: Context) -> str:
    """
    Universal LLM formatter for all Wazuh API responses.
    Converts raw JSON to human-readable, contextual responses.
    """
    if not OPENAI_AVAILABLE or not lm_client:
        await ctx.info("LLM formatting not available - returning raw response")
        return raw_json
    
    try:
        # Create context-aware prompt based on tool type
        system_prompt = create_system_prompt(tool_name)
        user_prompt = create_user_prompt(raw_json, tool_name, user_context)
        
        await ctx.info(f"🤖 Processing {tool_name} response with LLM...")
        
        response = lm_client.chat.completions.create(
            model=lm_studio_config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=lm_studio_config.max_tokens // 2,  # Use half for formatting
            temperature=lm_studio_config.temperature
        )
        
        formatted_response = response.choices[0].message.content
        await ctx.info("✅ LLM formatting completed")
        return formatted_response
        
    except Exception as e:
        await ctx.error(f"LLM formatting failed: {e}")
        return f"LLM formatting error: {e}\n\nRaw response:\n{raw_json}"

def create_system_prompt(tool_name: str) -> str:
    """Create universal system prompt for all tools - NO keyword detection."""
    
    return """You are a Wazuh security platform expert. Your task is to format JSON API responses into clear, professional, human-readable information.

Your responsibilities:
- Convert technical JSON data into easy-to-understand format
- Present information in Indonesian language
- Use clear structure with bullet points and formatting
- Highlight important status information and critical details
- Provide context and explanations for technical terms
- Summarize key findings at the end
- Make the information accessible to both technical and non-technical users

Always maintain professional tone and focus on clarity and usefulness of the information."""

def create_user_prompt(raw_json: str, tool_name: str, user_context: str) -> str:
    """Create user prompts with context and raw data."""
    
    return f"""Tugas: Format respons Wazuh API menjadi informasi yang mudah dipahami.

Tool yang dipanggil: {tool_name}
Konteks permintaan: {user_context}

Data mentah dari Wazuh API:
{raw_json}

Instruksi:
1. Analisis data JSON dan ekstrak informasi penting
2. Format dalam bahasa Indonesia yang jelas dan profesional
3. Gunakan bullet points dan struktur yang rapi
4. Highlight informasi kritis atau yang memerlukan perhatian
5. Berikan context keamanan jika relevan
6. Sertakan ringkasan di akhir jika data banyak

Format respons yang diinginkan:
- Header dengan ringkasan total
- Detail terstruktur dengan bullet points
- Highlight status atau kondisi penting
- Rekomendasi aksi jika diperlukan"""

# =============================================================================
# WAZUH ARCHIVES RAG SYSTEM
# =============================================================================

async def wazuh_archives_rag(query: str, days_range: int = 7) -> List[Dict[str, Any]]:
    """
    Retrieval-Augmented Generation (RAG) function for Wazuh archives database.
    
    Performs semantic search on ALL columns of wazuh_archives database to find
    the top 15 most relevant security log entries for the given query.
    
    Args:
        query: Search query string
        days_range: Number of days to look back (default: 7)
        
    Returns:
        List of dictionaries containing top 15 relevant log entries with ALL columns
    """
    
    if not SEMANTIC_SEARCH_AVAILABLE:
        logger.warning("Semantic search not available - cannot perform RAG")
        return []
    
    try:
        # Database path
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent
        db_path = str(project_root / "data" / "wazuh_archives.db")
        
        logger.info(f"🔍 Starting RAG search for query: '{query}' (last {days_range} days)")
        
        # Step 1: Fetch ALL rows and columns from database within date range
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        # Query to get ALL columns from last N days
        query_sql = """
            SELECT * FROM wazuh_archives 
            WHERE datetime(substr(timestamp, 1, 19)) >= datetime('now', '-{} days')
            ORDER BY timestamp DESC
        """.format(days_range)
        
        cursor.execute(query_sql)
        all_logs = []
        
        logger.info(f"📊 Fetching logs from database...")
        
        for row in cursor.fetchall():
            log_dict = dict(row)  # Convert row to dictionary with ALL columns
            all_logs.append(log_dict)
        
        conn.close()
        
        if not all_logs:
            logger.warning(f"No logs found in last {days_range} days")
            return []
        
        logger.info(f"📋 Retrieved {len(all_logs)} total logs from database")
        
        # Step 2: Prepare text for semantic search
        # Combine key fields to create searchable text for each log
        log_texts = []
        log_mappings = []
        
        for i, log in enumerate(all_logs):
            # Create searchable text from ALL available fields
            text_parts = []
            
            # Add all non-null string values to searchable text
            for key, value in log.items():
                if value is not None and str(value).strip():
                    # Include field name and value for better context
                    text_parts.append(f"{key}: {str(value)}")
            
            # Combine all fields into one searchable text
            combined_text = " | ".join(text_parts)
            log_texts.append(combined_text)
            log_mappings.append(i)  # Map text index to log index
        
        if not log_texts:
            logger.warning("No searchable text found in logs")
            return []
        
        # Step 3: Initialize semantic search model
        logger.info("🧠 Initializing semantic search model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Step 4: Create embeddings for all log texts
        logger.info(f"🔢 Creating embeddings for {len(log_texts)} logs...")
        log_embeddings = model.encode(log_texts)
        
        # Step 5: Create query embedding
        logger.info(f"🎯 Creating query embedding for: '{query}'")
        query_embedding = model.encode([query])
        
        # Step 6: Calculate similarity scores
        logger.info("📊 Calculating similarity scores...")
        
        # Normalize embeddings for cosine similarity
        log_embeddings_norm = log_embeddings / np.linalg.norm(log_embeddings, axis=1, keepdims=True)
        query_embedding_norm = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
        
        # Calculate cosine similarity
        similarities = np.dot(log_embeddings_norm, query_embedding_norm.T).flatten()
        
        # Step 7: Get top 15 most relevant logs
        top_15_indices = np.argsort(similarities)[-15:][::-1]  # Top 15, descending order
        
        # Step 8: Prepare results with similarity scores
        results = []
        for idx in top_15_indices:
            log_index = log_mappings[idx]
            log_entry = all_logs[log_index].copy()  # Copy to avoid modifying original
            log_entry['similarity_score'] = float(similarities[idx])
            log_entry['search_text'] = log_texts[idx][:200] + "..." if len(log_texts[idx]) > 200 else log_texts[idx]
            results.append(log_entry)
        
        logger.info(f"✅ RAG search completed. Found {len(results)} relevant logs")
        logger.info(f"📈 Similarity scores range: {results[0]['similarity_score']:.3f} to {results[-1]['similarity_score']:.3f}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in RAG search: {e}")
        return []

# =============================================================================
# WAZUH LOG ANALYSIS MCP TOOL
# =============================================================================

@mcp.tool
async def check_wazuh_log(ctx: Context, user_prompt: str, days_range: int = 7) -> str:
    """
    Intelligent Wazuh log analysis using RAG (Retrieval-Augmented Generation).
    
    This tool analyzes user requests and searches Wazuh archives for relevant security logs.
    It uses LLM to generate optimal search queries and provides human-readable analysis.
    
    Args:
        user_prompt: User's security question or analysis request
        days_range: Number of days to search back (default: 7)
        
    Returns:
        Comprehensive security analysis based on relevant Wazuh logs
    """
    
    if not OPENAI_AVAILABLE or not lm_client:
        await ctx.error("LLM not available for log analysis")
        return "❌ LLM service not available for Wazuh log analysis"
    
    if not SEMANTIC_SEARCH_AVAILABLE:
        await ctx.error("Semantic search not available for RAG")
        return "❌ Semantic search dependencies not available for log analysis"
    
    try:
        await ctx.info(f"🔍 Analyzing user request: '{user_prompt}'")
        
        # Step 1: Generate optimal search query using LLM
        await ctx.info("🧠 Generating search query with LLM...")
        
        query_generation_prompt = f"""You are a cybersecurity expert specializing in Wazuh SIEM log analysis. 

Your task is to convert the user's security question into an optimal search query for semantic search on Wazuh security logs.

User's request: "{user_prompt}"

Generate a focused search query that will find the most relevant security logs. Consider:
- Security events, attacks, threats
- System activities, authentication, network events  
- Malware, intrusions, anomalies
- Specific security terms and indicators

Return ONLY the search query string, nothing else. Make it specific and security-focused.

Examples:
User: "Are there any SQL injection attacks?" → Query: "SQL injection attack web application vulnerability"
User: "Check for brute force login attempts" → Query: "brute force login authentication failed attempts"
User: "Any malware detected recently?" → Query: "malware detection virus trojan malicious file"

Query:"""

        query_response = lm_client.chat.completions.create(
            model=lm_studio_config.model,
            messages=[
                {"role": "user", "content": query_generation_prompt}
            ],
            max_tokens=50,  # Short response for query
            temperature=0.3  # Lower temperature for focused results
        )
        
        generated_query = query_response.choices[0].message.content.strip()
        await ctx.info(f"✅ Generated search query: '{generated_query}'")
        
        # Step 2: Search Wazuh archives using RAG
        await ctx.info(f"🔎 Searching Wazuh archives (last {days_range} days)...")
        
        rag_results = await wazuh_archives_rag(
            query=generated_query,
            days_range=days_range
        )
        
        if not rag_results:
            await ctx.info("No relevant logs found")
            return f"""🔍 **Analisis Log Wazuh**

**Permintaan:** {user_prompt}
**Pencarian:** {generated_query}
**Periode:** {days_range} hari terakhir

❌ **Tidak ada log yang relevan ditemukan**

**Kemungkinan penyebab:**
- Tidak ada aktivitas terkait dalam periode yang ditentukan
- Query pencarian terlalu spesifik
- Sistem sedang normal tanpa ancaman yang terdeteksi

**Rekomendasi:**
- Coba perluas rentang waktu pencarian
- Gunakan kata kunci yang lebih umum
- Periksa konfigurasi Wazuh untuk memastikan log dikumpulkan dengan benar"""

        await ctx.info(f"📊 Found {len(rag_results)} relevant logs")
        
        # Step 3: Prepare data for LLM analysis
        # Create summary of findings for LLM processing
        logs_summary = {
            "user_request": user_prompt,
            "search_query": generated_query, 
            "days_searched": days_range,
            "total_logs_found": len(rag_results),
            "top_logs": []
        }
        
        # Include top 10 most relevant logs for analysis
        for i, log in enumerate(rag_results[:10], 1):
            log_summary = {
                "rank": i,
                "similarity_score": log.get('similarity_score', 0),
                "timestamp": log.get('timestamp', 'N/A'),
                "agent_name": log.get('agent_name', 'N/A'),
                "rule_level": log.get('rule_level', 'N/A'),
                "rule_description": log.get('rule_description', 'N/A'),
                "rule_groups": log.get('rule_groups', 'N/A'),
                "location": log.get('location', 'N/A'),
                "full_log": log.get('full_log', '')[:300] + "..." if len(log.get('full_log', '')) > 300 else log.get('full_log', '')
            }
            logs_summary["top_logs"].append(log_summary)
        
        # Step 4: Generate comprehensive analysis using LLM
        await ctx.info("🤖 Generating security analysis with LLM...")
        
        analysis_data = json.dumps(logs_summary, indent=2, ensure_ascii=False)
        
        # Format with LLM for final human-readable output
        formatted_response = await format_with_llm(
            raw_json=analysis_data,
            tool_name="check_wazuh_log",
            user_context=f"User meminta analisis keamanan: '{user_prompt}'. Ditemukan {len(rag_results)} log relevan dari pencarian '{generated_query}' dalam {days_range} hari terakhir.",
            ctx=ctx
        )
        
        await ctx.info("✅ Security analysis completed")
        return formatted_response
        
    except Exception as e:
        await ctx.error(f"Error in Wazuh log analysis: {e}")
        return f"""❌ **Error dalam Analisis Log Wazuh**

**Permintaan:** {user_prompt}
**Error:** {str(e)}

**Solusi:**
- Periksa koneksi ke database Wazuh
- Pastikan layanan LLM berjalan
- Coba lagi dalam beberapa saat

**Detail Error:** {type(e).__name__}"""

# =============================================================================
# API INFO & STATUS
# =============================================================================

@mcp.tool
async def get_api_info(ctx: Context) -> str:
    """Get Wazuh API basic information and status."""
    result = await make_api_request("GET", "/", ctx)
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_api_info", 
        user_context="User meminta informasi dasar dan status API Wazuh",
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Create context for LLM
    filter_context = []
    if status: filter_context.append(f"status: {status}")
    if os_platform: filter_context.append(f"platform: {os_platform}")
    if search: filter_context.append(f"search: {search}")
    
    context = f"User meminta daftar Wazuh agents dengan filter: {', '.join(filter_context) if filter_context else 'tanpa filter'}"
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="list_agents",
        user_context=context,
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="add_agent",
        user_context=f"User menambahkan agent baru dengan nama '{name}'" + (f" dan IP {ip}" if ip else ""),
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="delete_agents",
        user_context="User menghapus agents dari sistem",
        ctx=ctx
    )
    
    return formatted_response

@mcp.tool
async def get_agent_info(ctx: Context, agent_id: str) -> str:
    """Get detailed information about a specific agent."""
    result = await make_api_request("GET", f"/agents/{agent_id}", ctx)
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_agent_info",
        user_context=f"User meminta informasi detail agent ID {agent_id}",
        ctx=ctx
    )
    
    return formatted_response

@mcp.tool
async def get_agent_key(ctx: Context, agent_id: str) -> str:
    """Get the key for a specific agent (used for agent registration)."""
    result = await make_api_request("GET", f"/agents/{agent_id}/key", ctx)
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_agent_key",
        user_context=f"User meminta key untuk agent ID {agent_id}",
        ctx=ctx
    )
    
    return formatted_response

@mcp.tool
async def restart_agent(ctx: Context, agent_id: str) -> str:
    """Restart a specific Wazuh agent."""
    result = await make_api_request("PUT", f"/agents/{agent_id}/restart", ctx)
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="restart_agent",
        user_context=f"User restart agent ID {agent_id}",
        ctx=ctx
    )
    
    return formatted_response

@mcp.tool
async def restart_multiple_agents(ctx: Context, agent_ids: str) -> str:
    """
    Restart multiple Wazuh agents.
    
    Args:
        agent_ids: Comma-separated list of agent IDs to restart
    """
    params = {"agents_list": agent_ids.split(",")}
    result = await make_api_request("PUT", "/agents/restart", ctx, params=params)
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="restart_multiple_agents",
        user_context=f"User restart multiple agents: {agent_ids}",
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="upgrade_agents",
        user_context=f"User upgrade agents: {agent_ids}" + (f" ke versi {upgrade_version}" if upgrade_version else ""),
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_agent_config",
        user_context=f"User meminta konfigurasi agent {agent_id} untuk komponen {component}",
        ctx=ctx
    )
    
    return formatted_response

@mcp.tool
async def get_agent_stats(ctx: Context, agent_id: str) -> str:
    """Get daemon statistics from a specific agent."""
    result = await make_api_request("GET", f"/agents/{agent_id}/daemons/stats", ctx)
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_agent_stats",
        user_context=f"User meminta statistik daemon agent {agent_id}",
        ctx=ctx
    )
    
    return formatted_response

# =============================================================================
# MANAGER OPERATIONS
# =============================================================================

@mcp.tool
async def get_manager_status(ctx: Context) -> str:
    """Get the status of all Wazuh manager daemons."""
    result = await make_api_request("GET", "/manager/status", ctx)
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_manager_status",
        user_context=f"User called get_manager_status function",
        ctx=ctx
    )
    
    return formatted_response

@mcp.tool
async def get_manager_info(ctx: Context) -> str:
    """Get basic information about the Wazuh manager."""
    result = await make_api_request("GET", "/manager/info", ctx)
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_manager_info",
        user_context=f"User called get_manager_info function",
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_manager_configuration",
        user_context="User meminta konfigurasi Wazuh manager",
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_manager_daemon_stats",
        user_context="User meminta statistik daemon manager",
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_manager_stats",
        user_context="User meminta statistik manager",
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_manager_logs",
        user_context="User meminta log entries manager",
        ctx=ctx
    )
    
    return formatted_response

@mcp.tool
async def get_manager_logs_summary(ctx: Context) -> str:
    """Get a summary of manager logs by level and tag."""
    result = await make_api_request("GET", "/manager/logs/summary", ctx)
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_manager_logs_summary",
        user_context=f"User called get_manager_logs_summary function",
        ctx=ctx
    )
    
    return formatted_response

@mcp.tool
async def restart_manager(ctx: Context) -> str:
    """Restart the Wazuh manager."""
    result = await make_api_request("PUT", "/manager/restart", ctx)
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="restart_manager",
        user_context=f"User called restart_manager function",
        ctx=ctx
    )
    
    return formatted_response

@mcp.tool
async def validate_configuration(ctx: Context) -> str:
    """Validate the current Wazuh configuration."""
    result = await make_api_request("GET", "/manager/configuration/validation", ctx)
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="validate_configuration",
        user_context=f"User called validate_configuration function",
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="run_active_response",
        user_context=f"User menjalankan active response command '{command}' pada agents {agent_ids}",
        ctx=ctx
    )
    
    return formatted_response

# =============================================================================
# CLUSTER MANAGEMENT
# =============================================================================

@mcp.tool
async def get_cluster_status(ctx: Context) -> str:
    """Get the current cluster status."""
    result = await make_api_request("GET", "/cluster/status", ctx)
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_cluster_status",
        user_context=f"User called get_cluster_status function",
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_current_user",
        user_context=f"User called get_current_user function",
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_security_config",
        user_context=f"User called get_security_config function",
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_rule_groups",
        user_context=f"User called get_rule_groups function",
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_agents_overview",
        user_context=f"User called get_agents_overview function",
        ctx=ctx
    )
    
    return formatted_response

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
    raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="get_mitre_metadata",
        user_context=f"User called get_mitre_metadata function",
        ctx=ctx
    )
    
    return formatted_response

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
        print(f"Base URL: {wazuh_config.base_url}")
        print(f"Username: {wazuh_config.username}")
        print(f"SSL Verify: {wazuh_config.verify_ssl}")
        print(f"Timeout: {wazuh_config.timeout}s")
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
