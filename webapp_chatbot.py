#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LM Studio + FastMCP Webapp Chatbot
Integrates LM Studio with Wazuh FastMCP Server via web interface

Based on tool-use-example.py pattern but with FastMCP integration
"""

import asyncio
import json
import logging
import threading
import time
from typing import Dict, List, Any
from flask import Flask, render_template, request, jsonify, Response
import itertools
import sys

# LM Studio client
from openai import OpenAI

# FastMCP bridge
from mcp_tool_bridge import FastMCPBridge

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize LM Studio client (same as tool-use-example.py)
client = OpenAI(base_url="http://192.168.56.1:1234/v1", api_key="lm-studio")
MODEL = "qwen/qwen3-1.7b"

# Initialize FastMCP bridge
mcp_bridge = FastMCPBridge()

# Global chat state
chat_sessions = {}

class ChatSession:
    """Manage individual chat sessions"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages = [
            {
                "role": "system",
                "content": (
                    "You are a cybersecurity assistant with access to Wazuh SIEM tools. "
                    "You can help monitor security events, manage agents, analyze threats, "
                    "and provide security insights using the available Wazuh tools. "
                    "Always use the appropriate tools when users ask about security-related tasks."
                ),
            }
        ]
        self.mcp_tools = []
    
    async def initialize_tools(self):
        """Initialize MCP tools for this session"""
        try:
            # Connect to FastMCP server
            success = await mcp_bridge.connect_to_server()
            if not success:
                logger.error("Failed to connect to FastMCP server")
                return False
            
            # Load tools
            self.mcp_tools = await mcp_bridge.get_available_tools()
            logger.info(f"Loaded {len(self.mcp_tools)} MCP tools for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize tools for session {self.session_id}: {e}")
            return False
    
    def add_message(self, role: str, content: str):
        """Add message to chat history"""
        self.messages.append({"role": role, "content": content})
    
    def get_messages(self):
        """Get chat messages"""
        return self.messages

# Utility functions (similar to tool-use-example.py)
class Spinner:
    """Progress indicator for processing"""
    def __init__(self, message="Processing..."):
        self.spinner = itertools.cycle(["-", "/", "|", "\\"])
        self.busy = False
        self.delay = 0.1
        self.message = message
        self.thread = None

    def write(self, text):
        sys.stdout.write(text)
        sys.stdout.flush()

    def _spin(self):
        while self.busy:
            self.write(f"\r{self.message} {next(self.spinner)}")
            time.sleep(self.delay)
        self.write("\r\033[K")  # Clear the line

    def __enter__(self):
        self.busy = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.busy = False
        time.sleep(self.delay)
        if self.thread:
            self.thread.join()
        self.write("\r")

# Flask routes
@app.route('/')
def index():
    """Serve chat interface"""
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id', 'default')
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        # Get or create chat session
        if session_id not in chat_sessions:
            chat_sessions[session_id] = ChatSession(session_id)
            # Initialize tools asynchronously
            asyncio.run(chat_sessions[session_id].initialize_tools())
        
        session = chat_sessions[session_id]
        
        # Add user message
        session.add_message("user", user_message)
        
        # Process message with LM Studio
        response_data = process_chat_message(session)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500

