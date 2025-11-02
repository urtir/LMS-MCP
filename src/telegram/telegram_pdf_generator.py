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
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus import Image as ReportLabImage
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import base64

# Design constants
BASE_UNIT = 8  # Core spacing/font step size
TITLE_FONT_SIZE = BASE_UNIT * 4  # 32pt
SECTION_FONT_SIZE = BASE_UNIT * 3  # 24pt
SUBSECTION_FONT_SIZE = BASE_UNIT * 2  # 16pt
BODY_FONT_SIZE = BASE_UNIT * 1.5  # 12pt for readability while aligned to 8-based hierarchy

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
        self.telegram_config = TelegramBotConfig()
        self.config = self.telegram_config.PDF_CONFIG
        self.styles = getSampleStyleSheet()
        self.fonts = {}
        self.palette = {
            'text_primary': colors.HexColor('#1F2933'),
            'text_muted': colors.HexColor('#475569'),
            'accent': colors.HexColor('#4338CA'),
            'accent_soft': colors.HexColor('#EEF2FF'),
            'accent_dark': colors.HexColor('#312E81'),
            'success': colors.HexColor('#047857'),
            'warning': colors.HexColor('#D97706'),
            'danger': colors.HexColor('#B91C1C'),
            'background_muted': colors.HexColor('#F5F7FA')
        }
        self._register_fonts()
        self._setup_custom_styles()
    
    def _spacer(self, units: float = 1) -> Spacer:
        """Return a spacer using the design base unit."""
        return Spacer(1, BASE_UNIT * units)
    
    def _register_fonts(self):
        """Register Poppins font family for consistent typography."""
        fonts_dir = Path(self.config.get('font_dir', project_root / 'assets' / 'fonts'))
        font_map = {
            'Regular': fonts_dir / 'Poppins-Regular.ttf',
            'Medium': fonts_dir / 'Poppins-Medium.ttf',
            'Semibold': fonts_dir / 'Poppins-SemiBold.ttf',
            'Bold': fonts_dir / 'Poppins-Bold.ttf',
        }
        missing = [name for name, path in font_map.items() if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                "Missing Poppins font files: " + ', '.join(missing) +
                f". Place the TTF files in '{fonts_dir}' or update 'font_dir' in PDF_CONFIG."
            )
        for name, path in font_map.items():
            pdfmetrics.registerFont(TTFont(f"Poppins-{name}", str(path)))
        pdfmetrics.registerFontFamily(
            'Poppins',
            normal='Poppins-Regular',
            bold='Poppins-Bold',
            italic='Poppins-Regular',
            boldItalic='Poppins-Semibold'
        )
        self.fonts = {
            'regular': 'Poppins-Regular',
            'medium': 'Poppins-Medium',
            'semibold': 'Poppins-Semibold',
            'bold': 'Poppins-Bold'
        }
        
    def _setup_custom_styles(self):
        """Setup custom PDF styles for security reports"""
        normal_style = self.styles['Normal']
        normal_style.fontName = self.fonts['regular']
        normal_style.fontSize = BODY_FONT_SIZE
        normal_style.leading = BODY_FONT_SIZE + (BASE_UNIT // 2)
        normal_style.textColor = self.palette['text_primary']
        normal_style.spaceAfter = BASE_UNIT

        self.styles.add(ParagraphStyle(
            name='BodyMuted',
            parent=normal_style,
            textColor=self.palette['text_muted']
        ))

        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=normal_style,
            fontName=self.fonts['bold'],
            fontSize=TITLE_FONT_SIZE,
            leading=TITLE_FONT_SIZE + BASE_UNIT,
            textColor=self.palette['accent_dark'],
            alignment=TA_CENTER,
            spaceBefore=BASE_UNIT * 6,
            spaceAfter=BASE_UNIT * 4
        ))

        self.styles.add(ParagraphStyle(
            name='IntroHeading',
            parent=normal_style,
            fontName=self.fonts['semibold'],
            fontSize=SUBSECTION_FONT_SIZE,
            leading=SUBSECTION_FONT_SIZE + BASE_UNIT,
            alignment=TA_CENTER,
            textColor=self.palette['accent'],
            spaceBefore=BASE_UNIT,
            spaceAfter=BASE_UNIT
        ))

        self.styles.add(ParagraphStyle(
            name='IntroText',
            parent=normal_style,
            fontName=self.fonts['regular'],
            alignment=TA_CENTER,
            textColor=self.palette['text_muted'],
            leading=BODY_FONT_SIZE + BASE_UNIT,
            spaceAfter=BASE_UNIT * 3
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=normal_style,
            fontName=self.fonts['semibold'],
            fontSize=SECTION_FONT_SIZE,
            leading=SECTION_FONT_SIZE + BASE_UNIT,
            textColor=self.palette['accent'],
            backColor=self.palette['accent_soft'],
            spaceBefore=BASE_UNIT * 3,
            spaceAfter=BASE_UNIT * 2,
            leftIndent=0,
            borderPadding=BASE_UNIT,
            borderColor=self.palette['accent_soft'],
            borderWidth=0
        ))

        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=normal_style,
            fontName=self.fonts['medium'],
            fontSize=SUBSECTION_FONT_SIZE,
            leading=SUBSECTION_FONT_SIZE + (BASE_UNIT // 2),
            textColor=self.palette['text_primary'],
            spaceBefore=BASE_UNIT * 2,
            spaceAfter=BASE_UNIT
        ))

        self.styles.add(ParagraphStyle(
            name='SummaryBox',
            parent=normal_style,
            fontName=self.fonts['medium'],
            backColor=self.palette['background_muted'],
            textColor=self.palette['text_primary'],
            borderColor=self.palette['accent_soft'],
            borderWidth=1,
            borderPadding=BASE_UNIT * 2,
            spaceBefore=BASE_UNIT,
            spaceAfter=BASE_UNIT * 2
        ))

        self.styles.add(ParagraphStyle(
            name='AlertStyle',
            parent=normal_style,
            fontName=self.fonts['semibold'],
            textColor=self.palette['danger'],
            backColor=colors.HexColor('#FEF2F2'),
            borderColor=self.palette['danger'],
            borderWidth=1,
            borderPadding=BASE_UNIT * 2,
            spaceBefore=BASE_UNIT,
            spaceAfter=BASE_UNIT * 2
        ))

        self.styles.add(ParagraphStyle(
            name='CodeStyle',
            parent=normal_style,
            fontName='Courier',
            fontSize=BODY_FONT_SIZE - 2,
            leading=(BODY_FONT_SIZE - 2) + (BASE_UNIT // 2),
            backColor=colors.HexColor('#0F172A'),
            textColor=colors.whitesmoke,
            borderPadding=BASE_UNIT,
            spaceBefore=BASE_UNIT,
            spaceAfter=BASE_UNIT * 2
        ))

        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=normal_style,
            fontName=self.fonts['semibold'],
            fontSize=BODY_FONT_SIZE - 1,
            leading=BODY_FONT_SIZE + (BASE_UNIT // 2),
            alignment=TA_CENTER,
            textColor=colors.white,
            spaceBefore=0,
            spaceAfter=0
        ))

        self.styles.add(ParagraphStyle(
            name='TableCell',
            parent=normal_style,
            fontName=self.fonts['regular'],
            fontSize=BODY_FONT_SIZE - 2,
            leading=(BODY_FONT_SIZE - 2) + (BASE_UNIT // 2),
            textColor=self.palette['text_primary'],
            spaceBefore=0,
            spaceAfter=BASE_UNIT // 2
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
        story.append(Paragraph(
            f"{config.get('emoji', '📊')} {config.get('name', 'Security Report')}",
            self.styles['CustomTitle']
        ))

        story.append(Paragraph("AISOC MCP Security Operations Center", self.styles['IntroHeading']))

        intro_text = (
            "AISOC MCP menghadirkan rangkuman situasi keamanan terbaru dalam satu laporan ringkas. "
            "Gunakan temuan dan rekomendasi di dalamnya sebagai panduan tindakan cepat untuk menjaga kelangsungan operasional Anda."
        )
        story.append(Paragraph(intro_text, self.styles['IntroText']))

        meta_text = (
            f"<b>Periode:</b> {report_data.get('period', 'Unknown')}<br/>"
            f"<b>Generated:</b> {datetime.now().strftime('%d %B %Y, %H:%M:%S WIB')}"
        )
        story.append(Paragraph(meta_text, self.styles['BodyMuted']))

        ai_analysis = report_data.get('ai_analysis', {})
        risk_level = ai_analysis.get('risk_level') or 'Unknown'
        risk_color = self._get_risk_color(risk_level)
        risk_backdrop = colors.Color(risk_color.red, risk_color.green, risk_color.blue, alpha=0.12)

        risk_style = ParagraphStyle(
            'RiskBadge',
            parent=self.styles['SubsectionHeader'],
            alignment=TA_CENTER,
            fontName=self.fonts['semibold'],
            textColor=risk_color if risk_level not in {'Critical', 'High'} else colors.white,
            backColor=risk_color if risk_level in {'Critical', 'High'} else risk_backdrop,
            borderPadding=BASE_UNIT * 2,
            leading=SUBSECTION_FONT_SIZE + BASE_UNIT,
            spaceBefore=BASE_UNIT * 4,
            spaceAfter=BASE_UNIT * 4
        )
        story.append(Paragraph(f"Risk Level: {risk_level}", risk_style))

        story.append(PageBreak())
    
    def _add_executive_summary(self, story: List, report_data: Dict[str, Any]):
        """Add executive summary section"""
        story.append(Paragraph("📋 Executive Summary", self.styles['SectionHeader']))
        
        statistics = report_data.get('statistics', {})
        summary_stats = statistics.get('summary', {})
        ai_analysis = report_data.get('ai_analysis', {})

        total_events = self._safe_int(summary_stats.get('total_events'))
        critical_events = self._safe_int(statistics.get('critical_events'))
        high_events = self._safe_int(statistics.get('high_events'))
        agent_status = report_data.get('agent_status', {})
        active_agents = self._safe_int(agent_status.get('active_agents'))
        total_agents = self._safe_int(agent_status.get('total_agents'))
        risk_level = ai_analysis.get('risk_level') or 'Unknown'
        risk_score_raw = ai_analysis.get('risk_score')

        if risk_score_raw in (None, '', 'N/A'):
            risk_score_display = 'N/A'
        else:
            try:
                risk_score_display = f"{float(risk_score_raw):.1f}"
            except (TypeError, ValueError):
                risk_score_display = str(risk_score_raw)
        
        # Key metrics summary
        summary_text = f"""
        <b>Ringkasan Periode {report_data.get('period', 'Unknown')}:</b><br/><br/>
        
        • <b>Total Security Events:</b> {total_events:,} events<br/>
        • <b>Critical Events (Level 7):</b> {critical_events} events<br/>
        • <b>High Priority Events (Level 6):</b> {high_events} events<br/>
        • <b>Active Agents:</b> {active_agents} dari {total_agents} agents<br/>
        • <b>Risk Score:</b> {risk_score_display}/10<br/>
        • <b>Risk Level:</b> {risk_level}<br/><br/>
        
        <b>Status Keamanan:</b> {self._get_security_status_text(risk_level)}
        """
        
        story.append(Paragraph(summary_text, self.styles['SummaryBox']))
        story.append(self._spacer(3))
    
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
        total_events = self._safe_int(summary.get('total_events'))
        unique_agents = self._safe_int(summary.get('unique_agents'))
        unique_rules = self._safe_int(summary.get('unique_rules'))
        avg_severity = self._safe_float(summary.get('avg_severity'))
        max_severity = self._safe_int(summary.get('max_severity'))
        critical_events = self._safe_int(statistics.get('critical_events'))
        high_events = self._safe_int(statistics.get('high_events'))
        medium_events = self._safe_int(statistics.get('medium_events'))
        low_events = self._safe_int(statistics.get('low_events'))
        metrics_data.extend([
            ['Total Events', f"{total_events:,}", 'Total security events in period'],
            ['Unique Agents', f"{unique_agents}", 'Number of different agents reporting'],
            ['Unique Rules', f"{unique_rules}", 'Number of different security rules triggered'],
            ['Average Severity', f"{avg_severity:.1f}", 'Average severity level of events'],
            ['Max Severity', f"{max_severity}", 'Highest severity level detected'],
            ['Critical Events', f"{critical_events}", 'Level 7 - Immediate attention required'],
            ['High Events', f"{high_events}", 'Level 6 - High priority events'],
            ['Medium Events', f"{medium_events}", 'Level 2-3 - Medium priority events'],
            ['Low Events', f"{low_events}", 'Level 0-1 - Low priority events']
        ])
        
        metrics_table = Table(metrics_data, colWidths=col_widths, repeatRows=1)
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.palette['accent']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self.fonts['semibold']),
            ('FONTSIZE', (0, 0), (-1, 0), BODY_FONT_SIZE),
            ('BOTTOMPADDING', (0, 0), (-1, 0), BASE_UNIT * 2),
            ('TOPPADDING', (0, 0), (-1, 0), BASE_UNIT * 2),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.palette['text_primary']),
            ('FONTNAME', (0, 1), (-1, -1), self.fonts['regular']),
            ('FONTSIZE', (0, 1), (-1, -1), BODY_FONT_SIZE - 1),
            ('LEFTPADDING', (0, 0), (-1, -1), BASE_UNIT * 1.5),
            ('RIGHTPADDING', (0, 0), (-1, -1), BASE_UNIT * 1.5),
            ('TOPPADDING', (0, 1), (-1, -1), BASE_UNIT * 1.5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), BASE_UNIT * 1.5),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#E2E8F0')),
        ]))
        
        story.append(metrics_table)
        story.append(self._spacer(3))
        
        # Add severity distribution chart info
        severity_dist = statistics.get('severity_distribution', {})
        if severity_dist:
            story.append(Paragraph("Distribusi Tingkat Keamanan:", self.styles['SubsectionHeader']))
            
            dist_text = ""
            for level, count in sorted(severity_dist.items(), key=lambda x: int(x[0]), reverse=True):
                level_name = self._get_severity_name(int(level))
                dist_text += f"• Level {level} ({level_name}): {count} events<br/>"
            
            story.append(Paragraph(dist_text, self.styles['Normal']))
            story.append(self._spacer(2))
    
    def _add_security_events_analysis(self, story: List, report_data: Dict[str, Any]):
        """Add security events analysis section"""
        story.append(Paragraph("🔍 Security Events Analysis", self.styles['SectionHeader']))
        
        events = report_data.get('security_events', [])
        
        if not events:
            story.append(Paragraph("Tidak ada security events dalam periode ini.", self.styles['Normal']))
            return
        
        story.append(Paragraph(f"All Security Events - {len(events)} Grouped Rules (berdasarkan prioritas):", 
                             self.styles['SubsectionHeader']))
        
        headers = ['Waktu', 'Level', 'Rule ID', 'Description', 'Agent', 'Jumlah', 'Location']

        base_widths = [80, 40, 65, 210, 110, 50, 105]
        page_width, _ = A4
        margin_left = self.config['margins']['left']
        margin_right = self.config['margins']['right']
        available_width = page_width - (margin_left + margin_right)
        scale = min(1.0, available_width / sum(base_widths))
        col_widths = [w * scale for w in base_widths]

        table_rows = [[Paragraph(header, self.styles['TableHeader']) for header in headers]]

        for event in events:
            # GUNAKAN DATA DARI REPRESENTATIVE_EVENT
            rep_event = event.get('representative_event', {})
            
            timestamp = rep_event.get('timestamp', event.get('latest_occurrence', ''))
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp = dt.strftime('%d/%m %H:%M')
                except:
                    timestamp = timestamp[:16]  # Fallback
            timestamp_display = ''
            if timestamp:
                if 'T' in timestamp:
                    ts = timestamp.replace('T', ' ')
                else:
                    ts = timestamp
                if ' ' in ts:
                    date_part, time_part = ts.split(' ', 1)
                    timestamp_display = f"{date_part}<br/>{time_part}"
                else:
                    timestamp_display = timestamp
            else:
                timestamp_display = 'N/A'
                    
            # KOLOM JUMLAH TERPISAH
            count = event.get('count', 1)
            description_text = self._clean_text_for_pdf(event.get('rule_description', 'N/A'))
            agent_text = self._clean_text_for_pdf(rep_event.get('agent_name', 'N/A'))
            location_text = self._clean_text_for_pdf(rep_event.get('location', 'N/A'))

            description_text = description_text.replace('/', '/&#8203;')
            agent_text = agent_text.replace('-', '-&#8203;').replace('/', '/&#8203;')
            location_text = location_text.replace('-', '-&#8203;').replace('/', '/&#8203;')

            table_rows.append([
                Paragraph(timestamp_display or 'N/A', self.styles['TableCell']),
                Paragraph(self._clean_text_for_pdf(event.get('rule_level', 'N/A')), self.styles['TableCell']),
                Paragraph(self._clean_text_for_pdf(event.get('rule_id', 'N/A')), self.styles['TableCell']),
                Paragraph(description_text.replace(' - ', '<br/>- '), self.styles['TableCell']),
                Paragraph(agent_text, self.styles['TableCell']),
                Paragraph(str(count), self.styles['TableCell']),
                Paragraph(location_text, self.styles['TableCell'])
            ])

        events_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
        events_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.palette['danger']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self.fonts['semibold']),
            ('FONTSIZE', (0, 0), (-1, 0), BODY_FONT_SIZE - 1),
            ('BOTTOMPADDING', (0, 0), (-1, 0), BASE_UNIT * 1.5),
            ('TOPPADDING', (0, 0), (-1, 0), BASE_UNIT * 1.5),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FEF2F2')),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.palette['text_primary']),
            ('FONTNAME', (0, 1), (-1, -1), self.fonts['regular']),
            ('FONTSIZE', (0, 1), (-1, -1), BODY_FONT_SIZE - 2),
            ('LEFTPADDING', (0, 0), (-1, -1), BASE_UNIT),
            ('RIGHTPADDING', (0, 0), (-1, -1), BASE_UNIT),
            ('TOPPADDING', (0, 1), (-1, -1), BASE_UNIT),
            ('BOTTOMPADDING', (0, 1), (-1, -1), BASE_UNIT),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#FCA5A5')),
            ('WORDWRAP', (0, 0), (-1, -1), 'CJK'),
            ('SPLITLONGWORDS', (0, 1), (-1, -1), True),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ('ALIGN', (5, 1), (5, -1), 'CENTER'),
        ]))
        
        story.append(events_table)
        story.append(self._spacer(3))
    
    def _add_agent_status_section(self, story: List, report_data: Dict[str, Any]):
        """Add agent status section"""
        story.append(Paragraph("🖥️ Agent Status Overview", self.styles['SectionHeader']))
        
        agent_status = report_data.get('agent_status', {})
        agents_detail = agent_status.get('agents_detail', [])
        total_agents = self._safe_int(agent_status.get('total_agents'))
        active_agents = self._safe_int(agent_status.get('active_agents'))
        inactive_agents = max(total_agents - active_agents, 0)
        
        # Summary
        summary_text = f"""
        <b>Agent Summary:</b><br/>
        • Total Agents: {total_agents}<br/>
        • Active Agents: {active_agents}<br/>
        • Inactive Agents: {inactive_agents}<br/>
        """
        story.append(Paragraph(summary_text, self.styles['Normal']))
        story.append(self._spacer(1.5))
        
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
                    str(self._safe_int(agent.get('event_count'))),
                    f"{self._safe_float(agent.get('avg_severity')):.1f}",
                    str(self._safe_int(agent.get('max_severity'))),
                    self._truncate_text(last_event, 15)
                ])
            
            agents_table = Table(agents_data, colWidths=col_widths, repeatRows=1)
            agents_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.palette['success']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), self.fonts['semibold']),
                ('FONTSIZE', (0, 0), (-1, 0), BODY_FONT_SIZE - 1),
                ('BOTTOMPADDING', (0, 0), (-1, 0), BASE_UNIT * 1.5),
                ('TOPPADDING', (0, 0), (-1, 0), BASE_UNIT * 1.5),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECFDF5')),
                ('TEXTCOLOR', (0, 1), (-1, -1), self.palette['text_primary']),
                ('FONTNAME', (0, 1), (-1, -1), self.fonts['regular']),
                ('FONTSIZE', (0, 1), (-1, -1), BODY_FONT_SIZE - 2),
                ('LEFTPADDING', (0, 0), (-1, -1), BASE_UNIT),
                ('RIGHTPADDING', (0, 0), (-1, -1), BASE_UNIT),
                ('TOPPADDING', (0, 1), (-1, -1), BASE_UNIT),
                ('BOTTOMPADDING', (0, 1), (-1, -1), BASE_UNIT),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#A7F3D0')),
            ]))
            
            story.append(agents_table)
        
        story.append(self._spacer(3))
    
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
        
        # AI Analysis content - Remove thinking tags and render structured segments
        story.append(Paragraph("Analisis AI:", self.styles['SubsectionHeader']))
        ai_text = ai_analysis.get('ai_analysis', '')
        ai_text = self._remove_thinking_tags(ai_text)

        segments = self._split_markdown_tables(ai_text)

        for segment in segments:
            if segment['type'] == 'text':
                formatted_chunk = self._format_markdown_for_pdf(segment['content'])
                if formatted_chunk.strip():
                    try:
                        story.append(Paragraph(f"<para>{formatted_chunk}</para>", self.styles['Normal']))
                    except Exception:
                        logger.error("Markdown formatting failed; aborting PDF generation", exc_info=True)
                        raise
            elif segment['type'] == 'table':
                table = self._build_markdown_table(segment['data'])
                if table is not None:
                    story.append(table)
                    story.append(self._spacer(2))

        story.append(self._spacer(2))
        
        # Priority actions
        priority_actions = ai_analysis.get('priority_actions', [])
        if priority_actions:
            story.append(Paragraph("🚨 Priority Actions:", self.styles['SubsectionHeader']))
            story.append(self._spacer(0.75))
            
            actions_text = ""
            for i, action in enumerate(priority_actions, 1):
                # Clean and format each action
                clean_action = self._clean_text_for_pdf(action)
                clean_action = clean_action.replace('**', '')
                actions_text += f"{i}. {clean_action}<br/>"
            
            story.append(Paragraph(actions_text, self.styles['AlertStyle']))
        
        story.append(self._spacer(3))
    
    def _add_trends_analysis(self, story: List, report_data: Dict[str, Any]):
        """Add trends analysis section"""
        trends = report_data.get('trends', {})
        
        if not trends or 'analysis' not in trends:
            return
            
        story.append(Paragraph("📈 Trend Analysis", self.styles['SectionHeader']))
        
        analysis = trends.get('analysis', {})
        total_events_change = self._safe_float(analysis.get('total_events_change'))
        critical_events_change = self._safe_int(analysis.get('critical_events_change'))
        high_events_change = self._safe_int(analysis.get('high_events_change'))
        trend_direction = (analysis.get('trend_direction') or 'stable').title()
        
        trend_text = f"""
        <b>Trend Comparison dengan Periode Sebelumnya:</b><br/><br/>
        • Total Events Change: {total_events_change:.1f}%<br/>
        • Trend Direction: {trend_direction}<br/>
        • Critical Events Change: {critical_events_change:+d}<br/>
        • High Events Change: {high_events_change:+d}<br/>
        """
        
        story.append(Paragraph(trend_text, self.styles['Normal']))
        story.append(self._spacer(3))
    
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
            sanitized = self._clean_text_for_pdf(rec).replace('**', '')
            rec_text += f"{i}. {sanitized}<br/>"
        
        story.append(Paragraph(rec_text, self.styles['Normal']))
        story.append(self._spacer(3))
    
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
        story.append(self._spacer(2))
        
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
                ('BACKGROUND', (0, 0), (-1, 0), self.palette['accent_dark']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), self.fonts['semibold']),
                ('FONTSIZE', (0, 0), (-1, 0), BODY_FONT_SIZE - 1),
                ('BOTTOMPADDING', (0, 0), (-1, 0), BASE_UNIT * 1.5),
                ('TOPPADDING', (0, 0), (-1, 0), BASE_UNIT * 1.5),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#EEF2FF')),
                ('TEXTCOLOR', (0, 1), (-1, -1), self.palette['text_primary']),
                ('FONTNAME', (0, 1), (-1, -1), self.fonts['regular']),
                ('FONTSIZE', (0, 1), (-1, -1), BODY_FONT_SIZE - 2),
                ('LEFTPADDING', (0, 0), (-1, -1), BASE_UNIT * 1.5),
                ('RIGHTPADDING', (0, 0), (-1, -1), BASE_UNIT * 1.5),
                ('TOPPADDING', (0, 1), (-1, -1), BASE_UNIT * 1.5),
                ('BOTTOMPADDING', (0, 1), (-1, -1), BASE_UNIT * 1.5),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#C7D2FE')),
            ]))
            
            story.append(groups_table)
    
    # Helper methods
    def _safe_int(self, value: Any, default: int = 0) -> int:
        """Convert value to int safely, falling back to default."""
        try:
            if value is None:
                return default
            if isinstance(value, str):
                value = value.strip()
                if value == '' or value.lower() in {'nan', 'none'}:
                    return default
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Convert value to float safely, falling back to default."""
        try:
            if value is None:
                return default
            if isinstance(value, str):
                value = value.strip()
                if value == '' or value.lower() in {'nan', 'none'}:
                    return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _get_risk_color(self, risk_level: str):
        """Get accent color for risk level."""
        color_map = {
            'Critical': colors.HexColor('#B91C1C'),
            'High': colors.HexColor('#D97706'),
            'Medium': colors.HexColor('#2563EB'),
            'Low': colors.HexColor('#047857'),
        }
        return color_map.get(risk_level, self.palette['text_muted'])
    
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

    def _split_markdown_tables(self, text: str) -> List[Dict[str, Any]]:
        """Split markdown text into narrative and table segments."""
        if not text:
            return [{'type': 'text', 'content': ''}]

        import re

        segments: List[Dict[str, Any]] = []
        table_pattern = re.compile(r'(?:^\s*\|.*\|\s*$\n?){2,}', re.MULTILINE)

        last_end = 0
        for match in table_pattern.finditer(text):
            before = text[last_end:match.start()]
            if before.strip():
                segments.append({'type': 'text', 'content': before})

            block = match.group(0)
            lines = [line for line in block.splitlines() if line.strip()]
            table_data = self._parse_markdown_table(lines)

            if table_data:
                segments.append({'type': 'table', 'data': table_data})
                last_end = match.end()
            else:
                # Treat as plain text if parsing failed
                segments.append({'type': 'text', 'content': block})
                last_end = match.end()

        trailing = text[last_end:]
        if trailing.strip():
            segments.append({'type': 'text', 'content': trailing})

        return segments or [{'type': 'text', 'content': text}]

    def _parse_markdown_table(self, lines: List[str]) -> Optional[List[List[str]]]:
        """Parse markdown table lines into row data."""
        import re

        cleaned = [line.strip() for line in lines if line.strip()]
        if len(cleaned) < 2:
            return None

        header_cells = [cell.strip() for cell in cleaned[0].strip('|').split('|')]
        if not header_cells:
            return None

        rows: List[List[str]] = []
        for idx, raw_line in enumerate(cleaned[1:], start=1):
            stripped = raw_line.strip('|').strip()
            if not stripped:
                continue

            # Skip header separator rows like |-----|:----|
            separator_candidate = stripped.replace('|', '').replace(' ', '')
            if separator_candidate and set(separator_candidate) <= {'-', ':'}:
                continue

            cells = [cell.strip() for cell in raw_line.strip('|').split('|')]
            if not any(cells):
                continue
            if len(cells) < len(header_cells):
                cells.extend([''] * (len(header_cells) - len(cells)))
            rows.append(cells[:len(header_cells)])

        if not rows:
            return None

        return [header_cells] + rows

    def _build_markdown_table(self, data: List[List[str]]) -> Optional[Table]:
        """Build a styled ReportLab table from markdown data."""
        if not data or len(data) < 2:
            return None

        col_count = max(len(row) for row in data)
        page_width, _ = A4
        available_width = page_width - (self.config['margins']['left'] + self.config['margins']['right'])
        col_widths = [available_width / col_count] * col_count

        table_rows = []
        for row_index, row in enumerate(data):
            style_name = 'TableHeader' if row_index == 0 else 'TableCell'
            styled_row = []
            for cell in row:
                clean_cell = self._clean_text_for_pdf(cell or '-', preserve_html=True)
                clean_cell = clean_cell.replace('<', '&lt;').replace('>', '&gt;').replace('**', '')
                styled_row.append(Paragraph(clean_cell or '-', self.styles[style_name]))
            table_rows.append(styled_row)

        table = Table(table_rows, colWidths=col_widths, repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.palette['accent']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.palette['text_primary']),
            ('LEFTPADDING', (0, 0), (-1, -1), BASE_UNIT * 1.5),
            ('RIGHTPADDING', (0, 0), (-1, -1), BASE_UNIT * 1.5),
            ('TOPPADDING', (0, 0), (-1, 0), BASE_UNIT * 1.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), BASE_UNIT * 1.5),
            ('TOPPADDING', (0, 1), (-1, -1), BASE_UNIT),
            ('BOTTOMPADDING', (0, 1), (-1, -1), BASE_UNIT),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#CBD5F5')),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('WORDWRAP', (0, 0), (-1, -1), 'CJK'),
            ('SPLITLONGWORDS', (0, 0), (-1, -1), True),
        ]))

        return table
    
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

        # Escape HTML special characters first so ReportLab won't misinterpret raw content
        text = (
            text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;')
        )

        # Convert markdown headers to HTML-like formatting (from largest to smallest)
        # Remove empty heading markers like "###" or "##"
        text = re.sub(r'^\s*#{1,6}\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*#####\s+(.*?)$', r'<i><u>\1</u></i>', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*####\s+(.*?)$', r'<b><u>\1</u></b>', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*###\s+(.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*##\s+(.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*#\s+(.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)

        # Handle inline code first by stashing placeholders so later formatting doesn't interfere
        code_placeholders = {}

        def _store_code(match):
            key = f"__CODE_{len(code_placeholders)}__"
            code_placeholders[key] = f"<font name=\"Courier\">{match.group(1)}</font>"
            return key

        text = re.sub(r'`([^`]+)`', _store_code, text)

        # Handle repeated characters (decorative lines)
        text = re.sub(r'^\s*I{10,}\s*$', r'<br/>▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌<br/>', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*([=\-_#\*])\1{10,}\s*$', r'<br/>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━<br/>', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*---+\s*$', r'<br/>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━<br/>', text, flags=re.MULTILINE)

        # Convert markdown bold and italics (restrict italics to standalone markers to avoid code interference)
        text = re.sub(r'\*{2,}(.*?)\*{2,}', r'<b>\1</b>', text)
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)
        text = re.sub(r'(?<!\S)\*(\S.*?\S)\*(?!\S)', r'<i>\1</i>', text)
        text = re.sub(r'(?<!\S)_(\S.*?\S)_(?!\S)', r'<i>\1</i>', text)

        # Convert bullet and numbered lists
        text = re.sub(r'^\s*[\-\*\+]\s+(.*?)$', r'• \1', text, flags=re.MULTILINE)
        text = re.sub(r'^(\d+)\. (.*?)$', r'\1. \2', text, flags=re.MULTILINE)

        # Convert standalone emphasis markers (used as separators)
        text = re.sub(r'^\*\*\s*$', r'<b>※</b>', text, flags=re.MULTILINE)

        # Restore code placeholders
        for key, value in code_placeholders.items():
            text = text.replace(key, value)

        # Clean up repeated bold/italic tags caused by overlapping markup
        text = re.sub(r'<b>\s*<b>', '<b>', text)
        text = re.sub(r'</b>\s*</b>', '</b>', text)
        text = re.sub(r'<i>\s*<i>', '<i>', text)
        text = re.sub(r'</i>\s*</i>', '</i>', text)

        # Replace newlines with HTML breaks and collapse excessive spacing
        text = text.replace('\n', '<br/>')
        text = re.sub(r'<br/>\s*<br/>', '<br/><br/>', text)
        text = re.sub(r'(<br/>){3,}', '<br/><br/>', text)

        text = text.replace('**', '')

        return text
    
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
