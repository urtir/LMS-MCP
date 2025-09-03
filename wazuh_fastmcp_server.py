#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wazuh FastMCP Server - Complete Wazuh API Integration
Author: AI Assistant
Version: 1.0.0
Description: FastMCP server providing comprehensive Wazuh API tools for LM Studio integration

This server implements all major Wazuh API endpoints as MCP tools.
"""

import asyncio
import json
import logging
import os
from typing import Optional, Dict, List, Any, Union
from datetime import datetime
import base64
import ssl

import httpx
from fastmcp import FastMCP, Context
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Wazuh API Server")

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

@mcp.resource("wazuh://config")
def get_wazuh_config():
    """Get current Wazuh server configuration."""
    return {
        "base_url": config.base_url,
        "username": config.username,
        "verify_ssl": config.verify_ssl,
        "timeout": config.timeout,
        "authenticated": config._token is not None
    }

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
