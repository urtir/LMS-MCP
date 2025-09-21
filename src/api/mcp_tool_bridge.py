#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastMCP Tool Bridge - Connects LM Studio with Wazuh FastMCP Server
Author: AI Assistant
Version: 1.0.0

This module creates a bridge between LM Studio (OpenAI format) and FastMCP Server
by converting MCP tools into OpenAI function definitions and handling execution.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from fastmcp import Client
import subprocess
import threading
import time
import os
import signal
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FastMCPBridge:
    """Bridge between LM Studio and FastMCP Server"""
    
    def __init__(self, mcp_server_script: str = None):
        if mcp_server_script is None:
            # Get default script path relative to current file
            current_dir = Path(__file__).parent
            mcp_server_script = str(current_dir / "wazuh_fastmcp_server.py")
        self.mcp_server_script = mcp_server_script
        self.client = None
        self.tools_cache = {}
        self.openai_tools = []
        self.server_process = None
        self._is_connected = False  # Track connection state
        
    async def start_mcp_server(self):
        """Start FastMCP server in background"""
        try:
            logger.info(f"Starting FastMCP server: {self.mcp_server_script}")
            
            # Start server process
            self.server_process = subprocess.Popen(
                ["python", self.mcp_server_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            # Wait a bit for server to start
            await asyncio.sleep(2)
            
            logger.info("FastMCP server started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start FastMCP server: {e}")
            return False
    
    async def connect_to_server(self):
        """Connect to FastMCP server using Client"""
        # Return early if already connected
        if self._is_connected and self.client is not None:
            logger.info("Already connected to FastMCP server, reusing connection")
            return True
            
        try:
            logger.info("Connecting to FastMCP server...")
            
            # If we have an old client, clean it up
            if self.client:
                try:
                    await self.client.__aexit__(None, None, None)
                except:
                    pass
            
            # Connect to server via stdio - proper format with context manager
            self.client = Client(self.mcp_server_script)
            # Don't call __aenter__ here, it will be called in execute_tool
            self._is_connected = True
            
            logger.info("FastMCP client created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to FastMCP server: {e}")
            self._is_connected = False
            return False
    
    async def load_tools(self):
        """Load tools from FastMCP server and convert to OpenAI format"""
        # Return cached tools if already loaded
        if self.openai_tools and self.tools_cache:
            logger.info(f"Using cached tools ({len(self.openai_tools)} tools)")
            return self.openai_tools
            
        try:
            logger.info("Loading tools from FastMCP server...")
            
            # Use fresh client connection with proper context manager
            client = Client(self.mcp_server_script)
            
            async with client:
                # Get tools from MCP server
                tools_list = await client.list_tools()
                logger.info(f"Found {len(tools_list)} tools from FastMCP server")
                
                # Convert MCP tools to OpenAI format
                self.openai_tools = []
                self.tools_cache = {}
                
                for tool in tools_list:
                    # Store tool info
                    self.tools_cache[tool.name] = tool
                    
                    # Convert to OpenAI function format
                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or f"Execute {tool.name} tool",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    }
                    
                    # Add schema if available
                    if hasattr(tool, 'inputSchema') and tool.inputSchema:
                        schema = tool.inputSchema
                        if 'properties' in schema:
                            openai_tool["function"]["parameters"]["properties"] = schema['properties']
                        if 'required' in schema:
                            openai_tool["function"]["parameters"]["required"] = schema['required']
                    
                    self.openai_tools.append(openai_tool)
                
                logger.info(f"Converted {len(self.openai_tools)} tools to OpenAI format")
                return self.openai_tools
            
        except Exception as e:
            logger.error(f"Failed to load tools: {e}")
            return []
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP tool and return result using proper context manager - NO TIMEOUT"""
        try:
            logger.info(f"Executing tool: {tool_name} with args: {arguments}")
            
            # Use fresh client connection with proper context manager
            client = Client(self.mcp_server_script)
            
            # Execute tool via FastMCP client with proper context manager - NO TIMEOUT
            async with client:
                logger.info(f"Connected to MCP server, executing tool: {tool_name}")
                # NO TIMEOUT - let it run as long as needed
                result = await client.call_tool(tool_name, arguments)
            
            logger.info(f"Tool {tool_name} executed successfully")
            
            # Return result in standard format
            return {
                "status": "success",
                "content": result.content[0].text if result.content else "Tool executed successfully",
                "tool_name": tool_name,
                "arguments": arguments
            }
            
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_name}: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "tool_name": tool_name,
                "arguments": arguments
            }
    
    async def get_available_tools(self) -> List[Dict]:
        """Get list of available tools in OpenAI format"""
        # Always reload tools to ensure fresh connection
        await self.load_tools()
        return self.openai_tools
    
    async def close(self):
        """Close connection and cleanup"""
        try:
            if self.client:
                await self.client.__aexit__(None, None, None)
                self.client = None
            
            if self.server_process:
                if os.name == 'nt':  # Windows
                    os.kill(self.server_process.pid, signal.SIGTERM)
                else:  # Unix-like
                    self.server_process.terminate()
                self.server_process.wait(timeout=5)
                self.server_process = None
            
            logger.info("FastMCP bridge closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing FastMCP bridge: {e}")

# Global bridge instance
mcp_bridge = FastMCPBridge()

# Functions for direct use (similar to tool-use-example.py pattern)
async def initialize_mcp_bridge():
    """Initialize the FastMCP bridge"""
    success = await mcp_bridge.connect_to_server()
    if success:
        await mcp_bridge.load_tools()
    return success

def get_mcp_tools():
    """Get MCP tools in OpenAI format (synchronous wrapper)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(mcp_bridge.get_available_tools())
    finally:
        loop.close()

def execute_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute MCP tool (synchronous wrapper for use in chat loop)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(mcp_bridge.execute_tool(tool_name, arguments))
    finally:
        loop.close()

async def cleanup_mcp_bridge():
    """Cleanup FastMCP bridge"""
    await mcp_bridge.close()

# Test function
async def test_bridge():
    """Test the FastMCP bridge"""
    try:
        logger.info("Testing FastMCP bridge...")
        
        # Initialize bridge
        success = await initialize_mcp_bridge()
        if not success:
            logger.error("Failed to initialize FastMCP bridge")
            return False
        
        # Get available tools
        tools = await mcp_bridge.get_available_tools()
        logger.info(f"Available tools: {[tool['function']['name'] for tool in tools]}")
        
        # Test a simple tool if available
        if tools:
            tool_name = tools[0]['function']['name']
            logger.info(f"Testing tool: {tool_name}")
            
            # Execute with minimal args
            result = await mcp_bridge.execute_tool(tool_name, {})
            logger.info(f"Test result: {result}")
        
        await cleanup_mcp_bridge()
        return True
        
    except Exception as e:
        logger.error(f"Bridge test failed: {e}")
        return False

if __name__ == "__main__":
    # Run test
    asyncio.run(test_bridge())
