#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LM Studio + FastMCP Webapp Chatbot with Session History
Integrates LM Studio with Wazuh FastMCP Server via web interface

Based on tool-use-example.py pattern but with FastMCP integration
"""

import asyncio
import json
import logging
import threading
import time
import os
from typing import Dict, List, Any
from pathlib import Path
import sys
from flask import Flask, render_template, request, jsonify, Response
import itertools

# Add parent directories to path for importing project modules
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Import project components
from src.database import ChatDatabase
from src.api import FastMCPBridge

# LM Studio client
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment variables
LM_STUDIO_CONFIG = {
    'base_url': os.getenv('LM_STUDIO_BASE_URL', 'http://172.20.80.1:1234/v1'),
    'api_key': os.getenv('LM_STUDIO_API_KEY', 'lm-studio'),
    'model': os.getenv('LM_STUDIO_MODEL', 'qwen/qwen3-1.7b'),
    'timeout': None  # No timeout
}

FLASK_CONFIG = {
    'host': os.getenv('FLASK_HOST', '127.0.0.1'),
    'port': int(os.getenv('FLASK_PORT', '5000')),
    'debug': os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
}

# Initialize Flask app with correct template folder
template_dir = Path(__file__).parent / 'templates'
app = Flask(__name__, template_folder=str(template_dir))
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this')

# Global instances (singleton pattern to avoid re-initialization)
_db_instance = None
_mcp_bridge_instance = None
_client_instance = None

def get_database():
    """Get singleton database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = ChatDatabase()
    return _db_instance

def get_mcp_bridge():
    """Get singleton MCP bridge instance"""
    global _mcp_bridge_instance
    if _mcp_bridge_instance is None:
        _mcp_bridge_instance = FastMCPBridge()
    return _mcp_bridge_instance

def get_openai_client():
    """Get singleton OpenAI client instance"""
    global _client_instance
    if _client_instance is None:
        _client_instance = OpenAI(
            base_url=LM_STUDIO_CONFIG['base_url'], 
            api_key=LM_STUDIO_CONFIG['api_key'],
            timeout=None  # No timeout
        )
    return _client_instance

# Initialize singletons
db = get_database()
mcp_bridge = get_mcp_bridge()
client = get_openai_client()
MODEL = LM_STUDIO_CONFIG['model']

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
        self._tools_initialized = False  # Track if tools are already loaded
    
    async def initialize_tools(self):
        """Initialize MCP tools for this session"""
        # Return early if tools already initialized
        if self._tools_initialized and self.mcp_tools:
            logger.info(f"Tools already loaded for session {self.session_id} ({len(self.mcp_tools)} tools)")
            return True
            
        try:
            # Connect to FastMCP server
            success = await mcp_bridge.connect_to_server()
            if not success:
                logger.error("Failed to connect to FastMCP server")
                return False
            
            # Load tools
            self.mcp_tools = await mcp_bridge.get_available_tools()
            self._tools_initialized = True
            logger.info(f"Loaded {len(self.mcp_tools)} MCP tools for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize tools for session {self.session_id}: {e}")
            self._tools_initialized = False
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
    """Serve landing page"""
    return render_template('landing.html')

@app.route('/chat')
def chat_interface():
    """Serve chat interface with session history"""
    return render_template('chat_with_history.html')

@app.route('/dashboard')
def dashboard():
    """Serve dashboard interface"""
    return render_template('dashboard.html')

