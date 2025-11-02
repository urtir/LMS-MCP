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

# Import telegram config from config directory (NOT src.utils!)
from config.telegram_bot_config import TelegramBotConfig

logger = logging.getLogger(__name__)

class SecurityReportGenerator:
    """Generate security reports using existing Wazuh database and LLM integration"""
    
    def __init__(self):
        self.config = TelegramBotConfig()
        db_path = Path(self.config.DATABASE_CONFIG['wazuh_db'])
        if not db_path.is_absolute():
            db_path = (project_root / db_path).resolve()
        self.wazuh_db_path = str(db_path)
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
        """Generate SQL time range filter compatible with ISO timestamps."""
        # Stored timestamps look like 2025-11-02T04:09:04.730+0000
        # Normalise to "YYYY-MM-DD HH:MM:SS" for comparison
        time_expr = "datetime(replace(substr(timestamp, 1, 19), 'T', ' ')) BETWEEN ? AND ?"
        return time_expr, [
            start_time.strftime('%Y-%m-%d %H:%M:%S'),
            end_time.strftime('%Y-%m-%d %H:%M:%S')
        ]
    
    async def get_security_events(self, start_time: datetime, end_time: datetime, 
                                 report_type: str = 'daily') -> List[Dict[str, Any]]:
        """Get security events from Wazuh database for specified time range"""
        try:
            # Safe access to config with fallback
            if not hasattr(self.config, 'REPORT_TYPES') or report_type not in self.config.REPORT_TYPES:
                logger.warning(f"Report type '{report_type}' not found in config, using defaults")
                config = {
                    'priority_levels': [7, 8, 9, 10],  # Default to high/critical
                    'read_all_events': False,
                    'max_events': 100
                }
            else:
                config = self.config.REPORT_TYPES[report_type]
                
            priority_levels = config['priority_levels']
            read_all_events = config.get('read_all_events', False)
            
            with self._get_db_connection() as conn:
                # Build query for priority events - TANPA LIMIT, BACA SEMUA!
                time_filter, time_params = self._get_time_range_sql(start_time, end_time)
                level_placeholders = ','.join(['?'] * len(priority_levels))
                
                query = f"""
                    SELECT 
                        id, timestamp, agent_id, agent_name, manager_name,
                        rule_id, rule_level, rule_description, rule_mitre_tactic,
                        location, decoder_name, full_log,
                        json_data, created_at
                    FROM wazuh_archives 
                    WHERE {time_filter}
                    AND rule_level IN ({level_placeholders})
                    ORDER BY rule_level DESC, timestamp DESC
                """
                
                # HAPUS max_events dari parameter - BACA SEMUA EVENTS!
                params = time_params + priority_levels
                cursor = conn.execute(query, params)
                
                # Kumpulkan SEMUA events dan kelompokkan berdasarkan rule_id
                all_events = []
                events_by_rule = {}
                
                for row in cursor.fetchall():
                    if row is None:
                        continue
                        
                    event = dict(row)
                    if not event or not event.get('rule_id'):
                        continue
                        
                    # JANGAN PARSE! Simpan JSON data asli untuk LLM
                    all_events.append(event)
                    
                    # Kelompokkan berdasarkan rule_id
                    rule_id = event.get('rule_id')
                    if not rule_id:
                        continue
                        
                    if rule_id not in events_by_rule:
                        events_by_rule[rule_id] = {
                            'count': 0,
                            'representative_event': event,  # Event pertama sebagai perwakilan + RAW JSON DATA
                            'rule_description': event.get('rule_description', 'Unknown'),
                            'rule_level': event.get('rule_level', 0),
                            'latest_timestamp': event.get('timestamp', ''),
                            'earliest_timestamp': event.get('timestamp', '')
                        }
                    
                    events_by_rule[rule_id]['count'] += 1
                    # Update timestamp range - safely
                    event_timestamp = event.get('timestamp', '')
                    if event_timestamp and event_timestamp > events_by_rule[rule_id].get('latest_timestamp', ''):
                        events_by_rule[rule_id]['latest_timestamp'] = event_timestamp
                    if event_timestamp and event_timestamp < events_by_rule[rule_id].get('earliest_timestamp', ''):
                        events_by_rule[rule_id]['earliest_timestamp'] = event_timestamp
                
                # Convert ke format yang mudah dianalisis LLM
                grouped_events = []
                for rule_id, group_data in events_by_rule.items():
                    grouped_event = {
                        'rule_id': rule_id,
                        'count': group_data['count'],
                        'rule_description': group_data['rule_description'],
                        'rule_level': group_data['rule_level'],
                        'latest_occurrence': group_data['latest_timestamp'],
                        'earliest_occurrence': group_data['earliest_timestamp'],
                        'representative_event': group_data['representative_event'],  # FULL DATA + RAW JSON_DATA
                        'summary': f"Rule {rule_id}: {group_data['rule_description']} (Level {group_data['rule_level']}) - {group_data['count']} occurrences",
                        # PASTIKAN json_data RAW tersedia untuk LLM
                        'raw_json_sample': group_data['representative_event'].get('json_data', ''),
                        'full_log_sample': group_data['representative_event'].get('full_log', '')
                    }
                    grouped_events.append(grouped_event)
                
                # Sort berdasarkan rule level dan count
                grouped_events.sort(key=lambda x: (x['rule_level'], x['count']), reverse=True)
                
                logger.info(f"Found {len(all_events)} total events, grouped into {len(grouped_events)} rule types")
                return grouped_events
                
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
                stats_row = cursor.fetchone()
                stats = dict(stats_row) if stats_row else {
                    'total_events': 0,
                    'unique_agents': 0, 
                    'unique_rules': 0,
                    'avg_severity': 0,
                    'max_severity': 0,
                    'period_start': start_time.isoformat(),
                    'period_end': end_time.isoformat()
                }
                
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
                
                # Top MITRE tactics (instead of rule groups)
                tactics_query = f"""
                    SELECT rule_mitre_tactic, COUNT(*) as count
                    FROM wazuh_archives 
                    WHERE {time_filter}
                    AND rule_mitre_tactic IS NOT NULL
                    AND rule_mitre_tactic != ''
                    GROUP BY rule_mitre_tactic
                    ORDER BY count DESC
                    LIMIT 10
                """
                
                cursor = conn.execute(tactics_query, time_params)
                top_mitre_tactics = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'summary': stats,
                    'severity_distribution': severity_dist,
                    'top_mitre_tactics': top_mitre_tactics,
                    'critical_events': int(severity_dist.get('10', 0) + severity_dist.get('9', 0)),
                    'high_events': int(severity_dist.get('8', 0) + severity_dist.get('7', 0)),
                    'medium_events': int(severity_dist.get('6', 0) + severity_dist.get('5', 0)),
                    'low_events': int(severity_dist.get('4', 0) + severity_dist.get('3', 0) + severity_dist.get('2', 0) + severity_dist.get('1', 0))
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
                        "content": """Anda adalah analis keamanan siber ahli yang menganalisis data keamanan dari Wazuh SIEM.
                        Berikan analisis yang komprehensif dan profesional dalam bahasa Indonesia.
                        
                        **INSTRUKSI PENTING:**
                        1. Anda boleh menggunakan <think>...</think> untuk proses berpikir internal
                        2. Setelah <think> selesai, berikan analisis yang JELAS dan TERSTRUKTUR  
                        3. Fokus pada data konkret dari events yang diberikan
                        4. Berikan rekomendasi yang actionable dan spesifik
                        
                        **FORMAT ANALISIS:**
                        
                        **RINGKASAN EKSEKUTIF**
                        - Berikan ringkasan singkat kondisi keamanan saat ini
                        
                        **ANALISIS DETAIL SECURITY EVENTS**
                        - Analisis setiap event dengan detail technical
                        - Extract IP addresses, URLs, payloads dari JSON data
                        - Identifikasi attack vectors dan techniques
                        
                        **INDICATORS OF COMPROMISE (IoCs)**
                        - Daftar IP addresses yang mencurigakan
                        - URLs dan file paths yang terkompromasi
                        - Attack signatures yang terdeteksi
                        
                        **PENILAIAN RISIKO**
                        - Evaluasi tingkat risiko berdasarkan severity dan impact
                        - Identifikasi potensi dampak bisnis
                        
                        **REKOMENDASI TINDAKAN**
                        Berikan dalam format bullet points:
                        • Aksi 1: Detail spesifik yang harus dilakukan
                        • Aksi 2: Detail spesifik yang harus dilakukan
                        • Aksi 3: Detail spesifik yang harus dilakukan
                        
                        Pastikan analisis professional, faktual, dan mudah dipahami oleh tim keamanan."""
                    },
                    {
                        "role": "user",
                        "content": analysis_context
                    }
                ],
                temperature=self.config.LM_STUDIO_CONFIG['temperature'],
                max_tokens=self.config.LM_STUDIO_CONFIG['max_tokens']
            )
            
            ai_analysis = analysis_response.choices[0].message.content
            
            # Remove thinking tags BEFORE any further processing
            ai_analysis = self._remove_thinking_tags(ai_analysis)
            
            # Calculate risk score based on data
            risk_score = self._calculate_risk_score(report_data)
            
            # Extract priority actions from AI analysis (now cleaned)
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

