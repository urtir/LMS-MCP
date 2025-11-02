#!/usr/bin/env python3
"""
AISOC MCP - PDF Guide Generator (Bahasa Indonesia)
Mengkonversi README.md menjadi dokumentasi PDF profesional

Author: Tim AISOC MCP
Date: 26 September 2025
Version: 1.1.0
"""

import os
import sys
import markdown
from pathlib import Path
import logging
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import Color, blue, red, green, grey, black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import re
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def remove_paper_search_references(content):
    """Menghilangkan semua referensi paper search dari konten"""
    # Hapus baris yang mengandung paper-search
    lines = content.split('\n')
    filtered_lines = []
    
    for line in lines:
        # Skip lines yang mengandung paper-search atau paper search
        if 'paper-search' in line.lower() or 'paper search' in line.lower():
            continue
        # Skip folder paper-search-mcp dari struktur
        if 'paper-search-mcp/' in line:
            continue
        filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

class AISOCMCPPDFGenerator:
    """Generator PDF untuk AISOC MCP dalam Bahasa Indonesia"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.readme_path = project_root / "README.md"
        self.output_dir = project_root / "docs" / "pdf"
        
        # Pastikan output directory ada
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom styles untuk PDF"""
        
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=Color(0.2, 0.3, 0.8),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            textColor=Color(0.4, 0.4, 0.4),
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=15,
            textColor=Color(0.1, 0.4, 0.2),
            fontName='Helvetica-Bold',
            borderPadding=5
        ))
        
        # Subsection header style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            textColor=Color(0.2, 0.2, 0.6),
            fontName='Helvetica-Bold'
        ))
        
        # Code style
        self.styles.add(ParagraphStyle(
            name='CodeBlock',
            parent=self.styles['Code'],
            fontSize=9,
            leftIndent=20,
            rightIndent=20,
            spaceAfter=10,
            backgroundColor=Color(0.95, 0.95, 0.95),
            borderPadding=10,
            fontName='Courier'
        ))
        
        # Normal with justify
        self.styles.add(ParagraphStyle(
            name='NormalJustify',
            parent=self.styles['Normal'],
            alignment=TA_JUSTIFY,
            spaceAfter=6,
            fontSize=10
        ))
    
    def _create_cover_page(self):
        """Membuat halaman sampul"""
        story = []
        
        # Logo/Title area
        story.append(Spacer(1, 2*inch))
        
        # Main title
        title = Paragraph("🛡️ AISOC MCP", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.3*inch))
        
        # Subtitle
        subtitle = Paragraph("AI Security Operations Center", self.styles['CustomSubtitle'])
        story.append(subtitle)
        story.append(Spacer(1, 0.5*inch))
        
        # Description
        description = """
        <para alignment="center" fontSize="12" spaceAfter="20">
        <b>Panduan Lengkap Pengguna &amp; Dokumentasi</b><br/>
        <br/>
        Panduan komprehensif untuk instalasi, konfigurasi, dan penggunaan platform AISOC MCP.<br/>
        Dari nol hingga mahir - semua yang Anda butuhkan untuk deploy dan operasikan<br/>
        AI-powered Security Operations Center Anda.
        </para>
        """
        story.append(Paragraph(description, self.styles['Normal']))
        story.append(Spacer(1, 1*inch))
        
        # Version info
        version_info = f"""
        <para alignment="center" fontSize="10" textColor="gray">
        <b>Versi:</b> 1.0.0<br/>
        <b>Tanggal:</b> {datetime.now().strftime('%d %B %Y')}<br/>
        <b>Repository:</b> github.com/urtir/AISOC-MCP<br/>
        <br/>
        <b>Teknologi:</b> Python 3.8+ • FastMCP • Wazuh SIEM • LM Studio • Telegram Bot<br/>
        </para>
        """
        story.append(Paragraph(version_info, self.styles['Normal']))
        
        # Add page break
        story.append(PageBreak())
        
        return story
    
    def _create_toc(self, content):
        """Membuat daftar isi"""
        story = []
        
        # TOC Title
        toc_title = Paragraph("📋 Daftar Isi", self.styles['SectionHeader'])
        story.append(toc_title)
        story.append(Spacer(1, 20))
        
        # Extract headers for TOC
        toc_items = []
        lines = content.split('\n')
        page_num = 3  # Start from page 3 (after cover and TOC)
        
        for line in lines:
            if line.startswith('## ') and '**' in line:
                title = re.sub(r'## .*?\*\*(.*?)\*\*', r'\1', line)
                title = re.sub(r'[🎯⭐🏗️📋🚀⚙️🎮🔧📊🤖📱🌐🧪📚🚨🤝]', '', title).strip()
                toc_items.append((title, page_num))
                page_num += 2
        
        # Create TOC table
        toc_data = []
        for title, page in toc_items:
            dots = '.' * (50 - len(title))
            toc_data.append([title, dots, str(page)])
        
        if toc_data:
            toc_table = Table(toc_data, colWidths=[4*inch, 2*inch, 0.5*inch])
            toc_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(toc_table)
        
        story.append(PageBreak())
        return story
    
    def _process_markdown_content(self, content):
        """Memproses konten markdown menjadi elemen PDF"""
        story = []
        
        # Remove paper search references
        content = remove_paper_search_references(content)
        
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # Headers
            if line.startswith('# '):
                title = re.sub(r'# .*?🛡️ (.*)', r'\1', line)
                story.append(Paragraph(title, self.styles['CustomTitle']))
                story.append(Spacer(1, 20))
                
            elif line.startswith('## ') and '**' in line:
                title = re.sub(r'## .*?\*\*(.*?)\*\*', r'\1', line)
                title = re.sub(r'[🎯⭐🏗️📋🚀⚙️🎮🔧📊🤖📱🌐🧪📚🚨🤝]', '', title).strip()
                story.append(Paragraph(title, self.styles['SectionHeader']))
                story.append(Spacer(1, 15))
                
            elif line.startswith('### '):
                title = re.sub(r'### \*\*(.*?)\*\*', r'\1', line)
                title = re.sub(r'### (.*)', r'\1', title)
                title = re.sub(r'[🛠️🤖🛡️📊🔍📈⚙️🎯]', '', title).strip()
                story.append(Paragraph(title, self.styles['SubsectionHeader']))
                story.append(Spacer(1, 10))
                
            elif line.startswith('#### '):
                title = re.sub(r'#### \*\*(.*?)\*\*', r'\1', line)
                title = re.sub(r'#### (.*)', r'\1', title)
                story.append(Paragraph(f"<b>{title}</b>", self.styles['Normal']))
                story.append(Spacer(1, 8))
            
            # Code blocks
            elif line.startswith('```'):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                
                if code_lines:
                    code_text = '\n'.join(code_lines)
                    # Escape special characters for ReportLab
                    code_text = code_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(f"<font name='Courier' size='9'>{code_text}</font>", 
                                         self.styles['CodeBlock']))
                    story.append(Spacer(1, 10))
            
            # Tables
            elif '|' in line and '-' not in line:
                table_lines = []
                # Collect table lines
                while i < len(lines) and '|' in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                i -= 1  # Back one step
                
                if len(table_lines) > 1:
                    # Process table
                    table_data = []
                    for table_line in table_lines:
                        if '---' not in table_line:  # Skip separator line
                            cells = [cell.strip() for cell in table_line.split('|')[1:-1]]
                            # Clean up markdown formatting in cells
                            cleaned_cells = []
                            for cell in cells:
                                cell = re.sub(r'\*\*(.*?)\*\*', r'\1', cell)  # Remove bold
                                cell = re.sub(r'`(.*?)`', r'\1', cell)        # Remove code
                                cell = re.sub(r'[🤖👥📈🚨⚠️🎯🔀🕵️🛡️📄❤️🔄📊🔧💾🗃️🔍✅🖥️]', '', cell).strip()
                                cleaned_cells.append(cell)
                            table_data.append(cleaned_cells)
                    
                    if table_data:
                        # Create table
                        pdf_table = Table(table_data)
                        pdf_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), Color(0.8, 0.8, 0.9)),
                            ('TEXTCOLOR', (0, 0), (-1, 0), black),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 9),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                            ('BACKGROUND', (0, 1), (-1, -1), Color(0.95, 0.95, 0.95)),
                            ('GRID', (0, 0), (-1, -1), 1, black)
                        ]))
                        story.append(pdf_table)
                        story.append(Spacer(1, 15))
            
            # Lists
            elif line.startswith('- ') or line.startswith('* '):
                list_items = []
                while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                    item = lines[i].strip()[2:].strip()
                    # Clean up markdown formatting
                    item = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', item)
                    item = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', item)
                    list_items.append(f"• {item}")
                    i += 1
                i -= 1  # Back one step
                
                for item in list_items:
                    story.append(Paragraph(item, self.styles['Normal']))
                story.append(Spacer(1, 10))
            
            # Regular paragraphs
            else:
                if line and not line.startswith('#'):
                    # Clean up markdown formatting
                    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                    text = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', text)
                    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # Remove links
                    text = re.sub(r'[🎯🔥⭐🛠️🤖🛡️📊🔍💾🎯⚙️📋💬🧪📚🚨🤝📄📞🌟🙏]', '', text).strip()
                    
                    if text:
                        story.append(Paragraph(text, self.styles['NormalJustify']))
                        story.append(Spacer(1, 6))
            
            i += 1
        
        return story
    
    def generate_pdf(self):
        """Generate PDF document"""
        try:
            logger.info("🚀 Memulai pembuatan PDF...")
            
            if not self.readme_path.exists():
                raise FileNotFoundError(f"README.md tidak ditemukan di {self.readme_path}")
            
            # Read README
            logger.info("📖 Membaca README.md...")
            with open(self.readme_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Setup PDF document
            output_pdf = self.output_dir / f"Panduan_AISOC_MCP_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            logger.info("📄 Membuat dokumen PDF...")
            doc = SimpleDocTemplate(
                str(output_pdf),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Build story
            story = []
            
            # Add cover page
            logger.info("📋 Membuat halaman sampul...")
            story.extend(self._create_cover_page())
            
            # Add table of contents
            logger.info("📑 Membuat daftar isi...")
            story.extend(self._create_toc(markdown_content))
            
            # Add main content
            logger.info("📝 Memproses konten utama...")
            story.extend(self._process_markdown_content(markdown_content))
            
            # Build PDF
            logger.info("🔨 Membangun PDF...")
            doc.build(story)
            
            logger.info(f"✅ PDF berhasil dibuat: {output_pdf}")
            return output_pdf
            
        except Exception as e:
            logger.error(f"❌ Error membuat PDF: {e}")
            raise

def main():
    """Main function"""
    print("=" * 50)
    print("🛡️  AISOC MCP - PDF Guide Generator (Bahasa Indonesia)")
    print("=" * 50)
    
    try:
        # Get project root
        project_root = Path(__file__).parent.parent
        
        # Create generator
        generator = AISOCMCPPDFGenerator(project_root)
        
        # Generate PDF
        output_file = generator.generate_pdf()
        
        print(f"")
        print(f"✅ PDF berhasil dibuat!")
        print(f"📄 File PDF: {output_file}")
        print(f"📁 Direktori output: {generator.output_dir}")
        print(f"")
        print(f"🎉 Panduan AISOC MCP siap digunakan!")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()