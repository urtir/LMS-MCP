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
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
import sys
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, flash, session, make_response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
import itertools

# Add parent directories to path for importing project modules
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Add config directory to path
sys.path.append(str(project_root))
from config.config_manager import ConfigManager
config = ConfigManager()

# Import project components
from src.database import ChatDatabase
from src.api import FastMCPBridge
from src.models.user import User

# Import admin blueprint
from src.webapp.admin import admin_bp

# LM Studio client
from openai import OpenAI

# Configure logging with detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/webapp_chatbot.log')
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Configuration from JSON config - NO FALLBACKS!
LM_STUDIO_CONFIG = {
    'base_url': config.get('network.LM_STUDIO_BASE_URL'),
    'api_key': config.get('ai_model.LM_STUDIO_API_KEY'),
    'model': config.get('ai_model.LM_STUDIO_MODEL'),
    'timeout': None  # No timeout
}

FLASK_CONFIG = {
    'host': config.get('flask.FLASK_HOST'),
    'port': int(config.get('flask.FLASK_PORT')),
    'debug': config.get('flask.FLASK_DEBUG').lower() == 'true'
}

# Initialize Flask app with correct template folder
template_dir = Path(__file__).parent / 'templates'
app = Flask(__name__, template_folder=str(template_dir))
app.secret_key = config.get('security.FLASK_SECRET_KEY')

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Register blueprints
app.register_blueprint(admin_bp)

# Create main blueprint for organizing routes
from flask import Blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def dashboard():
    """Primary security dashboard"""
    return render_template('dashboard.html', user=current_user, current_year=datetime.utcnow().year)

# Register main blueprint  
app.register_blueprint(main_bp)

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    db = get_database()
    user_data = db.get_user_by_id(user_id)
    if user_data:
        return User(user_data)
    return None

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
logger.info("=== INITIALIZING WEBAPP COMPONENTS ===")
logger.info("Initializing database connection...")
db = get_database()
logger.info("Database initialized successfully")

logger.info("Initializing MCP bridge...")
mcp_bridge = get_mcp_bridge()
logger.info("MCP bridge initialized successfully")

logger.info("Initializing OpenAI client...")
client = get_openai_client()
logger.info(f"OpenAI client initialized: {LM_STUDIO_CONFIG['base_url']}")

MODEL = LM_STUDIO_CONFIG['model']
logger.info(f"Using model: {MODEL}")

logger.info("=== WEBAPP INITIALIZATION COMPLETE ===")

# Global chat state
chat_sessions = {}
logger.info("Chat sessions storage initialized")

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

# Flask Routes
@app.route('/login')
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return render_template('login.html')

@app.route('/register')
def register():
    """Register page"""
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return render_template('register.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    """Handle login API"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Authenticate user
        user_data = db.authenticate_user(username, password)
        if user_data:
            user = User(user_data)
            login_user(user, remember=True)
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': user.to_dict()
            })
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/register', methods=['POST'])
def api_register():
    """Handle registration API"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        
        # Validate input
        if not username or not email or not password:
            return jsonify({'error': 'Username, email, and password are required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        # Check if user already exists
        if db.user_exists(username=username):
            return jsonify({'error': 'Username already exists'}), 400
        
        if db.user_exists(email=email):
            return jsonify({'error': 'Email already exists'}), 400
        
        # Create user
        user_id = db.create_user(username, email, password, full_name)
        user_data = db.get_user_by_id(user_id)
        
        if user_data:
            user = User(user_data)
            login_user(user, remember=True)
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'user': user.to_dict()
            })
        else:
            return jsonify({'error': 'Registration failed'}), 500
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    """Handle logout API"""
    logout_user()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/chat')
@login_required
def chat():
    """Chat page - requires login"""
    response = make_response(render_template('chat_with_history.html', user=current_user))
    # Add anti-cache headers to prevent browser caching of old JavaScript
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/logout')
@login_required  
def logout():
    """Logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Existing routes (data endpoints, etc.)
