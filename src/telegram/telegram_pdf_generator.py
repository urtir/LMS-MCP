#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Report Generator for Telegram Bot
Creates professional PDF reports from security data
"""

import io
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus import Image as ReportLabImage
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import base64

# Add parent directories to path for importing project modules
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# Import internal telegram config
from src.utils.telegram_config import TelegramBotConfig

logger = logging.getLogger(__name__)

class PDFReportGenerator:
    """Generate professional PDF security reports"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.telegram_config = TelegramBotConfig()
        self.config = self.telegram_config.PDF_CONFIG
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Setup custom PDF styles for security reports"""
        
        # Custom title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=self.config['title_font_size'],
            textColor=colors.darkblue,
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=self.config['header_font_size'],
            textColor=colors.darkred,
            spaceBefore=20,
            spaceAfter=12,
            fontName='Helvetica-Bold',
            borderWidth=1,
            borderColor=colors.darkred,
            borderPadding=5
        ))
        
        # Subsection header style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.darkgreen,
            spaceBefore=15,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))
        
        # Alert style for critical information
        self.styles.add(ParagraphStyle(
            name='AlertStyle',
            parent=self.styles['Normal'],
            fontSize=self.config['body_font_size'],
            textColor=colors.darkred,
            backgroundColor=colors.lightyellow,
            borderWidth=1,
            borderColor=colors.red,
            borderPadding=10,
            spaceAfter=10
        ))
        
        # Summary box style
        self.styles.add(ParagraphStyle(
            name='SummaryBox',
            parent=self.styles['Normal'],
            fontSize=self.config['body_font_size'],
            backgroundColor=colors.lightblue,
            borderWidth=1,
            borderColor=colors.blue,
            borderPadding=10,
            spaceAfter=15
        ))
        
        # Code/log style
        self.styles.add(ParagraphStyle(
            name='CodeStyle',
            parent=self.styles['Code'],
            fontSize=10,
            fontName='Courier',
            backgroundColor=colors.lightgrey,
            borderWidth=1,
            borderColor=colors.grey,
            borderPadding=5,
            spaceAfter=10
        ))
    
    async def generate_pdf_report(self, report_data: Dict[str, Any]) -> io.BytesIO:
        """Generate comprehensive PDF report"""
        try:
            logger.info(f"Generating PDF report for {report_data.get('report_type', 'unknown')} report")
            
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer, 
                pagesize=A4,
                rightMargin=self.config['margins']['right'],
                leftMargin=self.config['margins']['left'],
                topMargin=self.config['margins']['top'],
                bottomMargin=self.config['margins']['bottom']
            )
            
            story = []
            
            # Generate report content
            self._add_title_page(story, report_data)
            self._add_executive_summary(story, report_data)
            self._add_security_metrics(story, report_data)
            self._add_security_events_analysis(story, report_data)
            self._add_agent_status_section(story, report_data)
            self._add_ai_analysis_section(story, report_data)
            self._add_trends_analysis(story, report_data)
            self._add_recommendations(story, report_data)
            self._add_appendices(story, report_data)
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            
            logger.info(f"✅ PDF report generated successfully")
            return buffer
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            # Return simple error PDF without complex formatting
            buffer = io.BytesIO()
            error_doc = SimpleDocTemplate(buffer, pagesize=A4)
            
            # Create simple error message without special characters
            error_msg = str(e).replace('<', '').replace('>', '').replace('&', 'and')[:200]
            
            error_story = [
                Paragraph("PDF Generation Error", self.styles['Title']),
                Paragraph(f"An error occurred while generating the report.", self.styles['Normal']),
                Paragraph(f"Error details: {error_msg}", self.styles['Normal']),
                Paragraph("Please contact system administrator for assistance.", self.styles['Normal'])
            ]
            
            try:
                error_doc.build(error_story)
            except Exception as inner_e:
                # If even the error PDF fails, create minimal content
                logger.error(f"Error creating error PDF: {inner_e}")
                error_story = [Paragraph("PDF Error - Contact Administrator", self.styles['Normal'])]
                error_doc.build(error_story)
            
            buffer.seek(0)
            return buffer
    
    def _add_title_page(self, story: List, report_data: Dict[str, Any]):
        """Add title page to report"""
        config = report_data.get('report_config', {})
        
        story.append(Spacer(1, 100))
        story.append(Paragraph(
            f"{config.get('emoji', '📊')} {config.get('name', 'Security Report')}", 
            self.styles['CustomTitle']
        ))
        
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Periode: {report_data.get('period', 'Unknown')}", self.styles['Heading3']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M:%S WIB')}", self.styles['Normal']))
        
        # Add risk level indicator
        ai_analysis = report_data.get('ai_analysis', {})
        risk_level = ai_analysis.get('risk_level', 'Unknown')
        
        # Handle None or empty risk_level
        if risk_level is None or risk_level == '':
            risk_level = 'Unknown'
        
        risk_color = self._get_risk_color(risk_level)
        
        story.append(Spacer(1, 40))
        risk_style = ParagraphStyle(
            'RiskLevel',
            parent=self.styles['Heading2'],
            textColor=risk_color,
            alignment=TA_CENTER,
            fontSize=18,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph(f"🚨 Risk Level: {risk_level or 'Unknown'}", risk_style))
        
        story.append(PageBreak())
    
    def _add_executive_summary(self, story: List, report_data: Dict[str, Any]):
        """Add executive summary section"""
        story.append(Paragraph("📋 Executive Summary", self.styles['SectionHeader']))
        
        statistics = report_data.get('statistics', {})
        summary_stats = statistics.get('summary', {})
        ai_analysis = report_data.get('ai_analysis', {})
        
        # Key metrics summary
        summary_text = f"""
        <b>Ringkasan Periode {report_data.get('period', 'Unknown')}:</b><br/><br/>
        
        • <b>Total Security Events:</b> {summary_stats.get('total_events', 0):,} events<br/>
        • <b>Critical Events (Level 7):</b> {statistics.get('critical_events', 0)} events<br/>
        • <b>High Priority Events (Level 6):</b> {statistics.get('high_events', 0)} events<br/>
        • <b>Active Agents:</b> {report_data.get('agent_status', {}).get('active_agents', 0)} dari {report_data.get('agent_status', {}).get('total_agents', 0)} agents<br/>
        • <b>Risk Score:</b> {ai_analysis.get('risk_score', 'N/A')}/10<br/>
        • <b>Risk Level:</b> {ai_analysis.get('risk_level', 'Unknown')}<br/><br/>
        
        <b>Status Keamanan:</b> {self._get_security_status_text(ai_analysis.get('risk_level', 'Unknown'))}
        """
        
        story.append(Paragraph(summary_text, self.styles['SummaryBox']))
        story.append(Spacer(1, 20))
    
    def _add_security_metrics(self, story: List, report_data: Dict[str, Any]):
        """Add security metrics section with charts"""
        story.append(Paragraph("📊 Security Metrics", self.styles['SectionHeader']))
        
        statistics = report_data.get('statistics', {})
        
        # Create metrics table with proper column widths
        metrics_data = [
            ['Metric', 'Value', 'Description']
        ]
        
        # Define column widths for better layout (total ~500 points)
        col_widths = [140, 80, 280]  # Total: 500
        
        summary = statistics.get('summary', {})
        metrics_data.extend([
            ['Total Events', f"{summary.get('total_events', 0):,}", 'Total security events in period'],
            ['Unique Agents', f"{summary.get('unique_agents', 0)}", 'Number of different agents reporting'],
            ['Unique Rules', f"{summary.get('unique_rules', 0)}", 'Number of different security rules triggered'],
            ['Average Severity', f"{summary.get('avg_severity', 0):.1f}", 'Average severity level of events'],
            ['Max Severity', f"{summary.get('max_severity', 0)}", 'Highest severity level detected'],
            ['Critical Events', f"{statistics.get('critical_events', 0)}", 'Level 7 - Immediate attention required'],
            ['High Events', f"{statistics.get('high_events', 0)}", 'Level 6 - High priority events'],
            ['Medium Events', f"{statistics.get('medium_events', 0)}", 'Level 2-3 - Medium priority events'],
            ['Low Events', f"{statistics.get('low_events', 0)}", 'Level 0-1 - Low priority events']
        ])
        
        metrics_table = Table(metrics_data, colWidths=col_widths, repeatRows=1)
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),  # Center first two columns
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),    # Left align description column
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        
        story.append(metrics_table)
        story.append(Spacer(1, 20))
        
        # Add severity distribution chart info
        severity_dist = statistics.get('severity_distribution', {})
        if severity_dist:
            story.append(Paragraph("Distribusi Tingkat Keamanan:", self.styles['SubsectionHeader']))
            
            dist_text = ""
            for level, count in sorted(severity_dist.items(), key=lambda x: int(x[0]), reverse=True):
                level_name = self._get_severity_name(int(level))
                dist_text += f"• Level {level} ({level_name}): {count} events<br/>"
            
            story.append(Paragraph(dist_text, self.styles['Normal']))
            story.append(Spacer(1, 15))
    
    def _add_security_events_analysis(self, story: List, report_data: Dict[str, Any]):
        """Add security events analysis section"""
        story.append(Paragraph("🔍 Security Events Analysis", self.styles['SectionHeader']))
        
        events = report_data.get('security_events', [])
        
        if not events:
            story.append(Paragraph("Tidak ada security events dalam periode ini.", self.styles['Normal']))
            return
        
        story.append(Paragraph(f"All Security Events - {len(events)} Grouped Rules (berdasarkan prioritas):", 
                             self.styles['SubsectionHeader']))
        
        # Create events table with KOLOM JUMLAH
        events_data = [
            ['Waktu', 'Level', 'Rule ID', 'Description', 'Agent', 'Jumlah', 'Location']
        ]
        
        # Define optimal column widths for A4 page dengan kolom jumlah
        col_widths = [60, 30, 45, 150, 75, 40, 70]  # Total: 470
        
        for event in events:  # TAMPILKAN SEMUA EVENTS - HAPUS [:20]!
            # GUNAKAN DATA DARI REPRESENTATIVE_EVENT
            rep_event = event.get('representative_event', {})
            
            timestamp = rep_event.get('timestamp', event.get('latest_occurrence', ''))
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp = dt.strftime('%d/%m %H:%M')
                except:
                    timestamp = timestamp[:16]  # Fallback
                    
            # KOLOM JUMLAH TERPISAH
            count = event.get('count', 1)
            
            events_data.append([
                timestamp,
                str(event.get('rule_level', 'N/A')),
                str(event.get('rule_id', 'N/A')),
                self._truncate_text(self._clean_text_for_pdf(event.get('rule_description', 'N/A')), 35),
                self._truncate_text(self._clean_text_for_pdf(rep_event.get('agent_name', 'N/A')), 15),
                str(count),  # KOLOM JUMLAH DEDICATED
                self._truncate_text(self._clean_text_for_pdf(rep_event.get('location', 'N/A')), 18)
            ])
        
        events_table = Table(events_data, colWidths=col_widths, repeatRows=1)
        events_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('WORDWRAP', (0, 0), (-1, -1), 'CJK'),
        ]))
        
        story.append(events_table)
        story.append(Spacer(1, 20))
    
    def _add_agent_status_section(self, story: List, report_data: Dict[str, Any]):
        """Add agent status section"""
        story.append(Paragraph("🖥️ Agent Status Overview", self.styles['SectionHeader']))
        
        agent_status = report_data.get('agent_status', {})
        agents_detail = agent_status.get('agents_detail', [])
        
        # Summary
        summary_text = f"""
        <b>Agent Summary:</b><br/>
        • Total Agents: {agent_status.get('total_agents', 0)}<br/>
        • Active Agents: {agent_status.get('active_agents', 0)}<br/>
        • Inactive Agents: {agent_status.get('total_agents', 0) - agent_status.get('active_agents', 0)}<br/>
        """
        story.append(Paragraph(summary_text, self.styles['Normal']))
        story.append(Spacer(1, 10))
        
        if agents_detail:
            story.append(Paragraph("Top Active Agents:", self.styles['SubsectionHeader']))
            
            # Create agents table with proper column widths
            agents_data = [
                ['Agent Name', 'Agent ID', 'Events', 'Avg Severity', 'Max Severity', 'Last Activity']
            ]
            
            # Define optimal column widths for A4 page (total ~500 points)
            col_widths = [90, 60, 50, 65, 65, 120]  # Total: 450
            
            for agent in agents_detail:
                last_event = agent.get('last_event', '')
                if last_event:
                    try:
                        dt = datetime.fromisoformat(last_event.replace('Z', '+00:00'))
                        last_event = dt.strftime('%d/%m/%Y %H:%M')
                    except:
                        last_event = last_event[:16]
                        
                agents_data.append([
                    self._truncate_text(self._clean_text_for_pdf(agent.get('agent_name', 'N/A')), 15),
                    str(agent.get('agent_id', 'N/A'))[:8] + '...' if len(str(agent.get('agent_id', 'N/A'))) > 8 else str(agent.get('agent_id', 'N/A')),
                    str(agent.get('event_count', 0)),
                    f"{agent.get('avg_severity', 0):.1f}",
                    str(agent.get('max_severity', 0)),
                    self._truncate_text(last_event, 15)
                ])
            
            agents_table = Table(agents_data, colWidths=col_widths, repeatRows=1)
            agents_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ]))
            
            story.append(agents_table)
        
        story.append(Spacer(1, 20))
    
    def _add_ai_analysis_section(self, story: List, report_data: Dict[str, Any]):
        """Add AI analysis section"""
        story.append(Paragraph("🤖 AI Security Analysis", self.styles['SectionHeader']))
        
        ai_analysis = report_data.get('ai_analysis', {})
        
        if not ai_analysis.get('ai_analysis'):
            story.append(Paragraph("AI analysis tidak tersedia.", self.styles['Normal']))
            return
        
        # Risk assessment box
        risk_info = f"""
        <b>Risk Assessment:</b><br/>
        • Risk Score: {ai_analysis.get('risk_score', 'N/A')}/10<br/>
        • Risk Level: {ai_analysis.get('risk_level', 'Unknown')}<br/>
        • Analysis Time: {ai_analysis.get('analysis_timestamp', 'N/A')}<br/>
        """
        story.append(Paragraph(risk_info, self.styles['SummaryBox']))
        
        # AI Analysis content - Remove thinking tags and format markdown
        story.append(Paragraph("Analisis AI:", self.styles['SubsectionHeader']))
        ai_text = ai_analysis.get('ai_analysis', '')
        
        # Remove thinking tags completely
        ai_text = self._remove_thinking_tags(ai_text)
        
        # Safely format for PDF with fallback to plain text
        try:
            # Try to format markdown first
            formatted_analysis = self._format_markdown_for_pdf(ai_text)
            
            # Test if the formatted text can be parsed safely
            # Create a test paragraph to validate HTML
            test_para = Paragraph(f"<para>{formatted_analysis}</para>", self.styles['Normal'])
            
            # If we get here, the HTML is valid
            story.append(Paragraph(f"<para>{formatted_analysis}</para>", self.styles['Normal']))
            
        except Exception as format_error:
            logger.warning(f"Markdown formatting failed, using plain text: {format_error}")
            
            # Fallback: use plain text with basic formatting
            plain_text = self._clean_text_for_pdf(ai_text, preserve_html=False)
            
            # Add basic structure to plain text
            plain_text = plain_text.replace('\n\n', '<br/><br/>')
            plain_text = plain_text.replace('\n', '<br/>')
            
            # Ensure it's wrapped in para tags
            story.append(Paragraph(f"<para>{plain_text}</para>", self.styles['Normal']))
        
        story.append(Spacer(1, 15))
        
        # Priority actions
        priority_actions = ai_analysis.get('priority_actions', [])
        if priority_actions:
            story.append(Paragraph("🚨 Priority Actions:", self.styles['SubsectionHeader']))
            
            actions_text = ""
            for i, action in enumerate(priority_actions, 1):
                # Clean and format each action
                clean_action = self._clean_text_for_pdf(action)
                actions_text += f"{i}. {clean_action}<br/>"
            
            story.append(Paragraph(actions_text, self.styles['AlertStyle']))
        
        story.append(Spacer(1, 20))
    
    def _add_trends_analysis(self, story: List, report_data: Dict[str, Any]):
        """Add trends analysis section"""
        trends = report_data.get('trends', {})
        
        if not trends or 'analysis' not in trends:
            return
            
        story.append(Paragraph("📈 Trend Analysis", self.styles['SectionHeader']))
        
        analysis = trends.get('analysis', {})
        
        trend_text = f"""
        <b>Trend Comparison dengan Periode Sebelumnya:</b><br/><br/>
        • Total Events Change: {analysis.get('total_events_change', 0):.1f}%<br/>
        • Trend Direction: {analysis.get('trend_direction', 'stable').title()}<br/>
        • Critical Events Change: {analysis.get('critical_events_change', 0):+d}<br/>
        • High Events Change: {analysis.get('high_events_change', 0):+d}<br/>
        """
        
        story.append(Paragraph(trend_text, self.styles['Normal']))
        story.append(Spacer(1, 20))
    
    def _add_recommendations(self, story: List, report_data: Dict[str, Any]):
        """Add recommendations section"""
        story.append(Paragraph("💡 Recommendations", self.styles['SectionHeader']))
        
        ai_analysis = report_data.get('ai_analysis', {})
        priority_actions = ai_analysis.get('priority_actions', [])
        
        # General recommendations based on data
        recommendations = []
        
        # Add AI-generated recommendations
        recommendations.extend(priority_actions[:3])
        
        # Add data-driven recommendations
        statistics = report_data.get('statistics', {})
        if statistics.get('critical_events', 0) > 5:
            recommendations.append("Investigasi mendalam diperlukan untuk critical events yang tinggi")
        
        if report_data.get('agent_status', {}).get('active_agents', 0) < report_data.get('agent_status', {}).get('total_agents', 1):
            recommendations.append("Periksa dan aktifkan agent yang tidak responsive")
        
        # Default recommendations
        if not recommendations:
            recommendations = [
                "Lanjutkan monitoring keamanan secara berkala",
                "Review dan update security policies",
                "Pastikan semua agent dalam kondisi optimal"
            ]
        
        rec_text = ""
        for i, rec in enumerate(recommendations, 1):
            rec_text += f"{i}. {rec}<br/>"
        
        story.append(Paragraph(rec_text, self.styles['Normal']))
        story.append(Spacer(1, 20))
    
    def _add_appendices(self, story: List, report_data: Dict[str, Any]):
        """Add appendices section"""
        story.append(PageBreak())
        story.append(Paragraph("📎 Appendices", self.styles['SectionHeader']))
        
        # Report metadata
        story.append(Paragraph("Report Metadata:", self.styles['SubsectionHeader']))
        
        metadata_text = f"""
        • Report Type: {report_data.get('report_type', 'Unknown').title()}<br/>
        • Generated At: {report_data.get('generated_at', 'Unknown')}<br/>
        • Period: {report_data.get('period', 'Unknown')}<br/>
        • Database Records: {len(report_data.get('security_events', []))}<br/>
        • Analysis Engine: LM Studio + Wazuh FastMCP<br/>
        """
        
        story.append(Paragraph(metadata_text, self.styles['Normal']))
        story.append(Spacer(1, 15))
        
        # Top rule groups
        statistics = report_data.get('statistics', {})
        top_groups = statistics.get('top_rule_groups', [])
        
        if top_groups:
            story.append(Paragraph("Top Rule Groups:", self.styles['SubsectionHeader']))
            
            # Improved table with proper column widths
            groups_data = [['Rule Group', 'Event Count']]
            col_widths = [350, 100]  # Total: 450
            
            for group in top_groups[:10]:
                groups_data.append([
                    self._truncate_text(self._clean_text_for_pdf(group.get('rule_groups', 'N/A')), 60),
                    str(group.get('count', 0))
                ])
            
            groups_table = Table(groups_data, colWidths=col_widths, repeatRows=1)
            groups_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),    # Left align rule group
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Center align count
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ]))
            
            story.append(groups_table)
    
    # Helper methods
    def _get_risk_color(self, risk_level: str):
        """Get color for risk level"""
        color_map = {
            'Critical': colors.red,
            'High': colors.orange,
            'Medium': colors.yellow,
            'Low': colors.green
        }
        return color_map.get(risk_level, colors.black)
    
    def _get_security_status_text(self, risk_level: str) -> str:
        """Get security status description"""
        status_map = {
            'Critical': 'Sistem memerlukan perhatian segera. Tindakan darurat diperlukan.',
            'High': 'Risiko tinggi terdeteksi. Monitoring ekstra dan tindakan preventif diperlukan.',
            'Medium': 'Kondisi keamanan normal dengan beberapa peringatan yang perlu dimonitor.',
            'Low': 'Sistem dalam kondisi aman. Lanjutkan monitoring rutin.'
        }
        return status_map.get(risk_level, 'Status keamanan tidak dapat ditentukan.')
    
    def _get_severity_name(self, level: int) -> str:
        """Get severity level name"""
        severity_map = {
            0: 'Info',
            1: 'Low',
            2: 'Low',
            3: 'Medium',
            6: 'High',
            7: 'Critical'
        }
        return severity_map.get(level, f'Level-{level}')
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to specified length"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def _remove_thinking_tags(self, text: str) -> str:
        """Remove <thinking></thinking> tags and their content completely"""
        import re
        # Remove thinking tags and everything between them
        pattern = r'<thinking>.*?</thinking>'
        cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Also remove any remaining thinking-related patterns
        cleaned_text = re.sub(r'</?thinking[^>]*>', '', cleaned_text, flags=re.IGNORECASE)
        
        # Clean up extra whitespace and newlines
        cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)  # Replace multiple newlines with double
        cleaned_text = re.sub(r'^\s*\n', '', cleaned_text)  # Remove leading newlines
        cleaned_text = cleaned_text.strip()
        
        return cleaned_text
    
    def _format_markdown_for_pdf(self, text: str) -> str:
        """Format markdown text for PDF display"""
        import re
        
        # Handle None or empty text
        if not text:
            return ""
        
        # Convert markdown headers to HTML-like formatting (from largest to smallest)
        text = re.sub(r'^##### (.*?)$', r'<i><u>\1</u></i>', text, flags=re.MULTILINE)  # Level 5 - Italic + Underline
        text = re.sub(r'^#### (.*?)$', r'<b><u>\1</u></b>', text, flags=re.MULTILINE)  # Level 4 - Bold + Underline
        text = re.sub(r'^### (.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)          # Level 3 - Bold
        text = re.sub(r'^## (.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)           # Level 2 - Bold  
        text = re.sub(r'^# (.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)            # Level 1 - Bold
        
        # Handle repeated characters (decorative lines)
        # Convert long repeated I's to visual separator
        text = re.sub(r'^I{10,}$', r'<br/>▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌<br/>', text, flags=re.MULTILINE)
        
        # Convert other repeated characters to decorative separators
        text = re.sub(r'^([=\-_#\*])\1{10,}$', r'<br/>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━<br/>', text, flags=re.MULTILINE)
        
        # Convert horizontal rules (---) to visual separator  
        text = re.sub(r'^---+$', r'<br/>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━<br/>', text, flags=re.MULTILINE)
        
        # Convert markdown bold (handle multiple asterisks)
        text = re.sub(r'\*{2,}(.*?)\*{2,}', r'<b>\1</b>', text)  # Multiple asterisks
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)
        
        # Convert markdown italic  
        text = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'<i>\1</i>', text)  # Single asterisk (not part of double)
        text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'<i>\1</i>', text)       # Single underscore (not part of double)
        
        # Convert bullet points
        text = re.sub(r'^[\-\*\+] (.*?)$', r'• \1', text, flags=re.MULTILINE)
        
        # Convert numbered lists
        text = re.sub(r'^(\d+)\. (.*?)$', r'\1. \2', text, flags=re.MULTILINE)
        
        # Convert code blocks (basic support)
        text = re.sub(r'`([^`]+)`', r'<font name="Courier">\1</font>', text)
        
        # Handle special markdown patterns
        # Convert standalone ** as emphasis marker
        text = re.sub(r'^\*\*\s*$', r'<b>※</b>', text, flags=re.MULTILINE)
        
        # Replace newlines with HTML breaks
        text = text.replace('\n', '<br/>')
        
        # Clean up extra spaces and breaks
        text = re.sub(r'<br/>\s*<br/>', '<br/><br/>', text)
        text = re.sub(r'(<br/>){3,}', '<br/><br/>', text)  # Max 2 consecutive breaks
        
        return text
    
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
    
    def _clean_text_for_pdf(self, text: str, preserve_html: bool = False) -> str:
        """Clean text for safe PDF rendering"""
        if not text:
            return ""
        
        # Convert to string first
        text = str(text)
        
        if not preserve_html:
            # Remove or escape problematic characters for plain text
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;').replace('>', '&gt;')
            text = text.replace('"', '&quot;').replace("'", '&apos;')
        else:
            # For HTML/markdown formatted text, only escape problematic characters that aren't part of HTML tags
            import re
            # Escape & that are not part of HTML entities
            text = re.sub(r'&(?![a-zA-Z0-9#]+;)', '&amp;', text)
        
        # Remove non-printable characters
        import re
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        if not preserve_html:
            # Normalize whitespace for plain text
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
        
        return text
