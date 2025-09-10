#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security Report Generator for Telegram Bot
Integrates with existing Wazuh database and LLM system
"""

import asyncio
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import sys
import pandas as pd
from openai import OpenAI

# Add parent directories to path for importing project modules
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Import project components
from src.database import ChatDatabase
from src.api import FastMCPBridge

# Import internal telegram config
from ..utils.telegram_config import TelegramBotConfig

logger = logging.getLogger(__name__)

class SecurityReportGenerator:
    """Generate security reports using existing Wazuh database and LLM integration"""
    
    def __init__(self):
        self.config = TelegramBotConfig()
        self.wazuh_db_path = self.config.DATABASE_CONFIG['wazuh_db']
        self.chat_db = ChatDatabase()
        self.mcp_bridge = FastMCPBridge()
        
        # Initialize LM Studio client (same as existing webapp)
        self.llm_client = OpenAI(
            base_url=self.config.LM_STUDIO_CONFIG['base_url'],
            api_key=self.config.LM_STUDIO_CONFIG['api_key'],
            timeout=None  # No timeout
        )
        self.model = self.config.LM_STUDIO_CONFIG['model']
        
    async def initialize(self):
        """Initialize MCP bridge connection"""
        try:
            success = await self.mcp_bridge.connect_to_server()
            if success:
                logger.info("✅ MCP Bridge initialized for report generator")
                return True
            else:
                logger.error("❌ Failed to initialize MCP Bridge")
                return False
        except Exception as e:
            logger.error(f"Error initializing report generator: {e}")
            return False
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """Get database connection with proper configuration"""
        conn = sqlite3.connect(self.wazuh_db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def _get_time_range_sql(self, start_time: datetime, end_time: datetime) -> Tuple[str, List]:
        """Generate SQL time range filter"""
        return "timestamp BETWEEN ? AND ?", [
            start_time.strftime('%Y-%m-%d %H:%M:%S'),
            end_time.strftime('%Y-%m-%d %H:%M:%S')
        ]
    
    async def get_security_events(self, start_time: datetime, end_time: datetime, 
                                 report_type: str = 'daily') -> List[Dict[str, Any]]:
        """Get security events from Wazuh database for specified time range"""
        try:
            config = TelegramBotConfig.REPORT_TYPES[report_type]
            priority_levels = config['priority_levels']
            max_events = config['max_events']
            
            with self._get_db_connection() as conn:
                # Build query for priority events
                time_filter, time_params = self._get_time_range_sql(start_time, end_time)
                level_placeholders = ','.join(['?'] * len(priority_levels))
                
                query = f"""
                    SELECT 
                        id, timestamp, agent_id, agent_name, manager,
                        rule_id, rule_level, rule_description, rule_groups,
                        location, decoder_name, data, full_log,
                        json_data, created_at
                    FROM wazuh_archives 
                    WHERE {time_filter}
                    AND rule_level IN ({level_placeholders})
                    ORDER BY rule_level DESC, timestamp DESC
                    LIMIT ?
                """
                
                params = time_params + priority_levels + [max_events]
                cursor = conn.execute(query, params)
                
                events = []
                for row in cursor.fetchall():
                    event = dict(row)
                    # Parse JSON data if available
                    if event['json_data']:
                        try:
                            event['parsed_json'] = json.loads(event['json_data'])
                        except json.JSONDecodeError:
                            event['parsed_json'] = {}
                    events.append(event)
                
                logger.info(f"Retrieved {len(events)} security events for {report_type} report")
                return events
                
        except Exception as e:
            logger.error(f"Error getting security events: {e}")
            return []
    
    async def get_agent_status_summary(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get agent status summary from database"""
        try:
            with self._get_db_connection() as conn:
                time_filter, time_params = self._get_time_range_sql(start_time, end_time)
                
                # Get agent activity summary
                query = f"""
                    SELECT 
                        agent_name,
                        agent_id,
                        COUNT(*) as event_count,
                        MIN(timestamp) as first_event,
                        MAX(timestamp) as last_event,
                        AVG(rule_level) as avg_severity,
                        MAX(rule_level) as max_severity
                    FROM wazuh_archives 
                    WHERE {time_filter}
                    AND agent_name IS NOT NULL
                    GROUP BY agent_id, agent_name
                    ORDER BY event_count DESC
                """
                
                cursor = conn.execute(query, time_params)
                agents = []
                
                for row in cursor.fetchall():
                    agent = dict(row)
                    agent['status'] = 'active' if agent['event_count'] > 0 else 'inactive'
                    agents.append(agent)
                
                return {
                    'total_agents': len(agents),
                    'active_agents': len([a for a in agents if a['status'] == 'active']),
                    'agents_detail': agents[:10]  # Top 10 most active
                }
                
        except Exception as e:
            logger.error(f"Error getting agent status: {e}")
            return {'total_agents': 0, 'active_agents': 0, 'agents_detail': []}
    
    async def get_security_statistics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get comprehensive security statistics"""
        try:
            with self._get_db_connection() as conn:
                time_filter, time_params = self._get_time_range_sql(start_time, end_time)
                
                # Overall statistics
                stats_query = f"""
                    SELECT 
                        COUNT(*) as total_events,
                        COUNT(DISTINCT agent_id) as unique_agents,
                        COUNT(DISTINCT rule_id) as unique_rules,
                        AVG(rule_level) as avg_severity,
                        MAX(rule_level) as max_severity,
                        MIN(timestamp) as period_start,
                        MAX(timestamp) as period_end
                    FROM wazuh_archives 
                    WHERE {time_filter}
                """
                
                cursor = conn.execute(stats_query, time_params)
                stats = dict(cursor.fetchone())
                
                # Severity distribution
                severity_query = f"""
                    SELECT rule_level, COUNT(*) as count
                    FROM wazuh_archives 
                    WHERE {time_filter}
                    GROUP BY rule_level
                    ORDER BY rule_level DESC
                """
                
                cursor = conn.execute(severity_query, time_params)
                severity_dist = {str(row['rule_level']): row['count'] for row in cursor.fetchall()}
                
                # Top rule groups
                groups_query = f"""
                    SELECT rule_groups, COUNT(*) as count
                    FROM wazuh_archives 
                    WHERE {time_filter}
                    AND rule_groups IS NOT NULL
                    GROUP BY rule_groups
                    ORDER BY count DESC
                    LIMIT 10
                """
                
                cursor = conn.execute(groups_query, time_params)
                top_rule_groups = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'summary': stats,
                    'severity_distribution': severity_dist,
                    'top_rule_groups': top_rule_groups,
                    'critical_events': int(severity_dist.get('7', 0)),
                    'high_events': int(severity_dist.get('6', 0)),
                    'medium_events': int(severity_dist.get('3', 0) + severity_dist.get('2', 0)),
                    'low_events': int(severity_dist.get('1', 0) + severity_dist.get('0', 0))
                }
                
        except Exception as e:
            logger.error(f"Error getting security statistics: {e}")
            return {}
    
    async def analyze_security_trends(self, start_time: datetime, end_time: datetime, 
                                    compare_previous: bool = True) -> Dict[str, Any]:
        """Analyze security trends with optional comparison to previous period"""
        try:
            current_stats = await self.get_security_statistics(start_time, end_time)
            
            trends = {
                'current_period': current_stats,
                'analysis': {}
            }
            
            if compare_previous:
                # Calculate previous period
                period_duration = end_time - start_time
                prev_end = start_time
                prev_start = prev_end - period_duration
                
                prev_stats = await self.get_security_statistics(prev_start, prev_end)
                trends['previous_period'] = prev_stats
                
                # Calculate changes
                if prev_stats.get('summary', {}).get('total_events', 0) > 0:
                    current_total = current_stats.get('summary', {}).get('total_events', 0)
                    prev_total = prev_stats.get('summary', {}).get('total_events', 0)
                    
                    change_percent = ((current_total - prev_total) / prev_total) * 100
                    trends['analysis'] = {
                        'total_events_change': change_percent,
                        'trend_direction': 'increasing' if change_percent > 5 else 'decreasing' if change_percent < -5 else 'stable',
                        'critical_events_change': current_stats.get('critical_events', 0) - prev_stats.get('critical_events', 0),
                        'high_events_change': current_stats.get('high_events', 0) - prev_stats.get('high_events', 0)
                    }
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing security trends: {e}")
            return {}
    
    async def generate_ai_analysis(self, report_data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
        """Generate AI analysis using existing LLM integration (similar to webapp)"""
        try:
            # Prepare analysis context
            analysis_context = self._prepare_analysis_context(report_data, report_type)
            
            # Use LLM for analysis (same pattern as webapp_chatbot.py)
            analysis_response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a cybersecurity analyst specializing in Wazuh SIEM data analysis. 
                        Analyze the provided security data and generate comprehensive insights for security teams.
                        
                        Focus on:
                        1. Critical security events and their implications
                        2. Threat patterns and attack indicators
                        3. Risk assessment and prioritization
                        4. Actionable recommendations for security teams
                        5. Trends and anomalies in the data
                        
                        Provide analysis in Indonesian language for better understanding by the team.
                        Be precise, actionable, and focus on security implications."""
                    },
                    {
                        "role": "user",
                        "content": analysis_context
                    }
                ],
                temperature=TelegramBotConfig.LM_STUDIO_CONFIG['temperature'],
                max_tokens=TelegramBotConfig.LM_STUDIO_CONFIG['max_tokens']
            )
            
            ai_analysis = analysis_response.choices[0].message.content
            
            # Calculate risk score based on data
            risk_score = self._calculate_risk_score(report_data)
            
            # Extract priority actions from AI analysis
            priority_actions = self._extract_priority_actions(ai_analysis)
            
            return {
                'ai_analysis': ai_analysis,
                'risk_score': risk_score,
                'risk_level': self._get_risk_level(risk_score),
                'priority_actions': priority_actions,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating AI analysis: {e}")
            return {
                'ai_analysis': f'Error dalam analisis AI: {str(e)}',
                'risk_score': 5,
                'risk_level': 'Medium',
                'priority_actions': ['Periksa log secara manual'],
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    def _prepare_analysis_context(self, report_data: Dict[str, Any], report_type: str) -> str:
        """Prepare context for AI analysis"""
        context = f"""LAPORAN KEAMANAN {report_type.upper()}
        
Periode: {report_data.get('period', 'Unknown')}
        
RINGKASAN STATISTIK:
- Total Events: {report_data.get('statistics', {}).get('summary', {}).get('total_events', 0)}
- Agent Aktif: {report_data.get('agent_status', {}).get('active_agents', 0)} dari {report_data.get('agent_status', {}).get('total_agents', 0)}
- Critical Events (Level 7): {report_data.get('statistics', {}).get('critical_events', 0)}
- High Events (Level 6): {report_data.get('statistics', {}).get('high_events', 0)}

TOP SECURITY EVENTS:
"""
        
        # Add sample events for context
        events = report_data.get('security_events', [])[:10]
        for i, event in enumerate(events, 1):
            context += f"\n{i}. [{event.get('rule_level', 'N/A')}] {event.get('rule_description', 'N/A')} - Agent: {event.get('agent_name', 'Unknown')}"
        
        # Add trend analysis if available
        if 'trends' in report_data:
            trends = report_data['trends'].get('analysis', {})
            context += f"\n\nTREND ANALYSIS:\n"
            context += f"- Perubahan Total Events: {trends.get('total_events_change', 0):.1f}%\n"
            context += f"- Arah Trend: {trends.get('trend_direction', 'stable')}\n"
        
        context += "\n\nSilakan berikan analisis mendalam tentang kondisi keamanan berdasarkan data di atas."
        
        return context
    
    def _calculate_risk_score(self, report_data: Dict[str, Any]) -> int:
        """Calculate risk score (1-10) based on security data"""
        try:
            stats = report_data.get('statistics', {})
            critical_events = stats.get('critical_events', 0)
            high_events = stats.get('high_events', 0)
            total_events = stats.get('summary', {}).get('total_events', 0)
            
            # Base score calculation
            base_score = 3
            
            # Critical events impact (0-4 points)
            if critical_events > 10:
                base_score += 4
            elif critical_events > 5:
                base_score += 3
            elif critical_events > 1:
                base_score += 2
            elif critical_events > 0:
                base_score += 1
            
            # High events impact (0-2 points) 
            if high_events > 20:
                base_score += 2
            elif high_events > 5:
                base_score += 1
            
            # Volume impact (0-1 point)
            if total_events > 1000:
                base_score += 1
            
            return min(base_score, 10)
            
        except Exception:
            return 5  # Default medium risk
    
    def _get_risk_level(self, risk_score: int) -> str:
        """Convert risk score to risk level"""
        if risk_score >= 8:
            return 'Critical'
        elif risk_score >= 6:
            return 'High'
        elif risk_score >= 4:
            return 'Medium'
        else:
            return 'Low'
    
    def _extract_priority_actions(self, ai_analysis: str) -> List[str]:
        """Extract priority actions from AI analysis"""
        # Simple extraction based on common patterns
        actions = []
        lines = ai_analysis.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['tindakan', 'action', 'rekomendasi', 'segera', 'prioritas']):
                if len(line) > 10 and len(line) < 200:  # Reasonable length
                    actions.append(line)
        
        # Default actions if none found
        if not actions:
            actions = [
                'Monitor sistem secara berkala',
                'Review log keamanan critical events',
                'Pastikan semua agent dalam kondisi aktif'
            ]
        
        return actions[:5]  # Top 5 actions
    
    # Report generation methods for different types
    async def generate_daily_report(self) -> Dict[str, Any]:
        """Generate daily security report"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=1)
        
        return await self._generate_base_report('daily', start_time, end_time)
    
    async def generate_three_daily_report(self) -> Dict[str, Any]:
        """Generate 3-day security trend report"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=3)
        
        return await self._generate_base_report('three_daily', start_time, end_time)
    
    async def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate weekly security summary report"""
        end_time = datetime.now()
        start_time = end_time - timedelta(weeks=1)
        
        return await self._generate_base_report('weekly', start_time, end_time)
    
    async def generate_monthly_report(self) -> Dict[str, Any]:
        """Generate monthly security assessment report"""
        end_time = datetime.now()
        # First day of current month
        start_time = end_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return await self._generate_base_report('monthly', start_time, end_time)
    
    async def _generate_base_report(self, report_type: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Generate base report structure for any type"""
        try:
            logger.info(f"Generating {report_type} report for period {start_time} to {end_time}")
            
            # Gather all data
            security_events = await self.get_security_events(start_time, end_time, report_type)
            agent_status = await self.get_agent_status_summary(start_time, end_time)
            statistics = await self.get_security_statistics(start_time, end_time)
            trends = await self.analyze_security_trends(start_time, end_time, 
                                                      compare_previous=(report_type != 'daily'))
            
            # Compile base report data
            report_data = {
                'report_type': report_type,
                'report_config': TelegramBotConfig.REPORT_TYPES[report_type],
                'period': f"{start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')}",
                'period_start': start_time.isoformat(),
                'period_end': end_time.isoformat(),
                'security_events': security_events,
                'agent_status': agent_status,
                'statistics': statistics,
                'trends': trends,
                'generated_at': datetime.now().isoformat()
            }
            
            # Generate AI analysis
            ai_analysis = await self.generate_ai_analysis(report_data, report_type)
            report_data['ai_analysis'] = ai_analysis
            
            logger.info(f"✅ {report_type} report generated successfully with {len(security_events)} events")
            return report_data
            
        except Exception as e:
            logger.error(f"Error generating {report_type} report: {e}")
            return {
                'error': f'Error generating {report_type} report: {str(e)}',
                'report_type': report_type,
                'generated_at': datetime.now().isoformat()
            }

# Initialize report generator
report_generator = None

async def get_report_generator():
    """Get initialized report generator instance"""
    global report_generator
    if report_generator is None:
        report_generator = SecurityReportGenerator()
        await report_generator.initialize()
    return report_generator