@app.route('/')
def index():
    """Redirect root requests to dashboard or login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('login'))

@app.route('/test-tool')
def test_tool():
    """Test page for tool responses"""
    with open('test_tool_response.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/security-data')
@login_required
def security_data():
    """API endpoint for security data"""
    try:
        import sqlite3

        def to_int(value, default=0):
            if value is None:
                return default
            try:
                return int(value)
            except (TypeError, ValueError):
                try:
                    return int(float(value))
                except (TypeError, ValueError):
                    return default

        def to_bool(value):
            if isinstance(value, bool):
                return value
            if value is None:
                return False
            return str(value).strip().lower() in {"true", "1", "yes", "on"}

        def parse_recipients(raw):
            if not raw:
                return []
            return [recipient.strip() for recipient in str(raw).split(',') if recipient.strip()]

        # Database path
        database_dir = config.get('database.DATABASE_DIR')
        wazuh_db_name = config.get('database.WAZUH_DB_NAME')
        db_path = os.path.join(project_root, database_dir, wazuh_db_name)

        logger.info(f"Attempting to connect to database: {db_path}")

        if not os.path.exists(db_path):
            logger.error(f"Database not found at: {db_path}")
            return jsonify({'error': 'Database not found'}), 404

        has_rule_groups = False
        timeline_rows: List[Any] = []
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                logger.info("Successfully connected to database")

                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(wazuh_archives)")
                table_columns = {row[1] for row in cursor.fetchall()}
                has_rule_groups = 'rule_groups' in table_columns

                # Get total alerts count
                total_alerts = conn.execute('SELECT COUNT(*) as count FROM wazuh_archives').fetchone()['count']

                # Get alert distribution by rule level
                rule_levels = conn.execute('''
                    SELECT CAST(rule_level AS INTEGER) AS level, COUNT(*) as count
                    FROM wazuh_archives 
                    WHERE rule_level IS NOT NULL AND TRIM(rule_level) != ''
                    GROUP BY CAST(rule_level AS INTEGER)
                    ORDER BY CAST(rule_level AS INTEGER)
                ''').fetchall()

                # Get top agents with additional metrics
                top_agents = conn.execute('''
                    SELECT agent_id,
                           agent_name,
                           COUNT(*) as count,
                           MAX(rule_level) as max_rule_level,
                           MAX(timestamp) as last_seen
                    FROM wazuh_archives 
                    WHERE agent_name IS NOT NULL AND agent_name != ''
                    GROUP BY agent_id, agent_name 
                    ORDER BY count DESC 
                    LIMIT 10
                ''').fetchall()

                # Get recent alerts
                recent_columns = "id, timestamp, agent_name, rule_level, rule_description, location"
                if has_rule_groups:
                    recent_columns += ", rule_groups"
                recent_alerts = conn.execute(f'''
                    SELECT {recent_columns}
                    FROM wazuh_archives 
                    ORDER BY id DESC 
                    LIMIT 50
                ''').fetchall()

                # Fetch raw timestamps for timeline chart aggregation
                timeline_rows = conn.execute('''
                    SELECT timestamp
                    FROM wazuh_archives 
                    WHERE timestamp IS NOT NULL AND TRIM(timestamp) != ''
                    ORDER BY timestamp DESC
                    LIMIT 20000
                ''').fetchall()

                # Get rule group distribution
                rule_groups = []
                if has_rule_groups:
                    rule_groups = conn.execute('''
                        SELECT rule_groups, COUNT(*) as count
                        FROM wazuh_archives 
                        WHERE rule_groups IS NOT NULL AND rule_groups != ''
                        GROUP BY rule_groups 
                        ORDER BY count DESC 
                        LIMIT 10
                    ''').fetchall()

        except Exception as query_error:
            logger.error(f"Database query error: {query_error}")
            return jsonify({'error': f'Database query failed: {str(query_error)}'}), 500

        logger.info("Database queries completed successfully")

        # Thresholds & configuration values
        agent_threshold = to_int(config.get('security_thresholds.AGENT_ACTIVE_THRESHOLD'), 100)
        high_level_threshold = to_int(config.get('security_thresholds.HIGH_RULE_LEVEL'), 7)
        critical_level_threshold = to_int(config.get('security_thresholds.CRITICAL_RULE_LEVEL'), 10)

        # Build severity summary and derived counts
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

        severity_counts = {}
        critical_events = 0
        high_events = 0
        for rule in rule_levels:
            level = to_int(rule['level'])
            count = to_int(rule['count'])
            severity_counts[level] = severity_counts.get(level, 0) + count
            if level >= critical_level_threshold:
                critical_events += count
            if level >= high_level_threshold:
                high_events += count

        severity_breakdown = []
        for level in range(0, 18):
            count = severity_counts.get(level, 0)
            severity_breakdown.append({
                'level': level,
                'count': count,
                'description': get_level_description(level)
            })

        # Prepare timeline data and compute velocity
        def parse_timestamp(raw_ts: str) -> Optional[datetime]:
            if not raw_ts:
                return None
            value = raw_ts.strip()
            formats = (
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S.%f%z"
            )
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            if value.endswith('+0000'):
                try:
                    return datetime.fromisoformat(value[:-5] + '+00:00')
                except ValueError:
                    pass
            return None

        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc - timedelta(days=14)
        timeline_counter: Dict[str, int] = {}

        for row in timeline_rows:
            if isinstance(row, sqlite3.Row):
                raw_ts = row['timestamp']
            elif isinstance(row, (tuple, list)):
                raw_ts = row[0]
            else:
                raw_ts = row
            parsed = parse_timestamp(raw_ts)
            if not parsed:
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed < cutoff:
                continue
            date_key = parsed.astimezone(timezone.utc).date().isoformat()
            timeline_counter[date_key] = timeline_counter.get(date_key, 0) + 1

        timeline_sorted = []
        for offset in range(13, -1, -1):
            current_date = (now_utc - timedelta(days=offset)).date().isoformat()
            timeline_sorted.append({
                'date': current_date,
                'count': timeline_counter.get(current_date, 0)
            })
        alert_velocity = 0
        alert_trend_percent = 0.0
        if len(timeline_sorted) >= 2:
            latest = timeline_sorted[-1]['count']
            previous = timeline_sorted[-2]['count']
            alert_velocity = latest - previous
            if previous > 0:
                alert_trend_percent = round(((latest - previous) / previous) * 100, 1)

        # Calculate security score with weighted factors
        total_alerts_value = to_int(total_alerts)
        denominator = total_alerts_value if total_alerts_value > 0 else 1
        critical_ratio = critical_events / denominator
        high_ratio = high_events / denominator
        score = 100.0
        score -= min(55.0, critical_ratio * 120.0)
        score -= min(30.0, high_ratio * 80.0)
        score -= min(15.0, max(alert_velocity, 0))
        security_score = max(0, min(100, round(score)))

        # Build agent summary
        agents_summary = []
        active_agents = 0
        for agent in top_agents:
            count = to_int(agent['count'])
            is_active = count >= agent_threshold
            if is_active:
                active_agents += 1
            agents_summary.append({
                'id': agent['agent_id'],
                'name': agent['agent_name'],
                'count': count,
                'status': 'active' if is_active else 'monitoring',
                'max_rule_level': to_int(agent['max_rule_level']),
                'last_seen': agent['last_seen']
            })

        # Recent alerts listing
        alerts_summary = []
        for alert in recent_alerts:
            raw_groups = alert['rule_groups'] if has_rule_groups and 'rule_groups' in alert.keys() else None
            rule_group_values = [value.strip() for value in (raw_groups or '').split(',') if value and value.strip()]
            alerts_summary.append({
                'id': alert['id'],
                'timestamp': alert['timestamp'],
                'agent_name': alert['agent_name'] or 'Unknown',
                'rule_level': to_int(alert['rule_level'], default=None),
                'rule_level_raw': alert['rule_level'],
                'rule_description': alert['rule_description'] or 'No description',
                'location': alert['location'] or 'Unknown',
                'rule_groups': rule_group_values
            })

        # Rule groups summary
        rule_group_summary = []
        if has_rule_groups:
            for group in rule_groups:
                names = [value.strip() for value in str(group['rule_groups']).split(',') if value.strip()]
                rule_group_summary.append({
                    'raw': group['rule_groups'],
                    'labels': names,
                    'count': to_int(group['count'])
                })

        # Additional supporting data
        chat_stats = db.get_stats()
        services_config = config.get_category('services') or {}
        reports_config = config.get_category('telegram_reports') or {}
        from src.webapp.admin import SERVICE_STATUS
        running_status = SERVICE_STATUS.copy()

        services_status = {
            'fastmcp_connected': bool(mcp_bridge.client),
            'lm_studio_connected': client is not None,
            'telegram_bot_enabled': to_bool(services_config.get('TELEGRAM_BOT_ENABLED')),
            'telegram_alert_interval': to_int(services_config.get('ALERT_CHECK_INTERVAL'), 0),
            'wazuh_realtime_enabled': to_bool(services_config.get('WAZUH_REALTIME_ENABLED')),
            'wazuh_realtime_interval': to_int(services_config.get('REALTIME_FETCH_INTERVAL'), 0),
            'telegram_bot_running': bool(running_status.get('telegram_bot')),
            'wazuh_realtime_running': bool(running_status.get('wazuh_realtime'))
        }

        report_schedule = []
        for key in ['DAILY', 'THREE_DAILY', 'WEEKLY', 'MONTHLY']:
            prefix = f'{key}_REPORT'
            enabled_key = f'{prefix}_ENABLED'
            time_key = f'{prefix}_TIME'
            recipients_key = f'{prefix}_RECIPIENTS'
            report_schedule.append({
                'period': key.lower(),
                'enabled': to_bool(reports_config.get(enabled_key)),
                'time': reports_config.get(time_key),
                'recipients': parse_recipients(reports_config.get(recipients_key))
            })

        response_data = {
            'stats': {
                'total_alerts': total_alerts_value,
                'active_agents': active_agents,
                'critical_events': critical_events,
                'security_score': security_score,
                'alert_velocity': alert_velocity,
                'alert_trend_percent': alert_trend_percent
            },
            'rule_levels': severity_breakdown,
            'agents': agents_summary,
            'alerts': alerts_summary,
            'timeline': timeline_sorted,
            'rule_groups': rule_group_summary,
            'chat': chat_stats,
            'services': services_status,
            'reports': report_schedule
        }

        logger.info(f"Dashboard severity payload: {severity_breakdown}")
        logger.info(f"Dashboard timeline payload (len={len(timeline_sorted)}): {timeline_sorted[:10]}")
        logger.info(f"Dashboard alerts sample: {alerts_summary[:5]}")

        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error fetching security data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """Handle chat messages"""
    try:
        logger.info("=== CHAT REQUEST RECEIVED ===")
        logger.info(f"User: {current_user.username} (ID: {current_user.id})")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request data: {request.data}")
        
        data = request.json
        logger.info(f"Parsed JSON data: {data}")
        
        user_message = data.get('message', '')
        session_id = data.get('session_id')
        
        logger.info(f"User message: '{user_message}'")
        logger.info(f"Session ID: {session_id}")
        
        if not user_message:
            logger.warning("No message provided in request")
            return jsonify({"error": "No message provided"}), 400
        
        # Create new session if none provided
        if not session_id:
            logger.info("Creating new session...")
            session_id = db.create_session(current_user.id)
            logger.info(f"Created new session: {session_id}")
        
        # Check if session exists and belongs to current user
        logger.info(f"Checking session {session_id} for user {current_user.id}")
        session_data = db.get_session(session_id, current_user.id)
        if not session_data:
            logger.error(f"Session {session_id} not found or access denied for user {current_user.id}")
            return jsonify({"error": "Session not found or access denied"}), 404
        
        logger.info("Session validated successfully")
        
        # Get or create chat session object
        if session_id not in chat_sessions:
            logger.info(f"Creating new chat session object for {session_id}")
            chat_sessions[session_id] = ChatSession(session_id)
            # Initialize tools asynchronously
            logger.info("Initializing MCP tools...")
            asyncio.run(chat_sessions[session_id].initialize_tools())
            logger.info("MCP tools initialized successfully")
            
            # Load existing messages from database
            logger.info("Loading existing messages from database...")
            existing_messages = db.get_messages(session_id)
            logger.info(f"Found {len(existing_messages)} existing messages")
            for msg in existing_messages:
                if msg['role'] != 'system':  # Skip system message as it's already added
                    chat_sessions[session_id].add_message(msg['role'], msg['content'])
        
        session = chat_sessions[session_id]
        logger.info(f"Using session object with {len(session.get_messages())} messages")
        
        # Add user message to session and database
        logger.info("Adding user message to session and database...")
        session.add_message("user", user_message)
        db.add_message(session_id, "user", user_message)
        logger.info("User message added successfully")
        
        # Process message with LM Studio
        logger.info("Processing message with LM Studio...")
        response_data = process_chat_message(session, session_id)
        logger.info(f"Chat processing complete. Response: {response_data}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"CHAT API ERROR: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

def process_chat_message(session: ChatSession, session_id: str) -> Dict[str, Any]:
    """Process chat message with LM Studio and MCP tools (similar to tool-use-example.py)"""
    try:
        logger.info(f"=== PROCESSING MESSAGE FOR SESSION {session.session_id} ===")
        logger.info(f"Session has {len(session.get_messages())} messages")
        logger.info(f"Available MCP tools: {len(session.mcp_tools) if session.mcp_tools else 0}")
        
        # Get LM Studio response with tools
        logger.info(f"Sending request to LM Studio: {LM_STUDIO_CONFIG['base_url']}")
        logger.info(f"Model: {MODEL}")
        
        messages = session.get_messages()
        logger.debug(f"Messages to send: {messages}")
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=session.mcp_tools,
            tool_choice="auto"
        )
        
        logger.info("LM Studio response received successfully")
        
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
            for i, tool_call in enumerate(assistant_message.tool_calls):
                try:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Executing tool {i+1}/{len(assistant_message.tool_calls)}: {tool_name}")
                    logger.debug(f"Tool arguments: {arguments}")
                    
                    # Execute MCP tool
                    result = asyncio.run(mcp_bridge.execute_tool(tool_name, arguments))
                    logger.info(f"Tool {tool_name} executed successfully")
                    logger.debug(f"Tool result: {result}")
                    
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
                    logger.error(f"Tool execution error for {tool_call.function.name}: {e}", exc_info=True)
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
            logger.info("Getting final response from LM Studio after tool execution...")
            
            # ALWAYS get LLM interpretation/formatting of tool results
            # This ensures natural language response instead of raw tool output
            logger.info("Getting LLM formatted response based on tool results")
            final_response = client.chat.completions.create(
                model=MODEL,
                messages=session.get_messages()
            )
            full_response = final_response.choices[0].message.content
            
            # SEPARATE THINKING FROM FINAL RESPONSE
            thinking = None
            final_message = full_response
            
            # Extract thinking tags
            import re
            thinking_match = re.search(r'<think>(.*?)</think>', full_response, re.DOTALL | re.IGNORECASE)
            if thinking_match:
                thinking = thinking_match.group(1).strip()
                # Remove thinking tags from final response
                final_message = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL | re.IGNORECASE).strip()
            
            logger.info(f"Final message from LLM: {final_message[:200] if final_message else 'None'}...")
            logger.info(f"Thinking extracted: {len(thinking) if thinking else 0} characters")
            
            logger.info("Final response processed")
            logger.debug(f"Final message length: {len(final_message) if final_message else 0}")
            
            # Ensure final_message is valid
            if not final_message or final_message.strip() == "":
                logger.warning("Final message is empty or None - using fallback")
                final_message = "Tool executed successfully but no response content available."
            
            session.add_message("assistant", final_message)
            
            # Save assistant message to database with tool usage
            logger.info("Saving assistant message to database...")
            db.add_message(session_id, "assistant", final_message, tool_results)
            logger.info("Message saved to database successfully")
            
            # Prepare response data
            response_data = {
                "response": final_message,
                "tool_calls": tool_results,
                "thinking": thinking,  # NOW PROPERLY SEPARATED!
                "session_id": session.session_id
            }
            
            logger.info(f"Returning response data - response length: {len(final_message) if final_message else 0}")
            logger.info(f"Tool calls count: {len(tool_results)}")
            logger.debug(f"Response data: {response_data}")
            
            return response_data
        
        else:
            # No tool calls, regular response
            logger.info("No tool calls - processing regular response")
            full_response = assistant_message.content
            logger.debug(f"Full response text: {full_response}")
            
            # SEPARATE THINKING FROM FINAL RESPONSE (even for non-tool responses)
            thinking = None
            final_message = full_response
            
            # Extract thinking tags
            import re
            thinking_match = re.search(r'<think>(.*?)</think>', full_response, re.DOTALL | re.IGNORECASE)
            if thinking_match:
                thinking = thinking_match.group(1).strip()
                # Remove thinking tags from final response
                final_message = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL | re.IGNORECASE).strip()
            
            logger.info(f"Thinking extracted: {len(thinking) if thinking else 0} characters")
            logger.info(f"Final message: {len(final_message) if final_message else 0} characters")
            
            session.add_message("assistant", final_message)
            
            # Save assistant message to database
            logger.info("Saving regular response to database...")
            db.add_message(session_id, "assistant", final_message)
            logger.info("Response saved to database successfully")
            
            return {
                "response": final_message,
                "tool_calls": [],
                "thinking": thinking,  # NOW PROPERLY SEPARATED!
                "session_id": session.session_id
            }
    
    except Exception as e:
        logger.error(f"ERROR PROCESSING CHAT MESSAGE: {e}", exc_info=True)
        return {
            "error": f"Failed to process message: {str(e)}",
            "session_id": session.session_id
        }

@app.route('/api/tools', methods=['GET'])
@login_required
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
    """Get system status - accessible from landing page"""
    try:
        # Check FastMCP connection only
        mcp_status = "connected" if mcp_bridge.client else "disconnected"
        lm_status = "connected" if client is not None else "disconnected"

        return jsonify({
            "fastmcp": mcp_status,
            "lm_studio": lm_status,
            "model": MODEL
        })
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": str(e)}), 500

# Session management endpoints
@app.route('/api/sessions', methods=['GET'])
@login_required
def get_sessions():
    """Get all chat sessions for current user"""
    try:
        sessions = db.get_sessions(current_user.id)
        return jsonify({"sessions": sessions})
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions', methods=['POST'])
@login_required
def create_session():
    """Create a new chat session for current user"""
    try:
        data = request.json or {}
        title = data.get('title')
        session_id = db.create_session(current_user.id, title)
        return jsonify({"session_id": session_id, "message": "Session created successfully"})
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions/<session_id>', methods=['GET'])
@login_required
def get_session_messages(session_id):
    """Get messages for a specific session"""
    try:
        session = db.get_session(session_id, current_user.id)
        if not session:
            return jsonify({"error": "Session not found or access denied"}), 404
        
        messages = db.get_messages(session_id)
        return jsonify({
            "session": session,
            "messages": messages
        })
    except Exception as e:
        logger.error(f"Error getting session messages: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions/<session_id>', methods=['PUT'])
@login_required
def update_session(session_id):
    """Update session title"""
    try:
        # Check if session belongs to current user
        session = db.get_session(session_id, current_user.id)
        if not session:
            return jsonify({"error": "Session not found or access denied"}), 404
        
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
@login_required
def delete_session(session_id):
    """Delete a chat session"""
    try:
        # Check if session belongs to current user
        session = db.get_session(session_id, current_user.id)
        if not session:
            return jsonify({"error": "Session not found or access denied"}), 404
        
        db.delete_session(session_id)
        return jsonify({"message": "Session deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions/search', methods=['GET'])
@login_required
def search_sessions():
    """Search sessions by query for current user"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({"sessions": []})
        
        # Note: search_sessions method needs to be updated to filter by user_id
        sessions = db.search_sessions(query)
        # Filter by user_id in Python for now
        user_sessions = [s for s in sessions if db.get_session(s['id'], current_user.id)]
        return jsonify({"sessions": user_sessions})
    except Exception as e:
        logger.error(f"Error searching sessions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get basic database statistics - accessible from landing page"""
    try:
        # Get basic stats (no user-specific data)
        stats = db.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/user-stats', methods=['GET'])
@login_required
def get_user_stats():
    """Get user-specific database statistics"""
    try:
        # Get user-specific stats for logged-in users
        stats = db.get_stats()
        # Note: You might want to add user-specific stats methods later
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
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
        debug=config.get('flask.FLASK_DEBUG').lower() == 'true',  # Use JSON config for debug
        host=FLASK_CONFIG['host'], 
        port=FLASK_CONFIG['port'],
        use_reloader=False,  # Disable reloader to prevent re-initialization
        threaded=True  # Enable threading for concurrent requests
    )