ALL SECURITY EVENTS (GROUPED BY RULE ID):
"""
        
        # TAMPILKAN SEMUA EVENTS - JANGAN DIBATASI!
        events = report_data.get('security_events', [])  # HAPUS [:10] - TAMPILKAN SEMUA!
        for i, event in enumerate(events, 1):
            rep_event = event.get('representative_event', {})
            agent_name = rep_event.get('agent_name', 'Unknown')
            agent_id = rep_event.get('agent_id', 'N/A')
            location = rep_event.get('location', 'N/A')
            timestamp = rep_event.get('timestamp', 'N/A')
            
            context += f"\n{i}. [Level {event.get('rule_level', 'N/A')}] Rule {event.get('rule_id', 'N/A')}: {event.get('rule_description', 'N/A')}"
            context += f"\n   - Agent: {agent_name} (ID: {agent_id})"
            context += f"\n   - Location: {location}"
            context += f"\n   - Count: {event.get('count', 1)} occurrences"
            context += f"\n   - Latest: {event.get('latest_occurrence', timestamp)}"
            
            # TAMBAHKAN RAW JSON DATA LENGKAP UNTUK ANALISIS MENDALAM - JANGAN DIPOTONG!
            raw_json = event.get('raw_json_sample', '')
            if raw_json:
                # Kirim JSON lengkap ke AI untuk analisis mendalam
                context += f"\n   - Raw JSON Data: {raw_json}"
            
            full_log = event.get('full_log_sample', '')
            if full_log:
                # Kirim full log lengkap ke AI 
                context += f"\n   - Full Log: {full_log}"
            
            context += "\n"
        
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
        # First remove think tags
        clean_analysis = self._remove_thinking_tags(ai_analysis)
        
        actions = []
        lines = clean_analysis.split('\n')
        
        # Look for recommendations or action sections
        in_recommendation_section = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check if we're entering a recommendations section
            if any(keyword in line.lower() for keyword in ['rekomendasi', 'tindakan', 'action', 'langkah']):
                if len(line) < 100:  # This is likely a header
                    in_recommendation_section = True
                    continue
            
            # If in recommendations section, look for bullet points or numbered items
            if in_recommendation_section:
                # Look for bullet points or numbered lists
                if line.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')):
                    # Clean and extract the action
                    clean_action = line
                    for prefix in ['•', '-', '*', '1.', '2.', '3.', '4.', '5.']:
                        clean_action = clean_action.lstrip(prefix).strip()
                    
                    if len(clean_action) > 20 and len(clean_action) < 300:  # Reasonable length
                        actions.append(clean_action)
                        
                # Stop if we hit another section header
                elif line.startswith('**') or line.startswith('#'):
                    break
            
            # Also look for direct action items anywhere in text
            elif any(keyword in line.lower() for keyword in ['monitor', 'blokir', 'pastikan', 'periksa', 'aktifkan', 'isolasi']):
                if len(line) > 20 and len(line) < 300:
                    actions.append(line)
        
        # Default actions if none found or too few
        if len(actions) < 2:
            actions = [
                'Monitor sistem secara berkala',
                'Review log keamanan critical events',
                'Pastikan semua agent dalam kondisi aktif',
                'Blokir IP addresses yang mencurigakan',
                'Update security measures jika diperlukan'
            ]
        
        return actions[:5]  # Top 5 actions
    
    def _remove_thinking_tags(self, text: str) -> str:
        """Remove thinking tags and any content within them from AI analysis"""
        import re
        
        # Remove <think>...</think> blocks completely
        clean_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Also remove any standalone <think> or </think> tags
        clean_text = re.sub(r'</?think>', '', clean_text, flags=re.IGNORECASE)
        
        # Clean up extra whitespace and newlines
        clean_text = re.sub(r'\n\s*\n\s*\n', '\n\n', clean_text)  # Remove excessive newlines
        clean_text = clean_text.strip()
        
        return clean_text
    
    # Report generation methods for different types
    async def generate_daily_report(self) -> Dict[str, Any]:
        """Generate daily security report - dari jam 00:00:00 hari ini sampai sekarang"""
        end_time = datetime.now()
        # Start dari jam 00:00:00 hari ini
        start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        return await self._generate_base_report('daily', start_time, end_time)
    
    async def generate_three_daily_report(self) -> Dict[str, Any]:
        """Generate 3-day security trend report - 3 hari terakhir lengkap + hari ini"""
        end_time = datetime.now()
        # 3 hari yang lalu jam 00:00 sampai sekarang
        start_time = (datetime.now() - timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        return await self._generate_base_report('three_daily', start_time, end_time)
    
    async def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate weekly security summary report - minggu ini (Senin-sekarang)"""
        end_time = datetime.now()
        # Hari Senin minggu ini jam 00:00
        days_since_monday = end_time.weekday()  # Monday = 0
        start_time = (end_time - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        return await self._generate_base_report('weekly', start_time, end_time)
    
    async def generate_monthly_report(self) -> Dict[str, Any]:
        """Generate monthly security assessment report - bulan ini (tanggal 1-sekarang)"""
        end_time = datetime.now()
        # Tanggal 1 bulan ini jam 00:00
        start_time = end_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return await self._generate_base_report('monthly', start_time, end_time)
    
    async def _generate_base_report(self, report_type: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Generate base report structure for any type"""
        try:
            logger.info(f"Generating {report_type} report for period {start_time} to {end_time}")
            
            # Gather all data - ensure all methods return safe defaults
            security_events = await self.get_security_events(start_time, end_time, report_type) or []
            agent_status = await self.get_agent_status_summary(start_time, end_time) or {}
            statistics = await self.get_security_statistics(start_time, end_time) or {}
            trends = await self.analyze_security_trends(start_time, end_time, 
                                                      compare_previous=(report_type != 'daily')) or {}
            
            # Compile base report data
            report_config = getattr(self.config, 'REPORT_TYPES', {}).get(report_type, {
                'name': f'{report_type.title()} Report',
                'emoji': '📊',
                'description': f'Security report for {report_type}'
            })
            
            report_data = {
                'report_type': report_type,
                'report_config': report_config,
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
