#!/usr/bin/env python3
"""
AISOC MCP - PDF Generator using ReportLab
Direct PDF generation without HTML conversion

Author: AISOC MCP Team
Date: September 25, 2025
Version: 1.0.0
"""

import os
import sys
from pathlib import Path
import logging
from datetime import datetime
import re
import markdown
from io import BytesIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.lib.colors import HexColor, black, white, blue, red, green
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
except ImportError as e:
    logger.error(f"ReportLab not installed. Please run: pip install reportlab")
    logger.error(f"Error: {e}")
    sys.exit(1)

class PDFCanvas(canvas.Canvas):
    """Custom canvas for headers and footers"""
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
        
    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()
        
    def save(self):
        page_count = len(self.pages)
        for page_num, page in enumerate(self.pages, 1):
            self.__dict__.update(page)
            self.draw_page_decorations(page_num, page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
        
    def draw_page_decorations(self, page_num, page_count):
        """Draw headers and footers"""
        self.setFont("Helvetica", 9)
        
        # Header
        self.setFillColor(HexColor("#1e40af"))
        self.drawString(1*inch, A4[1] - 0.75*inch, "AISOC MCP - AI Security Operations Center")
        
        # Footer
        self.setFillColor(black)
        self.drawRightString(A4[0] - 1*inch, 0.75*inch, f"Page {page_num} of {page_count}")
        self.drawString(1*inch, 0.75*inch, f"Generated on {datetime.now().strftime('%B %d, %Y')}")

class ReportLabPDFGenerator:
    """Generate PDF using ReportLab"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.readme_path = project_root / "README.md"
        self.output_dir = project_root / "docs" / "pdf"
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize styles
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        
    def _create_custom_styles(self):
        """Create custom paragraph styles"""
        
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            spaceBefore=20,
            textColor=HexColor("#1e40af"),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Heading 1
        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=20,
            spaceAfter=20,
            spaceBefore=30,
            textColor=HexColor("#1e40af"),
            fontName='Helvetica-Bold',
            borderWidth=1,
            borderColor=HexColor("#3b82f6"),
            borderPadding=(5, 5, 10, 5),
            backColor=HexColor("#f8fafc")
        ))
        
        # Heading 2  
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=15,
            spaceBefore=20,
            textColor=HexColor("#374151"),
            fontName='Helvetica-Bold',
            leftIndent=10,
            borderWidth=0,
            borderColor=HexColor("#3b82f6"),
            borderPadding=(0, 0, 0, 5)
        ))
        
        # Heading 3
        self.styles.add(ParagraphStyle(
            name='CustomHeading3',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=HexColor("#4b5563"),
            fontName='Helvetica-Bold'
        ))
        
        # Code style
        self.styles.add(ParagraphStyle(
            name='Code',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName='Courier',
            backColor=HexColor("#f3f4f6"),
            borderWidth=1,
            borderColor=HexColor("#d1d5db"),
            borderPadding=(10, 10, 10, 10),
            spaceAfter=15,
            spaceBefore=10
        ))
        
        # Note style
        self.styles.add(ParagraphStyle(
            name='Note',
            parent=self.styles['Normal'],
            fontSize=10,
            backColor=HexColor("#e0f2fe"),
            borderWidth=1,
            borderColor=HexColor("#0288d1"),
            borderPadding=(10, 10, 10, 10),
            spaceAfter=15,
            spaceBefore=10
        ))
        
        # Warning style
        self.styles.add(ParagraphStyle(
            name='Warning',
            parent=self.styles['Normal'],
            fontSize=10,
            backColor=HexColor("#fff3cd"),
            borderWidth=1,
            borderColor=HexColor("#ffc107"),
            borderPadding=(10, 10, 10, 10),
            spaceAfter=15,
            spaceBefore=10
        ))
    
    def _preprocess_markdown(self, content: str) -> str:
        """Preprocess markdown content for PDF"""
        
        # Remove badges
        badge_patterns = [
            r'\[!\[.*?\]\(.*?\)\]\(.*?\)',
        ]
        
        for pattern in badge_patterns:
            content = re.sub(pattern, '', content)
        
        # Convert mermaid to text
        content = re.sub(
            r'```mermaid\n.*?\n```', 
            '[System Architecture Diagram - See web version for interactive diagram]', 
            content, 
            flags=re.DOTALL
        )
        
        # Clean up extra whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content
    
    def _parse_markdown_to_elements(self, content: str):
        """Parse markdown content to ReportLab elements"""
        elements = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
                
            # Headers
            if line.startswith('# '):
                if '🛡️ AISOC MCP' in line:
                    # Main title
                    title_text = line[2:].strip()
                    elements.append(Paragraph(title_text, self.styles['CustomTitle']))
                    elements.append(Spacer(1, 20))
                else:
                    elements.append(PageBreak())
                    elements.append(Paragraph(line[2:], self.styles['CustomHeading1']))
                    elements.append(Spacer(1, 15))
                    
            elif line.startswith('## '):
                elements.append(Paragraph(line[3:], self.styles['CustomHeading2']))
                elements.append(Spacer(1, 10))
                
            elif line.startswith('### '):
                elements.append(Paragraph(line[4:], self.styles['CustomHeading3']))
                elements.append(Spacer(1, 8))
                
            # Code blocks
            elif line.startswith('```'):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                
                if code_lines:
                    code_text = '\\n'.join(code_lines)
                    elements.append(Paragraph(code_text, self.styles['Code']))
                    elements.append(Spacer(1, 10))
                    
            # Tables
            elif '|' in line and line.count('|') >= 2:
                table_data = []
                
                # Parse table
                while i < len(lines) and '|' in lines[i] and lines[i].strip():
                    row = lines[i].strip()
                    if row.startswith('|') and row.endswith('|'):
                        cells = [cell.strip() for cell in row[1:-1].split('|')]
                        if not all(cell in ['', '---', '----', '-----'] or cell.startswith('--') for cell in cells):
                            table_data.append(cells)
                    i += 1
                
                if table_data:
                    # Create table
                    table = Table(table_data, hAlign='LEFT')
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), HexColor("#f3f4f6")),
                        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#374151")),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('TOPPADDING', (0, 0), (-1, 0), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('GRID', (0, 0), (-1, -1), 1, HexColor("#d1d5db")),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    elements.append(table)
                    elements.append(Spacer(1, 15))
                continue
                
            # Lists
            elif line.startswith('- ') or line.startswith('* '):
                list_items = []
                while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                    item_text = lines[i].strip()[2:]
                    list_items.append(f"• {item_text}")
                    i += 1
                
                for item in list_items:
                    elements.append(Paragraph(item, self.styles['Normal']))
                elements.append(Spacer(1, 10))
                continue
                
            # Regular paragraphs
            else:
                # Handle special formatting
                if line.startswith('**') and line.endswith('**'):
                    line = f"<b>{line[2:-2]}</b>"
                elif '**' in line:
                    line = re.sub(r'\\*\\*(.*?)\\*\\*', r'<b>\\1</b>', line)
                
                if line.startswith('*') and line.endswith('*'):
                    line = f"<i>{line[1:-1]}</i>"
                elif '*' in line:
                    line = re.sub(r'\\*(.*?)\\*', r'<i>\\1</i>', line)
                
                # Handle code inline
                line = re.sub(r'`(.*?)`', r'<font name="Courier">\\1</font>', line)
                
                elements.append(Paragraph(line, self.styles['Normal']))
                elements.append(Spacer(1, 8))
            
            i += 1
        
        return elements
    
    def _create_cover_page(self):
        """Create cover page elements"""
        elements = []
        
        # Title
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph("🛡️ AISOC MCP", self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.5*inch))
        
        # Subtitle
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=self.styles['Normal'],
            fontSize=18,
            textColor=HexColor("#374151"),
            alignment=TA_CENTER,
            spaceAfter=30
        )
        elements.append(Paragraph("AI Security Operations Center", subtitle_style))
        elements.append(Paragraph("Model Context Protocol Platform", subtitle_style))
        elements.append(Spacer(1, 0.5*inch))
        
        # Description box
        desc_style = ParagraphStyle(
            'Description',
            parent=self.styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            backColor=HexColor("#f8fafc"),
            borderWidth=1,
            borderColor=HexColor("#e2e8f0"),
            borderPadding=(20, 20, 20, 20),
            spaceAfter=30
        )
        
        desc_text = """
        <b>Complete User Guide & Documentation</b><br/><br/>
        Comprehensive guide for installation, configuration, and usage of AISOC MCP platform.<br/>
        From zero to hero - everything you need to deploy and operate your AI-powered Security Operations Center.
        """
        elements.append(Paragraph(desc_text, desc_style))
        elements.append(Spacer(1, 1*inch))
        
        # Meta information
        meta_style = ParagraphStyle(
            'Meta',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=HexColor("#6b7280")
        )
        
        meta_text = f"""
        <b>Version:</b> 1.0.0<br/>
        <b>Generated:</b> {datetime.now().strftime('%B %d, %Y')}<br/>
        <b>Repository:</b> github.com/urtir/AISOC-MCP<br/><br/>
        🛡️ Made with ❤️ by AISOC MCP Team
        """
        elements.append(Paragraph(meta_text, meta_style))
        elements.append(PageBreak())
        
        return elements
    
    def generate_pdf(self) -> Path:
        """Generate PDF document"""
        try:
            logger.info("🚀 Starting PDF generation with ReportLab...")
            
            if not self.readme_path.exists():
                raise FileNotFoundError(f"README.md not found at {self.readme_path}")
            
            # Read and preprocess README
            logger.info("📖 Reading and preprocessing README...")
            with open(self.readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            content = self._preprocess_markdown(content)
            
            # Create PDF
            output_path = self.output_dir / f"AISOC_MCP_Complete_Guide_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            logger.info("📄 Creating PDF document...")
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=100,
                bottomMargin=100,
                canvasmaker=PDFCanvas
            )
            
            # Build elements
            elements = []
            
            # Add cover page
            elements.extend(self._create_cover_page())
            
            # Parse content
            logger.info("🔄 Parsing markdown content...")
            content_elements = self._parse_markdown_to_elements(content)
            elements.extend(content_elements)
            
            # Build PDF
            logger.info("📝 Building PDF...")
            doc.build(elements)
            
            logger.info(f"✅ PDF generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Error generating PDF: {e}")
            raise
    
    def generate_quick_reference_pdf(self) -> Path:
        """Generate quick reference PDF"""
        try:
            logger.info("📋 Generating Quick Reference PDF...")
            
            output_path = self.output_dir / f"AISOC_MCP_Quick_Reference_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=50,
                leftMargin=50,
                topMargin=80,
                bottomMargin=80
            )
            
            elements = []
            
            # Title
            elements.append(Paragraph("📋 AISOC MCP - Quick Reference", self.styles['CustomTitle']))
            elements.append(Spacer(1, 20))
            
            # Quick start section
            elements.append(Paragraph("🚀 Quick Start Commands", self.styles['CustomHeading2']))
            elements.append(Spacer(1, 10))
            
            install_commands = """git clone https://github.com/urtir/AISOC-MCP.git
cd AISOC-MCP
python -m venv aisoc_env
.\\aisoc_env\\Scripts\\Activate.ps1
pip install -r requirements.txt
python migrate_database.py"""
            
            elements.append(Paragraph(install_commands, self.styles['Code']))
            
            # Key URLs
            elements.append(Paragraph("📊 Key Access Points", self.styles['CustomHeading2']))
            elements.append(Spacer(1, 10))
            
            url_data = [
                ['Service', 'URL', 'Description'],
                ['Web Dashboard', 'http://localhost:5000', 'Main interface'],
                ['LM Studio', 'http://localhost:1234', 'AI model server'],
                ['Wazuh Manager', 'https://localhost:55000', 'SIEM API'],
                ['FastMCP API', 'http://localhost:8000', 'MCP endpoint']
            ]
            
            url_table = Table(url_data, hAlign='LEFT')
            url_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor("#f3f4f6")),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#374151")),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, HexColor("#d1d5db")),
            ]))
            
            elements.append(url_table)
            elements.append(Spacer(1, 20))
            
            # Build PDF
            doc.build(elements)
            
            logger.info(f"✅ Quick Reference PDF generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Error generating Quick Reference PDF: {e}")
            raise

def main():
    """Main function"""
    try:
        project_root = Path(__file__).parent.parent
        generator = ReportLabPDFGenerator(project_root)
        
        print("🛡️  AISOC MCP - ReportLab PDF Generator")
        print("=" * 50)
        
        # Generate complete guide
        complete_pdf = generator.generate_pdf()
        print(f"📄 Complete Guide PDF: {complete_pdf}")
        
        # Generate quick reference
        quick_pdf = generator.generate_quick_reference_pdf()
        print(f"📋 Quick Reference PDF: {quick_pdf}")
        
        print("\n✅ All PDFs generated successfully!")
        print(f"📁 Output directory: {generator.output_dir}")
        
        # Try to open output directory
        try:
            if sys.platform.startswith('win'):
                os.startfile(generator.output_dir)
            elif sys.platform.startswith('darwin'):
                os.system(f'open "{generator.output_dir}"')
            else:
                os.system(f'xdg-open "{generator.output_dir}"')
        except:
            pass
            
    except Exception as e:
        logger.error(f"❌ Failed to generate PDFs: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()