@app.route('/api/dashboard-data')
def dashboard_data():
    """API endpoint for dashboard data"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        # Database path
        db_path = os.path.join(project_root, 'data', 'wazuh_archives.db')
        
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Get total alerts count
        total_alerts = conn.execute('SELECT COUNT(*) as count FROM wazuh_archives').fetchone()['count']
        
        # Get alert distribution by rule level
        rule_levels = conn.execute('''
            SELECT rule_level, COUNT(*) as count 
            FROM wazuh_archives 
            GROUP BY rule_level 
            ORDER BY rule_level
        ''').fetchall()
        
        # Get top agents by alert count
        top_agents = conn.execute('''
            SELECT agent_name, COUNT(*) as count
            FROM wazuh_archives 
            WHERE agent_name IS NOT NULL 
            GROUP BY agent_name 
            ORDER BY count DESC 
            LIMIT 10
        ''').fetchall()
        
        # Get recent alerts
        recent_alerts = conn.execute('''
            SELECT id, timestamp, agent_name, rule_level, rule_description, location, rule_groups
            FROM wazuh_archives 
            ORDER BY id DESC 
            LIMIT 50
        ''').fetchall()
        
        # Get alerts by date for timeline chart
        alerts_by_date = conn.execute('''
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM wazuh_archives 
            WHERE timestamp >= date('now', '-7 days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        ''').fetchall()
        
        # Get rule group distribution
        rule_groups = conn.execute('''
            SELECT rule_groups, COUNT(*) as count
            FROM wazuh_archives 
            WHERE rule_groups IS NOT NULL AND rule_groups != ''
            GROUP BY rule_groups 
            ORDER BY count DESC 
            LIMIT 10
        ''').fetchall()
        
        conn.close()
        
        # Helper function for level descriptions
        def get_level_description(level):
            descriptions = {
                0: 'Informational events',
                1: 'Low priority alerts',
                2: 'Low priority alerts', 
                3: 'Medium priority alerts',
                4: 'Medium priority alerts',
                5: 'Medium priority alerts',
                6: 'High priority alerts',
                7: 'High priority alerts',
                8: 'Critical alerts',
                9: 'Critical alerts',
                10: 'Emergency alerts'
            }
            return descriptions.get(level, f'Level {level} alerts')
        
        # Format data for response
        response_data = {
            'stats': {
                'total_alerts': total_alerts,
                'active_agents': len([agent for agent in top_agents if agent['count'] > 0]),
                'critical_events': sum([rule['count'] for rule in rule_levels if rule['rule_level'] >= 8]),
                'security_score': 92  # Mock security score
            },
            'rule_levels': [
                {
                    'level': rule['rule_level'],
                    'count': rule['count'],
                    'description': get_level_description(rule['rule_level'])
                } for rule in rule_levels
            ],
            'agents': [
                {
                    'name': agent['agent_name'],
                    'count': agent['count'],
                    'status': 'active' if agent['count'] > 100 else 'inactive'
                } for agent in top_agents
            ],
            'alerts': [
                {
                    'id': alert['id'],
                    'timestamp': alert['timestamp'],
                    'agent_name': alert['agent_name'] or 'Unknown',
                    'rule_level': alert['rule_level'],
                    'rule_description': alert['rule_description'] or 'No description',
                    'location': alert['location'] or 'Unknown',
                    'rule_groups': alert['rule_groups'] or ''
                } for alert in recent_alerts
            ],
            'timeline': [
                {
                    'date': row['date'],
                    'count': row['count']
                } for row in alerts_by_date
            ],
            'rule_groups': [
                {
                    'name': group['rule_groups'],
                    'count': group['count']
                } for group in rule_groups
            ]
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id')
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        # Create new session if none provided
        if not session_id:
            session_id = db.create_session()
        
        # Check if session exists in database
        if not db.get_session(session_id):
            return jsonify({"error": "Session not found"}), 404
        
        # Get or create chat session object
        if session_id not in chat_sessions:
            chat_sessions[session_id] = ChatSession(session_id)
            # Initialize tools asynchronously
            asyncio.run(chat_sessions[session_id].initialize_tools())
            
            # Load existing messages from database
            existing_messages = db.get_messages(session_id)
            for msg in existing_messages:
                if msg['role'] != 'system':  # Skip system message as it's already added
                    chat_sessions[session_id].add_message(msg['role'], msg['content'])
        
        session = chat_sessions[session_id]
        
        # Add user message to session and database
        session.add_message("user", user_message)
        db.add_message(session_id, "user", user_message)
        
        # Process message with LM Studio
        response_data = process_chat_message(session, session_id)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500

def process_chat_message(session: ChatSession, session_id: str) -> Dict[str, Any]:
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
                        "name": tool_name,  # Changed from tool_name to name
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
                        "name": tool_call.function.name,  # Changed from tool_name to name
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
            
            # Save assistant message to database with tool usage
            db.add_message(session_id, "assistant", final_message, tool_results)
            
            return {
                "response": final_message,
                "tool_calls": tool_results,
                "thinking": None,  # Add thinking support
                "session_id": session.session_id
            }
        
        else:
            # No tool calls, regular response
            response_text = assistant_message.content
            session.add_message("assistant", response_text)
            
            # Save assistant message to database
            db.add_message(session_id, "assistant", response_text)
            
            return {
                "response": response_text,
                "tool_calls": [],
                "thinking": None,  # Add thinking support
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
    """Get system status - only check MCP"""
    try:
        # Check FastMCP connection only
        mcp_status = "connected" if mcp_bridge.client else "disconnected"
        
        return jsonify({
            "fastmcp": mcp_status,
            "model": MODEL
        })
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": str(e)}), 500

# Session management endpoints
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get all chat sessions"""
    try:
        sessions = db.get_sessions()
        return jsonify({"sessions": sessions})
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Create a new chat session"""
    try:
        data = request.json or {}
        title = data.get('title')
        session_id = db.create_session(title)
        return jsonify({"session_id": session_id, "message": "Session created successfully"})
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session_messages(session_id):
    """Get messages for a specific session"""
    try:
        session = db.get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        messages = db.get_messages(session_id)
        return jsonify({
            "session": session,
            "messages": messages
        })
    except Exception as e:
        logger.error(f"Error getting session messages: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions/<session_id>', methods=['PUT'])
def update_session(session_id):
    """Update session title"""
    try:
        data = request.json
        title = data.get('title')
        if not title:
            return jsonify({"error": "Title is required"}), 400
        
        db.update_session_title(session_id, title)
        return jsonify({"message": "Session updated successfully"})
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a chat session"""
    try:
        db.delete_session(session_id)
        return jsonify({"message": "Session deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions/search', methods=['GET'])
def search_sessions():
    """Search sessions by query"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({"sessions": []})
        
        sessions = db.search_sessions(query)
        return jsonify({"sessions": sessions})
    except Exception as e:
        logger.error(f"Error searching sessions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get database statistics"""
    try:
        stats = db.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
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
    # Only initialize on main process, not on Flask reloader
    import sys
    import os
    
    # Check if this is a Flask reloader process
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        # Initialize only once (main process)
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
    print(f"🌐 Web Interface: http://{FLASK_CONFIG['host']}:{FLASK_CONFIG['port']}")
    print("=" * 60)
    print("\nMake sure:")
    print(f"1. LM Studio is running at {LM_STUDIO_CONFIG['base_url']}")
    print(f"2. Model '{LM_STUDIO_CONFIG['model']}' is loaded")
    print("3. wazuh_fastmcp_server.py is accessible")
    print("4. Wazuh API credentials are configured")
    print("\nStarting webapp...")
    
    app.run(
        debug=True,  # Enable debug mode for development
        host=FLASK_CONFIG['host'], 
        port=FLASK_CONFIG['port'],
        use_reloader=False  # Disable reloader to prevent re-initialization
    )
