#!/usr/bin/env python3
"""
AISOC MCP - PDF Guide Generator
Converts README.md to professional PDF documentation

Author: AISOC MCP Team
Date: September 25, 2025
Version: 1.0.0
"""

import os
import sys
import markdown
import pdfkit
from pathlib import Path
import logging
from datetime import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PDFGuideGenerator:
    """Generate professional PDF guide from README.md"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.readme_path = project_root / "README.md"
        self.output_dir = project_root / "docs" / "pdf"
        self.css_path = project_root / "scripts" / "pdf_styles.css"
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # PDF options
        self.pdf_options = {
            'page-size': 'A4',
            'margin-top': '1in',
            'margin-right': '0.8in',
            'margin-bottom': '1in',
            'margin-left': '0.8in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None,
            'print-media-type': None,
            'disable-smart-shrinking': None,
            'footer-right': '[page]/[toPage]',
            'footer-font-size': '9',
            'footer-spacing': '5',
            'header-html': self._create_header_html(),
        }
    
    def _create_header_html(self) -> str:
        """Create HTML header for PDF"""
        header_html = f"""
        <div style="
            text-align: center; 
            font-family: Arial, sans-serif; 
            font-size: 10px; 
            color: #666;
            border-bottom: 1px solid #ccc;
            padding-bottom: 5px;
            margin-bottom: 10px;
        ">
            <strong>AISOC MCP - AI Security Operations Center</strong> | 
            Generated on {datetime.now().strftime('%B %d, %Y')}
        </div>
        """
        
        # Save header to temporary file
        header_file = self.output_dir / "header.html"
        with open(header_file, 'w', encoding='utf-8') as f:
            f.write(header_html)
        
        return str(header_file)
    
    def _create_css_styles(self) -> str:
        """Create CSS styles for PDF"""
        css_content = """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 11px;
            line-height: 1.6;
            color: #333;
            max-width: 100%;
            margin: 0;
            padding: 0;
        }
        
        h1 {
            font-size: 24px;
            font-weight: 700;
            color: #1e3a8a;
            margin-top: 30px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3b82f6;
            page-break-before: always;
        }
        
        h1:first-of-type {
            page-break-before: avoid;
            text-align: center;
            font-size: 28px;
            color: #1e40af;
            margin-top: 0;
        }
        
        h2 {
            font-size: 18px;
            font-weight: 600;
            color: #1e40af;
            margin-top: 25px;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #3b82f6;
        }
        
        h3 {
            font-size: 14px;
            font-weight: 600;
            color: #374151;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        h4 {
            font-size: 12px;
            font-weight: 500;
            color: #4b5563;
            margin-top: 15px;
            margin-bottom: 8px;
        }
        
        p {
            margin-bottom: 12px;
            text-align: justify;
        }
        
        ul, ol {
            margin-bottom: 15px;
            padding-left: 25px;
        }
        
        li {
            margin-bottom: 5px;
        }
        
        code {
            background-color: #f3f4f6;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 10px;
            color: #dc2626;
        }
        
        pre {
            background-color: #1f2937;
            color: #f9fafb;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 9px;
            line-height: 1.4;
            margin: 15px 0;
            page-break-inside: avoid;
        }
        
        pre code {
            background: none;
            color: inherit;
            padding: 0;
            font-size: inherit;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 10px;
            page-break-inside: avoid;
        }
        
        th, td {
            border: 1px solid #d1d5db;
            padding: 8px 10px;
            text-align: left;
            vertical-align: top;
        }
        
        th {
            background-color: #f3f4f6;
            font-weight: 600;
            color: #374151;
        }
        
        tr:nth-child(even) {
            background-color: #f9fafb;
        }
        
        blockquote {
            border-left: 4px solid #3b82f6;
            padding-left: 15px;
            margin: 15px 0;
            color: #4b5563;
            font-style: italic;
        }
        
        .badge {
            display: inline-block;
            padding: 3px 8px;
            font-size: 8px;
            font-weight: 500;
            color: white;
            background-color: #3b82f6;
            border-radius: 12px;
            margin: 2px;
        }
        
        .toc {
            background-color: #f8fafc;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            page-break-inside: avoid;
        }
        
        .toc h2 {
            margin-top: 0;
            color: #1e40af;
        }
        
        .toc ul {
            list-style-type: none;
            padding-left: 0;
        }
        
        .toc li {
            margin-bottom: 8px;
        }
        
        .toc a {
            color: #3b82f6;
            text-decoration: none;
            font-weight: 500;
        }
        
        .warning {
            background-color: #fef3cd;
            border: 1px solid #ffeaa7;
            border-radius: 6px;
            padding: 12px;
            margin: 15px 0;
        }
        
        .info {
            background-color: #e0f2fe;
            border: 1px solid #81d4fa;
            border-radius: 6px;
            padding: 12px;
            margin: 15px 0;
        }
        
        .success {
            background-color: #e8f5e8;
            border: 1px solid #a5d6a7;
            border-radius: 6px;
            padding: 12px;
            margin: 15px 0;
        }
        
        /* Page break utilities */
        .page-break {
            page-break-before: always;
        }
        
        .no-break {
            page-break-inside: avoid;
        }
        
        /* Print-specific styles */
        @media print {
            body {
                font-size: 10px;
            }
            
            h1 {
                font-size: 22px;
            }
            
            h2 {
                font-size: 16px;
            }
            
            pre {
                font-size: 8px;
            }
            
            table {
                font-size: 9px;
            }
        }
        """
        
        # Save CSS to file
        with open(self.css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)
        
        return str(self.css_path)
    
    def _preprocess_markdown(self, content: str) -> str:
        """Preprocess markdown content for better PDF conversion"""
        
        # Add page breaks for major sections
        content = re.sub(r'^## ([^#].*?)$', r'<div class="page-break"></div>\n\n## \1', content, flags=re.MULTILINE)
        
        # Convert badges to styled spans
        badge_patterns = [
            (r'\[!\[Python\]\(.*?\)\]\(.*?\)', '<span class="badge">Python 3.8+</span>'),
            (r'\[!\[FastMCP\]\(.*?\)\]\(.*?\)', '<span class="badge">FastMCP</span>'),
            (r'\[!\[Wazuh\]\(.*?\)\]\(.*?\)', '<span class="badge">Wazuh SIEM</span>'),
            (r'\[!\[Telegram\]\(.*?\)\]\(.*?\)', '<span class="badge">Telegram Bot</span>'),
            (r'\[!\[LM Studio\]\(.*?\)\]\(.*?\)', '<span class="badge">LM Studio AI</span>'),
        ]
        
        for pattern, replacement in badge_patterns:
            content = re.sub(pattern, replacement, content)
        
        # Improve code block formatting
        content = re.sub(r'```(\w+)\n', r'```\1\n', content)
        
        # Add no-break class to tables
        content = re.sub(r'^(\|.*?\|)$', r'<div class="no-break">\n\1\n</div>', content, flags=re.MULTILINE)
        
        # Convert mermaid diagrams to placeholder text
        mermaid_pattern = r'```mermaid\n(.*?)\n```'
        content = re.sub(mermaid_pattern, 
                        lambda m: f'<div class="info"><strong>📊 System Architecture Diagram</strong><br/>Interactive diagram available in web version</div>', 
                        content, flags=re.DOTALL)
        
        # Add styling classes to specific sections
        content = re.sub(r'### \*\*(.*?)\*\*', r'### <strong>\1</strong>', content)
        
        # Fix emoji spacing
        content = re.sub(r'([🎯🔥⭐🛠️🤖🛡️📊🔍📈🎯⚙️📋💬🧪📚🚨🤝📄📞🌟🙏])', r'\1 ', content)
        
        return content
    
    def _create_cover_page(self) -> str:
        """Create a cover page for the PDF"""
        cover_html = f"""
        <div style="text-align: center; padding-top: 100px;">
            <h1 style="font-size: 36px; color: #1e40af; margin-bottom: 20px; border: none; page-break-before: avoid;">
                🛡️ AISOC MCP
            </h1>
            <h2 style="font-size: 24px; color: #374151; margin-bottom: 40px; border: none; padding: 0;">
                AI Security Operations Center
            </h2>
            <h3 style="font-size: 18px; color: #6b7280; margin-bottom: 60px;">
                Model Context Protocol Platform
            </h3>
            
            <div style="background: #f8fafc; padding: 30px; border-radius: 12px; margin: 40px 0;">
                <h4 style="color: #1e40af; font-size: 16px; margin-bottom: 20px;">Complete User Guide & Documentation</h4>
                <p style="font-size: 14px; color: #4b5563; line-height: 1.8;">
                    Comprehensive guide for installation, configuration, and usage of AISOC MCP platform.<br/>
                    From zero to hero - everything you need to deploy and operate your AI-powered Security Operations Center.
                </p>
            </div>
            
            <div style="margin-top: 80px;">
                <p style="font-size: 12px; color: #6b7280;">
                    <strong>Version:</strong> 1.0.0<br/>
                    <strong>Generated:</strong> {datetime.now().strftime('%B %d, %Y')}<br/>
                    <strong>Repository:</strong> github.com/urtir/AISOC-MCP
                </p>
            </div>
            
            <div style="position: absolute; bottom: 50px; left: 50%; transform: translateX(-50%);">
                <p style="font-size: 10px; color: #9ca3af;">
                    🛡️ Made with ❤️ by AISOC MCP Team
                </p>
            </div>
        </div>
        <div style="page-break-after: always;"></div>
        """
        
        return cover_html
    
    def generate_pdf(self) -> Path:
        """Generate PDF from README.md"""
        try:
            logger.info("🚀 Starting PDF generation...")
            
            # Check if README exists
            if not self.readme_path.exists():
                raise FileNotFoundError(f"README.md not found at {self.readme_path}")
            
            # Read README content
            logger.info("📖 Reading README.md...")
            with open(self.readme_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Preprocess markdown
            logger.info("🔧 Preprocessing markdown content...")
            markdown_content = self._preprocess_markdown(markdown_content)
            
            # Create CSS styles
            logger.info("🎨 Creating CSS styles...")
            css_path = self._create_css_styles()
            
            # Convert markdown to HTML
            logger.info("🔄 Converting markdown to HTML...")
            md = markdown.Markdown(
                extensions=[
                    'markdown.extensions.tables',
                    'markdown.extensions.fenced_code',
                    'markdown.extensions.toc',
                    'markdown.extensions.codehilite'
                ],
                extension_configs={
                    'markdown.extensions.codehilite': {
                        'css_class': 'codehilite',
                        'use_pygments': False
                    }
                }
            )
            
            html_content = md.convert(markdown_content)
            
            # Add cover page
            cover_page = self._create_cover_page()
            
            # Combine cover and content
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>AISOC MCP - Complete Guide</title>
                <link rel="stylesheet" href="{css_path}">
                <style>
                    @page {{
                        size: A4;
                        margin: 1in 0.8in 1in 0.8in;
                    }}
                </style>
            </head>
            <body>
                {cover_page}
                {html_content}
            </body>
            </html>
            """
            
            # Save HTML to temporary file
            html_file = self.output_dir / "guide_temp.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(full_html)
            
            # Generate PDF
            logger.info("📄 Generating PDF...")
            output_pdf = self.output_dir / f"AISOC_MCP_Complete_Guide_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            # Update PDF options with header path
            self.pdf_options['header-html'] = self._create_header_html()
            
            pdfkit.from_file(str(html_file), str(output_pdf), options=self.pdf_options, css=css_path)
            
            # Cleanup temporary files
            html_file.unlink()
            Path(self.pdf_options['header-html']).unlink()
            
            logger.info(f"✅ PDF generated successfully: {output_pdf}")
            return output_pdf
            
        except Exception as e:
            logger.error(f"❌ Error generating PDF: {e}")
            raise
    
    def generate_quick_reference(self) -> Path:
        """Generate a quick reference PDF"""
        try:
            logger.info("📋 Generating Quick Reference PDF...")
            
            quick_ref_content = """
            # AISOC MCP - Quick Reference Guide
            
            ## 🚀 Quick Start Commands
            
            ### Installation
            ```bash
            git clone https://github.com/urtir/AISOC-MCP.git
            cd AISOC-MCP
            python -m venv aisoc_env
            .\\aisoc_env\\Scripts\\Activate.ps1
            pip install -r requirements.txt
            python migrate_database.py
            ```
            
            ### Start Services
            ```bash
            # All services
            python scripts/start_all_services.py
            
            # Individual services
            python src/api/wazuh_fastmcp_server.py        # FastMCP Server
            python src/webapp/webapp_chatbot.py           # Web App
            python src/telegram/telegram_security_bot.py  # Telegram Bot
            ```
            
            ## 🔧 FastMCP Tools (29 Tools)
            
            | Category | Tool | Description |
            |----------|------|-------------|
            | **Core** | `check_wazuh_log` | AI-powered log analysis |
            | **Core** | `get_agent_info` | Detailed agent information |
            | **Core** | `get_security_events` | Security event analysis |
            | **Analysis** | `search_logs_semantic` | Vector-based log search |
            | **Analysis** | `get_hybrid_search` | CAG + Semantic search |
            | **Monitoring** | `get_system_health` | System health status |
            | **Monitoring** | `get_agent_status` | Real-time agent status |
            
            ## 📱 Telegram Bot Commands
            
            | Command | Description | Example |
            |---------|-------------|---------|
            | `/start` | Initialize bot | `/start` |
            | `/help` | Show all commands | `/help` |
            | `/query` | Ask security question | `/query top threats today` |
            | `/search` | Search logs | `/search failed login` |
            | `/report` | Generate PDF report | `/report daily` |
            | `/alerts` | Recent alerts | `/alerts high` |
            
            ## ⚙️ Configuration Files
            
            ### Environment Variables (.env)
            ```bash
            LM_STUDIO_BASE_URL=http://localhost:1234/v1
            WAZUH_API_URL=https://localhost:55000
            WAZUH_USERNAME=wazuh-wui
            WAZUH_PASSWORD=your-password
            TELEGRAM_BOT_TOKEN=your-bot-token
            FLASK_PORT=5000
            ```
            
            ### Key Config (config/config.json)
            ```json
            {
              "services": {
                "fastmcp_server": {"enabled": true, "port": 8000},
                "web_app": {"enabled": true, "port": 5000},
                "telegram_bot": {"enabled": true}
              }
            }
            ```
            
            ## 🧪 Testing Commands
            
            ```bash
            # Test individual components
            python tests/test_tool_definition.py          # FastMCP tools
            python tests/check_db.py                      # Database
            python tests/test_telegram_alerting.py       # Telegram bot
            
            # Health checks
            python scripts/health_check.py               # Full system
            python scripts/check_fastmcp.py             # FastMCP server
            python scripts/check_webapp.py              # Web application
            ```
            
            ## 🚨 Common Troubleshooting
            
            ### Service Won't Start
            ```bash
            # Check ports
            netstat -an | findstr :8000
            netstat -an | findstr :5000
            
            # Check LM Studio
            curl http://localhost:1234/v1/models
            
            # Check Wazuh API
            curl -k -u "user:pass" https://localhost:55000
            ```
            
            ### Database Issues
            ```bash
            # Reset database
            python tests/vacuum_database.py
            python migrate_database.py
            python scripts/reset_database.py
            ```
            
            ### AI/ML Issues
            ```bash
            # Rebuild embeddings
            python scripts/rebuild_embeddings.py
            
            # Clear cache
            python scripts/clear_cag_cache.py
            ```
            
            ## 📊 Key URLs
            
            - **Web Dashboard**: http://localhost:5000
            - **LM Studio**: http://localhost:1234
            - **Wazuh Manager**: https://localhost:55000
            - **GitHub**: https://github.com/urtir/AISOC-MCP
            
            ## 📞 Support
            
            - **Issues**: GitHub Issues
            - **Docs**: docs/ directory
            - **Community**: Telegram @AisocMcpCommunity
            
            ---
            *Generated on {datetime.now().strftime('%B %d, %Y')}*
            """
            
            # Convert to HTML and PDF
            md = markdown.Markdown(extensions=['markdown.extensions.tables', 'markdown.extensions.fenced_code'])
            html_content = md.convert(quick_ref_content)
            
            # Create simplified CSS for quick reference
            quick_css = """
            body { font-family: Arial, sans-serif; font-size: 10px; line-height: 1.5; }
            h1 { font-size: 18px; color: #1e40af; }
            h2 { font-size: 14px; color: #374151; }
            h3 { font-size: 12px; color: #4b5563; }
            pre { background: #f3f4f6; padding: 8px; font-size: 8px; }
            table { width: 100%; border-collapse: collapse; font-size: 9px; }
            th, td { border: 1px solid #ccc; padding: 4px; }
            th { background: #f0f0f0; }
            """
            
            css_file = self.output_dir / "quick_ref_styles.css"
            with open(css_file, 'w', encoding='utf-8') as f:
                f.write(quick_css)
            
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>AISOC MCP - Quick Reference</title>
                <style>{quick_css}</style>
            </head>
            <body>{html_content}</body>
            </html>
            """
            
            html_file = self.output_dir / "quick_ref_temp.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(full_html)
            
            output_pdf = self.output_dir / f"AISOC_MCP_Quick_Reference_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            quick_options = {
                'page-size': 'A4',
                'margin-top': '0.5in',
                'margin-right': '0.5in',
                'margin-bottom': '0.5in',
                'margin-left': '0.5in',
                'encoding': "UTF-8",
                'enable-local-file-access': None,
            }
            
            pdfkit.from_file(str(html_file), str(output_pdf), options=quick_options)
            
            # Cleanup
            html_file.unlink()
            css_file.unlink()
            
            logger.info(f"✅ Quick Reference PDF generated: {output_pdf}")
            return output_pdf
            
        except Exception as e:
            logger.error(f"❌ Error generating Quick Reference PDF: {e}")
            raise

def main():
    """Main function to generate PDFs"""
    try:
        project_root = Path(__file__).parent.parent
        generator = PDFGuideGenerator(project_root)
        
        print("🛡️  AISOC MCP - PDF Guide Generator")
        print("=" * 50)
        
        # Generate complete guide
        complete_pdf = generator.generate_pdf()
        print(f"📄 Complete Guide: {complete_pdf}")
        
        # Generate quick reference
        quick_pdf = generator.generate_quick_reference()
        print(f"📋 Quick Reference: {quick_pdf}")
        
        print("\n✅ All PDFs generated successfully!")
        print(f"📁 Output directory: {generator.output_dir}")
        
        # Open output directory
        if sys.platform.startswith('win'):
            os.startfile(generator.output_dir)
        elif sys.platform.startswith('darwin'):
            os.system(f'open "{generator.output_dir}"')
        else:
            os.system(f'xdg-open "{generator.output_dir}"')
            
    except Exception as e:
        logger.error(f"❌ Failed to generate PDFs: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()