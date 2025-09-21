from flask import Flask, render_template, jsonify, request
import sqlite3
import json
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path

# Add config directory to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
from config.config_manager import ConfigManager
config = ConfigManager()

app = Flask(__name__)

# Database path - use JSON configuration
DATABASE_DIR = config.get('database.DATABASE_DIR')
WAZUH_DB_NAME = config.get('database.WAZUH_DB_NAME')
DB_PATH = os.path.join(DATABASE_DIR, WAZUH_DB_NAME)

# Ensure absolute path
if not os.path.isabs(DB_PATH):
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), DB_PATH)

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def landing():
    """Landing page"""
    return render_template('landing.html')

@app.route('/chat')
def chat():
    """Chat page"""
    return render_template('chat_with_history.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/dashboard-data')
def dashboard_data():
    """API endpoint for dashboard data"""
    try:
        conn = get_db_connection()
        
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
        print(f"Error fetching dashboard data: {e}")
        return jsonify({'error': str(e)}), 500

def get_level_description(level):
    """Get description for rule level"""
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

@app.route('/api/alerts')
def get_alerts():
    """Get paginated alerts"""
    try:
        page = int(request.args.get('page', 0))
        size = int(request.args.get('size', 10))
        level_filter = request.args.get('level')
        agent_filter = request.args.get('agent')
        
        conn = get_db_connection()
        
        # Build query with filters
        query = 'SELECT * FROM wazuh_archives WHERE 1=1'
        params = []
        
        if level_filter:
            query += ' AND rule_level = ?'
            params.append(level_filter)
            
        if agent_filter:
            query += ' AND agent_name = ?'
            params.append(agent_filter)
        
        # Get total count
        count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
        total = conn.execute(count_query, params).fetchone()[0]
        
        # Add pagination
        query += ' ORDER BY id DESC LIMIT ? OFFSET ?'
        params.extend([size, page * size])
        
        alerts = conn.execute(query, params).fetchall()
        conn.close()
        
        return jsonify({
            'alerts': [dict(alert) for alert in alerts],
            'total': total,
            'page': page,
            'size': size
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agents')
def get_agents():
    """Get agent information"""
    try:
        conn = get_db_connection()
        
        agents = conn.execute('''
            SELECT 
                agent_name,
                COUNT(*) as alert_count,
                MAX(timestamp) as last_seen,
                MIN(timestamp) as first_seen
            FROM wazuh_archives 
            WHERE agent_name IS NOT NULL 
            GROUP BY agent_name 
            ORDER BY alert_count DESC
        ''').fetchall()
        
        conn.close()
        
        return jsonify({
            'agents': [
                {
                    'name': agent['agent_name'],
                    'alert_count': agent['alert_count'],
                    'last_seen': agent['last_seen'],
                    'first_seen': agent['first_seen'],
                    'status': 'active' if agent['alert_count'] > 100 else 'inactive'
                } for agent in agents
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get dashboard statistics"""
    try:
        conn = get_db_connection()
        
        # Get various statistics
        stats = {}
        
        # Total alerts
        stats['total_alerts'] = conn.execute('SELECT COUNT(*) FROM wazuh_archives').fetchone()[0]
        
        # Unique agents
        stats['total_agents'] = conn.execute('SELECT COUNT(DISTINCT agent_name) FROM wazuh_archives WHERE agent_name IS NOT NULL').fetchone()[0]
        
        # Critical alerts (level >= 8)
        stats['critical_alerts'] = conn.execute('SELECT COUNT(*) FROM wazuh_archives WHERE rule_level >= 8').fetchone()[0]
        
        # High alerts (level >= 6)
        stats['high_alerts'] = conn.execute('SELECT COUNT(*) FROM wazuh_archives WHERE rule_level >= 6').fetchone()[0]
        
        # Alerts in last 24 hours
        stats['alerts_24h'] = conn.execute('''
            SELECT COUNT(*) FROM wazuh_archives 
            WHERE datetime(timestamp) >= datetime('now', '-1 day')
        ''').fetchone()[0]
        
        # Alerts in last 7 days
        stats['alerts_7d'] = conn.execute('''
            SELECT COUNT(*) FROM wazuh_archives 
            WHERE datetime(timestamp) >= datetime('now', '-7 days')
        ''').fetchone()[0]
        
        conn.close()
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print(f"Database path: {DB_PATH}")
    print(f"Database exists: {os.path.exists(DB_PATH)}")
    
    # Load configuration from environment variables
    debug_mode = config.get('flask.DASHBOARD_DEBUG').lower() == 'true'
    host = config.get('flask.DASHBOARD_HOST')
    port = int(config.get('flask.DASHBOARD_PORT'))
    
    print(f"Starting dashboard on {host}:{port} (debug={debug_mode})")
    app.run(debug=debug_mode, host=host, port=port)
