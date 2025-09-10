#!/usr/bin/env python3
"""
Database utilities for Wazuh SQLite operations
"""

import sqlite3
import json
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class WazuhDatabaseQuery:
    """Query utilities for Wazuh SQLite database."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Get path relative to project root
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            db_path = str(project_root / "data" / "wazuh_archives.db")
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def get_recent_alerts(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alerts from last N hours."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                since_time = datetime.now() - timedelta(hours=hours)
                
                cursor.execute("""
                    SELECT id, timestamp, agent_id, agent_name, rule_id, rule_level,
                           rule_description, rule_groups, location, full_log
                    FROM wazuh_archives 
                    WHERE datetime(timestamp) >= datetime(?)
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (since_time.isoformat(), limit))
                
                columns = [description[0] for description in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []
    
    def get_alerts_by_rule_level(self, min_level: int = 5, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alerts by minimum rule level."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                since_time = datetime.now() - timedelta(hours=hours)
                
                cursor.execute("""
                    SELECT id, timestamp, agent_id, agent_name, rule_id, rule_level,
                           rule_description, rule_groups, location, full_log
                    FROM wazuh_archives 
                    WHERE rule_level >= ? 
                    AND datetime(timestamp) >= datetime(?)
                    ORDER BY rule_level DESC, timestamp DESC
                """, (min_level, since_time.isoformat()))
                
                columns = [description[0] for description in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting alerts by rule level: {e}")
            return []
    
    def get_agent_statistics(self) -> List[Dict[str, Any]]:
        """Get statistics per agent."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        agent_id,
                        agent_name,
                        COUNT(*) as alert_count,
                        MAX(rule_level) as max_rule_level,
                        MIN(timestamp) as first_alert,
                        MAX(timestamp) as last_alert
                    FROM wazuh_archives 
                    WHERE agent_id != ''
                    GROUP BY agent_id, agent_name
                    ORDER BY alert_count DESC
                """)
                
                columns = [description[0] for description in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting agent statistics: {e}")
            return []
    
    def get_rule_statistics(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top rules by frequency."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        rule_id,
                        rule_description,
                        rule_level,
                        COUNT(*) as trigger_count,
                        MAX(timestamp) as last_triggered
                    FROM wazuh_archives 
                    WHERE rule_id > 0
                    GROUP BY rule_id, rule_description, rule_level
                    ORDER BY trigger_count DESC
                    LIMIT ?
                """, (limit,))
                
                columns = [description[0] for description in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting rule statistics: {e}")
            return []
    
    def search_logs(self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search in full_log and rule_description fields."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, timestamp, agent_id, agent_name, rule_id, rule_level,
                           rule_description, location, full_log
                    FROM wazuh_archives 
                    WHERE full_log LIKE ? OR rule_description LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (f'%{search_term}%', f'%{search_term}%', limit))
                
                columns = [description[0] for description in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results
                
        except Exception as e:
            logger.error(f"Error searching logs: {e}")
            return []
    
    def export_to_csv(self, filename: str, hours: int = 24) -> bool:
        """Export recent data to CSV."""
        try:
            alerts = self.get_recent_alerts(hours=hours, limit=10000)
            
            if alerts:
                df = pd.DataFrame(alerts)
                df.to_csv(filename, index=False)
                logger.info(f"Exported {len(alerts)} records to {filename}")
                return True
            else:
                logger.warning("No data to export")
                return False
                
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False

def main():
    """CLI interface for database queries."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Query Wazuh SQLite Database")
    parser.add_argument("--recent", type=int, help="Get alerts from last N hours", default=24)
    parser.add_argument("--level", type=int, help="Minimum rule level", default=1)
    parser.add_argument("--search", type=str, help="Search term in logs")
    parser.add_argument("--agents", action="store_true", help="Show agent statistics")
    parser.add_argument("--rules", action="store_true", help="Show rule statistics")
    parser.add_argument("--export", type=str, help="Export to CSV file")
    # Default database path using project structure
    default_db_path = str(Path(__file__).parent.parent.parent / "data" / "wazuh_archives.db")
    parser.add_argument("--db", type=str, help="Database file path", default=default_db_path)
    
    args = parser.parse_args()
    
    query = WazuhDatabaseQuery(args.db)
    
    if args.agents:
        print("\n=== AGENT STATISTICS ===")
        agents = query.get_agent_statistics()
        for agent in agents:
            print(f"Agent {agent['agent_id']} ({agent['agent_name']}): {agent['alert_count']} alerts")
    
    if args.rules:
        print("\n=== TOP RULES ===")
        rules = query.get_rule_statistics()
        for rule in rules:
            print(f"Rule {rule['rule_id']}: {rule['trigger_count']} triggers - {rule['rule_description']}")
    
    if args.search:
        print(f"\n=== SEARCH RESULTS FOR '{args.search}' ===")
        results = query.search_logs(args.search)
        for result in results[:10]:  # Show first 10
            print(f"{result['timestamp']} - Rule {result['rule_id']}: {result['rule_description']}")
    
    if args.export:
        success = query.export_to_csv(args.export, args.recent)
        if success:
            print(f"Data exported to {args.export}")
    
    if not any([args.agents, args.rules, args.search, args.export]):
        # Default: show recent high-level alerts
        print(f"\n=== RECENT HIGH-LEVEL ALERTS (Level >= {args.level}) ===")
        alerts = query.get_alerts_by_rule_level(args.level, args.recent)
        for alert in alerts[:20]:  # Show first 20
            print(f"{alert['timestamp']} - Agent {alert['agent_id']} - Level {alert['rule_level']} - {alert['rule_description']}")

if __name__ == "__main__":
    main()
