#!/usr/bin/env python3
"""
AISOC MCP - PDF Guide Generator (Alternative with WeasyPrint)
Converts README.md to professional PDF documentation

Author: AISOC MCP Team
Date: September 25, 2025
Version: 1.0.0
"""

import os
import sys
import markdown
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

class SimplePDFGenerator:
    """Simple PDF generator using HTML and print functionality"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.readme_path = project_root / "README.md"
        self.output_dir = project_root / "docs" / "pdf"
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_css_styles(self) -> str:
        """Create CSS styles for PDF"""
        return """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 12px;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: white;
        }
        
        h1 {
            font-size: 28px;
            font-weight: 700;
            color: #1e3a8a;
            margin-top: 40px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3b82f6;
            page-break-before: always;
        }
        
        h1:first-of-type {
            page-break-before: avoid;
            text-align: center;
            font-size: 32px;
            color: #1e40af;
            margin-top: 0;
        }
        
        h2 {
            font-size: 22px;
            font-weight: 600;
            color: #1e40af;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-left: 15px;
            border-left: 4px solid #3b82f6;
        }
        
        h3 {
            font-size: 16px;
            font-weight: 600;
            color: #374151;
            margin-top: 25px;
            margin-bottom: 12px;
        }
        
        h4 {
            font-size: 14px;
            font-weight: 500;
            color: #4b5563;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        p {
            margin-bottom: 14px;
            text-align: justify;
        }
        
        ul, ol {
            margin-bottom: 16px;
            padding-left: 30px;
        }
        
        li {
            margin-bottom: 6px;
        }
        
        code {
            background-color: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 11px;
            color: #dc2626;
        }
        
        pre {
            background-color: #1f2937;
            color: #f9fafb;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 10px;
            line-height: 1.4;
            margin: 16px 0;
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
            margin: 16px 0;
            font-size: 11px;
        }
        
        th, td {
            border: 1px solid #d1d5db;
            padding: 10px 12px;
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
            padding-left: 16px;
            margin: 16px 0;
            color: #4b5563;
            font-style: italic;
        }
        
        .cover-page {
            text-align: center;
            padding: 100px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 80vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            page-break-after: always;
        }
        
        .cover-title {
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .cover-subtitle {
            font-size: 24px;
            margin-bottom: 40px;
            opacity: 0.9;
        }
        
        .cover-description {
            font-size: 16px;
            max-width: 600px;
            margin: 0 auto 40px;
            opacity: 0.8;
            line-height: 1.8;
        }
        
        .cover-meta {
            font-size: 14px;
            opacity: 0.7;
            margin-top: 60px;
        }
        
        .toc {
            background-color: #f8fafc;
            padding: 25px;
            border-radius: 10px;
            margin: 25px 0;
            border: 1px solid #e2e8f0;
        }
        
        .toc h2 {
            margin-top: 0;
            color: #1e40af;
            border: none;
            padding: 0;
        }
        
        .toc ul {
            list-style-type: none;
            padding-left: 0;
        }
        
        .toc li {
            margin-bottom: 10px;
            padding-left: 20px;
            position: relative;
        }
        
        .toc li:before {
            content: "→";
            position: absolute;
            left: 0;
            color: #3b82f6;
            font-weight: bold;
        }
        
        .alert {
            padding: 15px;
            margin: 16px 0;
            border-radius: 6px;
            border-left: 4px solid;
        }
        
        .alert-info {
            background-color: #e0f2fe;
            border-left-color: #0288d1;
            color: #01579b;
        }
        
        .alert-warning {
            background-color: #fff3cd;
            border-left-color: #ffc107;
            color: #856404;
        }
        
        .alert-success {
            background-color: #d4edda;
            border-left-color: #28a745;
            color: #155724;
        }
        
        .emoji {
            font-size: 1.2em;
            margin-right: 5px;
        }
        
        @media print {
            body {
                font-size: 11px;
            }
            
            .cover-page {
                background: #667eea !important;
                -webkit-print-color-adjust: exact;
                color-adjust: exact;
            }
            
            pre {
                background-color: #1f2937 !important;
                color: #f9fafb !important;
                -webkit-print-color-adjust: exact;
                color-adjust: exact;
            }
            
            th {
                background-color: #f3f4f6 !important;
                -webkit-print-color-adjust: exact;
                color-adjust: exact;
            }
        }
        </style>
        """
    
    def _preprocess_markdown(self, content: str) -> str:
        """Preprocess markdown content"""
        
        # Remove paper search references
        content = remove_paper_search_references(content)
        
        # Convert badges to text
        badge_patterns = [
            (r'\[!\[Python\]\(.*?\)\]\(.*?\)', '**Python 3.8+**'),
            (r'\[!\[FastMCP\]\(.*?\)\]\(.*?\)', '**FastMCP Protocol**'),
            (r'\[!\[Wazuh\]\(.*?\)\]\(.*?\)', '**Wazuh SIEM**'),
            (r'\[!\[Telegram\]\(.*?\)\]\(.*?\)', '**Telegram Bot**'),
            (r'\[!\[LM Studio\]\(.*?\)\]\(.*?\)', '**LM Studio AI**'),
        ]
        
        for pattern, replacement in badge_patterns:
            content = re.sub(pattern, replacement, content)
        
        # Convert mermaid diagrams to text descriptions
        mermaid_pattern = r'```mermaid\n(.*?)\n```'
        content = re.sub(mermaid_pattern, 
                        lambda m: '<div class="alert alert-info">📊 **Diagram Arsitektur Sistem** - Diagram interaktif tersedia di versi web</div>', 
                        content, flags=re.DOTALL)
        
        # Add emoji class
        content = re.sub(r'([🎯🔥⭐🛠️🤖🛡️📊🔍📈🎯⚙️📋💬🧪📚🚨🤝📄📞🌟🙏])', r'<span class="emoji">\1</span>', content)
        
        return content
    
    def _create_cover_page(self) -> str:
        """Create cover page HTML"""
        return f"""
        <div class="cover-page">
            <div class="cover-title">🛡️ AISOC MCP</div>
            <div class="cover-subtitle">AI Security Operations Center</div>
            <div class="cover-description">
                Panduan Lengkap Pengguna & Dokumentasi<br/>
                Panduan komprehensif untuk instalasi, konfigurasi, dan penggunaan platform AISOC MCP.<br/>
                Dari nol hingga mahir - semua yang Anda butuhkan untuk deploy dan operasikan AI-powered Security Operations Center Anda.
            </div>
            <div class="cover-meta">
                <strong>Versi:</strong> 1.0.0<br/>
                <strong>Dibuat:</strong> {datetime.now().strftime('%d %B %Y')}<br/>
                <strong>Repository:</strong> github.com/urtir/AISOC-MCP<br/><br/>
                🛡️ Made with ❤️ by AISOC MCP Team
            </div>
        </div>
        """
    
    def generate_html(self) -> Path:
        """Generate HTML version"""
        try:
            logger.info("🚀 Starting HTML generation...")
            
            if not self.readme_path.exists():
                raise FileNotFoundError(f"README.md not found at {self.readme_path}")
            
            # Read README
            logger.info("📖 Reading README.md...")
            with open(self.readme_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Preprocess
            logger.info("🔧 Preprocessing content...")
            markdown_content = self._preprocess_markdown(markdown_content)
            
            # Convert to HTML
            logger.info("🔄 Converting to HTML...")
            md = markdown.Markdown(
                extensions=[
                    'markdown.extensions.tables',
                    'markdown.extensions.fenced_code',
                    'markdown.extensions.toc',
                    'markdown.extensions.codehilite'
                ]
            )
            
            html_content = md.convert(markdown_content)
            
            # Create full HTML
            cover_page = self._create_cover_page()
            css_styles = self._create_css_styles()
            
            full_html = f"""
            <!DOCTYPE html>
            <html lang="id">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>AISOC MCP - Panduan Lengkap</title>
                {css_styles}
            </head>
            <body>
                {cover_page}
                {html_content}
                
                <div style="text-align: center; margin-top: 50px; padding: 20px; border-top: 2px solid #e2e8f0;">
                    <p style="color: #6b7280; font-size: 14px;">
                        📄 <strong>Panduan Lengkap AISOC MCP</strong><br/>
                        Dibuat pada {datetime.now().strftime('%d %B %Y')} | Versi 1.0.0<br/>
                        🛡️ Dibuat dengan ❤️ oleh Tim AISOC MCP
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Save HTML
            output_html = self.output_dir / f"Panduan_AISOC_MCP_{datetime.now().strftime('%Y%m%d')}.html"
            with open(output_html, 'w', encoding='utf-8') as f:
                f.write(full_html)
            
            logger.info(f"✅ HTML berhasil dibuat: {output_html}")
            return output_html
            
        except Exception as e:
            logger.error(f"❌ Error generating HTML: {e}")
            raise
    
    def generate_quick_reference_html(self) -> Path:
        """Generate quick reference HTML"""
        try:
            logger.info("📋 Generating Quick Reference HTML...")
            
            quick_content = f"""
            # AISOC MCP - Panduan Referensi Cepat
            
            <div class="alert alert-info">
            <strong>🚀 Mulai Cepat:</strong> Perintah-perintah penting dan konfigurasi untuk platform AISOC MCP
            </div>
            
            ## <span class="emoji">🚀</span> **Perintah Mulai Cepat**
            
            ### Instalasi
            ```bash
            git clone https://github.com/urtir/AISOC-MCP.git
            cd AISOC-MCP
            python -m venv aisoc_env
            .\\aisoc_env\\Scripts\\Activate.ps1
            pip install -r requirements.txt
            python migrate_database.py
            ```
            
            ### Menjalankan Layanan
            ```bash
            # Semua layanan sekaligus (Disarankan)
            python scripts/start_all_services.py
            
            # Layanan individual
            python src/api/wazuh_fastmcp_server.py        # FastMCP Server (Port 8000)
            python src/webapp/webapp_chatbot.py           # Web App (Port 5000)
            python src/telegram/telegram_security_bot.py  # Telegram Bot
            python src/api/wazuh_realtime_server.py       # Real-time Monitor
            ```
            
            ## <span class="emoji">🔧</span> **FastMCP Tools (29 Tools Tersedia)**
            
            | Kategori | Tool | Deskripsi | Penggunaan |
            |----------|------|-----------|------------|
            | **Core** | `check_wazuh_log` | Analisis log berbasis AI | Analisis keamanan tingkat tinggi |
            | **Core** | `get_agent_info` | Informasi detail agent | Manajemen agent |
            | **Core** | `get_security_events` | Analisis event keamanan | Deteksi ancaman |
            | **Core** | `get_critical_alerts` | Identifikasi alert kritis | Respon prioritas |
            | **Analysis** | `search_logs_semantic` | Pencarian log berbasis vektor | Kemampuan pencarian lanjutan |
            | **Analysis** | `get_hybrid_search` | CAG + Semantic gabungan | Hasil pencarian terbaik |
            | **Analysis** | `analyze_attack_patterns` | Deteksi pola serangan | Threat hunting |
            | **Monitoring** | `get_system_health` | Status kesehatan sistem | Monitoring infrastruktur |
            | **Monitoring** | `get_agent_status` | Status agent real-time | Pemeriksaan konektivitas |
            | **Monitoring** | `get_rule_statistics` | Statistik rule firing | Tuning performa |
            | **Advanced** | `execute_wql_query` | Wazuh Query Language | Query kustom |
            | **Advanced** | `get_mitre_info` | Pemetaan MITRE ATT&CK | Klasifikasi ancaman |
            
            ## <span class="emoji">📱</span> **Perintah Telegram Bot**
            
            ### Perintah Dasar
            | Perintah | Deskripsi | Contoh |
            |----------|-----------|--------|
            | `/start` | Inisialisasi bot | `/start` |
            | `/help` | Tampilkan semua perintah | `/help` |
            | `/status` | Status sistem | `/status` |
            | `/settings` | Konfigurasi bot | `/settings` |
            
            ### Query Commands  
            | Command | Description | Example |
            |---------|-------------|---------|
            | `/query` | Ask security question | `/query what are top threats today?` |
            | `/search` | Search logs | `/search failed login` |
            | `/agents` | List agents | `/agents` |
            | `/alerts` | Recent alerts | `/alerts high` |
            
            ### Report Commands
            | Command | Description | Example |
            |---------|-------------|---------|
            | `/report` | Generate PDF report | `/report daily` |
            | `/summary` | Security summary | `/summary last 24h` |
            | `/stats` | System statistics | `/stats agents` |
            | `/export` | Export data | `/export logs csv` |
            
            ## <span class="emoji">⚙️</span> **Configuration Files**
            
            ### Environment Variables (.env)
            ```bash
            # LM Studio Configuration
            LM_STUDIO_BASE_URL=http://localhost:1234/v1
            LM_STUDIO_API_KEY=lm-studio
            LM_STUDIO_MODEL=qwen2.5-1.5b-instruct
            
            # Wazuh Configuration
            WAZUH_API_URL=https://localhost:55000
            WAZUH_USERNAME=wazuh-wui
            WAZUH_PASSWORD=your-secure-password
            
            # Flask Configuration
            FLASK_HOST=127.0.0.1
            FLASK_PORT=5000
            FLASK_SECRET_KEY=your-super-secret-key
            
            # Telegram Configuration
            TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
            TELEGRAM_CHAT_ID=your-chat-id
            ```
            
            ### Key Configuration (config/config.json)
            ```json
            {{
              "services": {{
                "fastmcp_server": {{
                  "enabled": true,
                  "host": "127.0.0.1", 
                  "port": 8000,
                  "lm_studio_url": "http://localhost:1234/v1"
                }},
                "web_app": {{
                  "enabled": true,
                  "host": "127.0.0.1",
                  "port": 5000,
                  "debug": false
                }},
                "telegram_bot": {{
                  "enabled": true,
                  "token": "${{TELEGRAM_BOT_TOKEN}}",
                  "admin_chat_id": "${{TELEGRAM_CHAT_ID}}"
                }}
              }},
              "wazuh": {{
                "api_url": "${{WAZUH_API_URL}}",
                "username": "${{WAZUH_USERNAME}}",
                "password": "${{WAZUH_PASSWORD}}",
                "verify_ssl": false
              }}
            }}
            ```
            
            ## <span class="emoji">🧪</span> **Testing & Verification Commands**
            
            ### Test Individual Components
            ```bash
            # Test FastMCP tools
            python tests/test_tool_definition.py
            python tests/test_check_wazuh_log_mcp.py
            
            # Test Database
            python tests/check_db.py
            python tests/vacuum_database.py
            
            # Test Telegram Bot
            python tests/test_telegram_alerting.py
            
            # Test AI Systems
            python tests/test_rag.py                    # RAG system
            python tests/test_cag.py                    # CAG system  
            python tests/test_hybrid_semantic_search.py # Hybrid search
            ```
            
            ### Health Check Commands
            ```bash
            # Complete system health check
            python scripts/health_check.py
            
            # Individual service checks
            python scripts/check_fastmcp.py      # FastMCP server
            python scripts/check_webapp.py      # Web application
            python scripts/check_telegram.py    # Telegram bot
            python scripts/check_database.py    # Database integrity
            python scripts/check_wazuh.py       # Wazuh connectivity
            python scripts/check_lmstudio.py    # LM Studio connection
            ```
            
            ## <span class="emoji">🚨</span> **Common Troubleshooting**
            
            ### Service Won't Start Issues
            ```bash
            # Check if ports are available
            netstat -an | findstr :8000          # FastMCP server port
            netstat -an | findstr :5000          # Web app port
            
            # Check LM Studio connection
            curl http://localhost:1234/v1/models
            
            # Check Wazuh API connection
            curl -k -u "username:password" https://localhost:55000
            
            # Verify Python dependencies
            pip list | grep -E "(fastmcp|flask|requests)"
            ```
            
            ### Database Issues
            ```bash
            # Database corruption or lock issues
            python tests/vacuum_database.py
            python migrate_database.py
            
            # Reset database completely
            python scripts/reset_database.py
            
            # Check database integrity
            python tests/check_db.py
            ```
            
            ### AI/ML System Issues
            ```bash
            # Rebuild RAG embeddings
            python scripts/rebuild_embeddings.py
            
            # Clear CAG cache
            python scripts/clear_cag_cache.py
            
            # Test LM Studio connection
            python tests/test_lm_studio_connection.py
            ```
            
            ### Telegram Bot Issues
            ```bash
            # Test bot connection
            python tests/test_telegram_connection.py
            
            # Verify bot token and permissions
            python scripts/test_telegram_alerts.py
            
            # Check chat ID configuration
            python scripts/get_telegram_chat_id.py
            ```
            
            ## <span class="emoji">📊</span> **Key URLs & Access Points**
            
            | Service | URL | Description |
            |---------|-----|-------------|
            | **Web Dashboard** | http://localhost:5000 | Main web interface |
            | **Admin Panel** | http://localhost:5000/admin | Admin interface |
            | **LM Studio** | http://localhost:1234 | AI model server |
            | **Wazuh Manager** | https://localhost:55000 | Wazuh API |
            | **FastMCP API** | http://localhost:8000 | MCP server endpoint |
            
            ## <span class="emoji">💾</span> **Database Queries**
            
            ### Common SQL Queries
            ```sql
            -- Get recent critical alerts
            SELECT rule_description, rule_level, COUNT(*) as count
            FROM wazuh_logs 
            WHERE rule_level >= 7 AND timestamp >= datetime('now', '-24 hours')
            GROUP BY rule_description, rule_level
            ORDER BY rule_level DESC, count DESC;
            
            -- Check agent activity
            SELECT agent_name, COUNT(*) as log_count, MAX(timestamp) as last_seen
            FROM wazuh_logs 
            GROUP BY agent_name 
            ORDER BY log_count DESC;
            
            -- Security events by hour
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as events
            FROM wazuh_logs 
            WHERE date(timestamp) = date('now')
            GROUP BY hour ORDER BY hour;
            ```
            
            ## <span class="emoji">🔄</span> **System Recovery Procedures**
            
            ### Complete System Reset
            ```bash
            # 1. Stop all services
            python scripts/stop_all_services.py
            
            # 2. Backup current data  
            python scripts/backup_data.py
            
            # 3. Reset configuration
            copy config/config.json.template config/config.json
            
            # 4. Reset database
            python scripts/reset_database.py
            
            # 5. Clear all caches
            python scripts/clear_all_caches.py
            
            # 6. Restart services
            python scripts/start_all_services.py
            ```
            
            ### Partial Recovery
            ```bash
            # Reset specific components only
            python scripts/reset_webapp.py      # Web application only
            python scripts/reset_telegram.py   # Telegram bot only  
            python scripts/reset_fastmcp.py    # FastMCP server only
            python scripts/reset_database.py   # Database only
            ```
            
            ## <span class="emoji">📞</span> **Support & Resources**
            
            ### Getting Help
            - **GitHub Issues**: https://github.com/urtir/AISOC-MCP/issues
            - **Documentation**: docs/ directory in project
            - **Community Telegram**: @AisocMcpCommunity
            - **Email Support**: support@aisoc-mcp.com
            
            ### Important File Locations
            ```
            📁 Project Structure:
            ├── src/                    # Source code
            ├── config/                 # Configuration files
            ├── data/                   # Databases
            ├── docs/                   # Documentation
            ├── logs/                   # Application logs
            ├── tests/                  # Test files
            └── scripts/                # Utility scripts
            ```
            
            ---
            
            <div class="alert alert-success">
            <strong>✅ Quick Reference Complete!</strong><br/>
            For detailed information, refer to the complete AISOC MCP documentation.
            </div>
            
            *Generated on {datetime.now().strftime('%B %d, %Y')} | Version 1.0.0*
            """
            
            # Convert to HTML
            md = markdown.Markdown(
                extensions=[
                    'markdown.extensions.tables',
                    'markdown.extensions.fenced_code'
                ]
            )
            
            html_content = md.convert(quick_content)
            css_styles = self._create_css_styles()
            
            full_html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>AISOC MCP - Quick Reference Guide</title>
                {css_styles}
            </head>
            <body>
                <div class="cover-page" style="min-height: 50vh; padding: 50px 20px;">
                    <div class="cover-title" style="font-size: 36px;">📋 AISOC MCP</div>
                    <div class="cover-subtitle" style="font-size: 20px;">Quick Reference Guide</div>
                    <div class="cover-description" style="font-size: 14px;">
                        Essential commands, configurations, and troubleshooting guide
                    </div>
                </div>
                
                {html_content}
                
                <div style="text-align: center; margin-top: 40px; padding: 20px; border-top: 2px solid #e2e8f0;">
                    <p style="color: #6b7280; font-size: 14px;">
                        📋 <strong>AISOC MCP Quick Reference</strong><br/>
                        Generated on {datetime.now().strftime('%B %d, %Y')} | Version 1.0.0<br/>
                        🛡️ Made with ❤️ by AISOC MCP Team
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Save HTML
            output_html = self.output_dir / f"AISOC_MCP_Quick_Reference_{datetime.now().strftime('%Y%m%d')}.html"
            with open(output_html, 'w', encoding='utf-8') as f:
                f.write(full_html)
            
            logger.info(f"✅ Quick Reference HTML generated: {output_html}")
            return output_html
            
        except Exception as e:
            logger.error(f"❌ Error generating Quick Reference HTML: {e}")
            raise

def main():
    """Main function"""
    try:
        project_root = Path(__file__).parent.parent
        generator = SimplePDFGenerator(project_root)
        
        print("🛡️  AISOC MCP - PDF Guide Generator")
        print("=" * 50)
        
        # Generate complete guide HTML
        complete_html = generator.generate_html()
        print(f"📄 Complete Guide HTML: {complete_html}")
        
        # Generate quick reference HTML  
        quick_html = generator.generate_quick_reference_html()
        print(f"📋 Quick Reference HTML: {quick_html}")
        
        print("\n✅ HTML files generated successfully!")
        print(f"📁 Output directory: {generator.output_dir}")
        
        print("\n📖 How to create PDF:")
        print("1. Open the HTML files in your browser")
        print("2. Press Ctrl+P (or Cmd+P on Mac)")  
        print("3. Select 'Save as PDF' as destination")
        print("4. Choose appropriate settings and save")
        
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
        logger.error(f"❌ Failed to generate files: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()