def process_chat_message(session: ChatSession) -> Dict[str, Any]:
    """Process chat message with LM Studio and MCP tools (similar to tool-use-example.py)"""
    try:
        logger.info(f"Processing message for session {session.session_id}")
        
        # Get LM Studio response with tools
        response = client.chat.completions.create(
            model=MODEL,
            messages=session.get_messages(),
            tools=session.mcp_tools,
            tool_choice="auto"
        )
        
        assistant_message = response.choices[0].message
        tool_results = []
        
        if assistant_message.tool_calls:
            logger.info(f"Processing {len(assistant_message.tool_calls)} tool calls")
            
            # Add assistant message with tool calls
            session.messages.append({
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": tool_call.function,
                    }
                    for tool_call in assistant_message.tool_calls
                ],
            })
            
            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                try:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Executing tool: {tool_name}")
                    
                    # Execute MCP tool
                    result = asyncio.run(mcp_bridge.execute_tool(tool_name, arguments))
                    tool_results.append({
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "result": result
                    })
                    
                    # Add tool result to messages
                    session.messages.append({
                        "role": "tool",
                        "content": json.dumps(result),
                        "tool_call_id": tool_call.id,
                    })
                    
                except Exception as e:
                    logger.error(f"Tool execution error for {tool_call.function.name}: {e}")
                    error_result = {
                        "status": "error",
                        "message": str(e),
                        "tool_name": tool_call.function.name
                    }
                    tool_results.append({
                        "tool_name": tool_call.function.name,
                        "arguments": {},
                        "result": error_result
                    })
                    
                    session.messages.append({
                        "role": "tool",
                        "content": json.dumps(error_result),
                        "tool_call_id": tool_call.id,
                    })
            
            # Get final response after tool execution
            final_response = client.chat.completions.create(
                model=MODEL,
                messages=session.get_messages()
            )
            
            final_message = final_response.choices[0].message.content
            session.add_message("assistant", final_message)
            
            return {
                "response": final_message,
                "tool_calls": tool_results,
                "session_id": session.session_id
            }
        
        else:
            # No tool calls, regular response
            response_text = assistant_message.content
            session.add_message("assistant", response_text)
            
            return {
                "response": response_text,
                "tool_calls": [],
                "session_id": session.session_id
            }
    
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        return {
            "error": f"Failed to process message: {str(e)}",
            "session_id": session.session_id
        }

@app.route('/api/tools', methods=['GET'])
def get_tools():
    """Get available MCP tools"""
    try:
        # Initialize bridge if needed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if not mcp_bridge.client:
                loop.run_until_complete(mcp_bridge.connect_to_server())
            tools = loop.run_until_complete(mcp_bridge.get_available_tools())
        finally:
            loop.close()
        
        return jsonify({
            "tools": [
                {
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"]
                }
                for tool in tools
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting tools: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    try:
        # Check LM Studio connection
        lm_studio_status = "unknown"
        try:
            test_response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            lm_studio_status = "connected"
        except:
            lm_studio_status = "disconnected"
        
        # Check FastMCP connection
        mcp_status = "connected" if mcp_bridge.client else "disconnected"
        
        return jsonify({
            "lm_studio": lm_studio_status,
            "fastmcp": mcp_status,
            "model": MODEL
        })
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": str(e)}), 500

# Initialize on startup
async def initialize_app():
    """Initialize the application"""
    try:
        logger.info("Initializing FastMCP webapp...")
        
        # Connect to FastMCP server
        success = await mcp_bridge.connect_to_server()
        if success:
            logger.info("FastMCP bridge initialized successfully")
        else:
            logger.error("Failed to initialize FastMCP bridge")
        
    except Exception as e:
        logger.error(f"App initialization error: {e}")

if __name__ == "__main__":
    # Initialize
    try:
        asyncio.run(initialize_app())
    except:
        logger.warning("Could not initialize FastMCP bridge at startup")
    
    # Run Flask app
    print("=" * 60)
    print("🚀 LM Studio + FastMCP Webapp Chatbot")
    print("=" * 60)
    print(f"🤖 LM Studio Model: {MODEL}")
    print(f"🔧 FastMCP Server: wazuh_fastmcp_server.py")
    print(f"🌐 Web Interface: http://127.0.0.1:5000")
    print("=" * 60)
    print("\nMake sure:")
    print("1. LM Studio is running at http://192.168.56.1:1234")
    print("2. Model 'qwen/qwen3-1.7b' is loaded")
    print("3. wazuh_fastmcp_server.py is accessible")
    print("4. Wazuh API credentials are configured")
    print("\nStarting webapp...")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
