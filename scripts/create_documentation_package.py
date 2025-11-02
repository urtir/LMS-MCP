#!/usr/bin/env python3
"""
AISOC MCP - Comprehensive Documentation Package Creator
Membuat paket dokumentasi lengkap dalam Bahasa Indonesia

Author: Tim AISOC MCP
Date: 26 September 2025
Version: 1.2.0
"""

import os
import sys
from pathlib import Path
import logging
from datetime import datetime
import shutil
import zipfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DocumentationPackager:
    """Membuat paket dokumentasi lengkap AISOC MCP"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docs_dir = project_root / "docs"
        self.pdf_dir = project_root / "docs" / "pdf"
        self.output_dir = project_root / "docs" / "release"
        
        # Pastikan output directory ada
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_documentation_package(self):
        """Membuat paket dokumentasi lengkap"""
        try:
            logger.info("🚀 Memulai pembuatan paket dokumentasi...")
            
            # Create release directory structure
            release_date = datetime.now().strftime('%Y%m%d')
            package_name = f"AISOC_MCP_Documentation_Package_{release_date}"
            package_dir = self.output_dir / package_name
            
            if package_dir.exists():
                shutil.rmtree(package_dir)
            package_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"📁 Membuat struktur paket: {package_dir}")
            
            # Create subdirectories
            (package_dir / "PDF_Guides").mkdir(exist_ok=True)
            (package_dir / "HTML_Guides").mkdir(exist_ok=True)
            (package_dir / "Technical_Docs").mkdir(exist_ok=True)
            (package_dir / "Quick_Reference").mkdir(exist_ok=True)
            
            # Copy PDF files
            logger.info("📄 Mengcopy file PDF...")
            for pdf_file in self.pdf_dir.glob("*.pdf"):
                shutil.copy2(pdf_file, package_dir / "PDF_Guides")
                logger.info(f"  ✓ {pdf_file.name}")
            
            # Copy HTML files
            logger.info("🌐 Mengcopy file HTML...")
            for html_file in self.pdf_dir.glob("*.html"):
                shutil.copy2(html_file, package_dir / "HTML_Guides")
                logger.info(f"  ✓ {html_file.name}")
            
            # Copy technical documentation
            logger.info("📚 Mengcopy dokumentasi teknis...")
            tech_docs = [
                "ALERT_SYSTEM_README.md",
                "CACHE_AUGMENTED_GENERATION_CAG.md",
                "COMPLETE_VARIABLES_LIST.md",
                "FastMCP_Documentation.md",
                "Wazuh_API_Documentation.md"
            ]
            
            for doc in tech_docs:
                doc_path = self.docs_dir / doc
                if doc_path.exists():
                    shutil.copy2(doc_path, package_dir / "Technical_Docs")
                    logger.info(f"  ✓ {doc}")
            
            # Copy main README
            main_readme = self.project_root / "README.md"
            if main_readme.exists():
                shutil.copy2(main_readme, package_dir / "Quick_Reference" / "README_Main.md")
                logger.info("  ✓ README.md")
            
            # Create package info file
            self._create_package_info(package_dir)
            
            # Create ZIP archive
            zip_path = self.output_dir / f"{package_name}.zip"
            logger.info(f"🗜️ Membuat arsip ZIP: {zip_path}")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(package_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(package_dir)
                        zipf.write(file_path, arcname)
            
            logger.info(f"✅ Paket dokumentasi berhasil dibuat!")
            return zip_path, package_dir
            
        except Exception as e:
            logger.error(f"❌ Error membuat paket: {e}")
            raise
    
    def _create_package_info(self, package_dir: Path):
        """Membuat file informasi paket"""
        info_content = f"""# 🛡️ AISOC MCP - Paket Dokumentasi Lengkap

## 📋 Informasi Paket
- **Nama**: AISOC MCP Documentation Package
- **Versi**: 1.0.0
- **Tanggal**: {datetime.now().strftime('%d %B %Y')}
- **Bahasa**: Indonesia
- **Format**: PDF, HTML, Markdown

## 📁 Struktur Paket

### 📄 PDF_Guides/
Berisi panduan lengkap dalam format PDF:
- `Panduan_AISOC_MCP_*.pdf` - Panduan utama lengkap

### 🌐 HTML_Guides/
Berisi panduan dalam format HTML untuk viewing di browser:
- `Panduan_AISOC_MCP_*.html` - Panduan utama dalam HTML
- `AISOC_MCP_Quick_Reference_*.html` - Referensi cepat

### 📚 Technical_Docs/
Berisi dokumentasi teknis detail:
- `ALERT_SYSTEM_README.md` - Sistem alerting
- `CACHE_AUGMENTED_GENERATION_CAG.md` - Teknologi CAG
- `COMPLETE_VARIABLES_LIST.md` - Daftar variabel lengkap
- `FastMCP_Documentation.md` - Dokumentasi FastMCP
- `Wazuh_API_Documentation.md` - API Wazuh

### 🚀 Quick_Reference/
Berisi referensi cepat dan getting started:
- `README_Main.md` - README utama project

## 🎯 Cara Penggunaan

### Untuk Pemula:
1. Mulai dengan `README_Main.md` di folder Quick_Reference
2. Baca `Panduan_AISOC_MCP_*.pdf` untuk instalasi lengkap
3. Gunakan `AISOC_MCP_Quick_Reference_*.html` untuk referensi cepat

### Untuk Developer:
1. Baca semua file di folder Technical_Docs
2. Implementasikan sesuai panduan di PDF_Guides
3. Gunakan HTML_Guides untuk reference saat development

### Untuk System Administrator:
1. Focus pada panduan instalasi di PDF
2. Implementasikan monitoring sesuai Technical_Docs
3. Setup alerting menggunakan ALERT_SYSTEM_README.md

## 🆘 Support

Jika mengalami kesulitan:
1. Baca troubleshooting section di panduan PDF
2. Check dokumentasi teknis terkait
3. Contact: github.com/urtir/AISOC-MCP

## 📜 License

MIT License - Lihat file LICENSE di repository utama.

---
🛡️ **AISOC MCP Team** - Dedicated to AI-Powered Security Excellence
"""
        
        info_file = package_dir / "PACKAGE_INFO.md"
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write(info_content)
        
        logger.info("  ✓ PACKAGE_INFO.md")

def main():
    """Main function"""
    print("=" * 60)
    print("🛡️  AISOC MCP - Documentation Package Creator")
    print("=" * 60)
    
    try:
        # Get project root
        project_root = Path(__file__).parent.parent
        
        # Create packager
        packager = DocumentationPackager(project_root)
        
        # Create package
        zip_path, package_dir = packager.create_documentation_package()
        
        print(f"")
        print(f"✅ Paket dokumentasi berhasil dibuat!")
        print(f"📦 File ZIP: {zip_path}")
        print(f"📁 Direktori: {package_dir}")
        print(f"")
        print(f"📊 Statistik Paket:")
        
        # Count files
        pdf_count = len(list((package_dir / "PDF_Guides").glob("*.pdf")))
        html_count = len(list((package_dir / "HTML_Guides").glob("*.html")))
        md_count = len(list((package_dir / "Technical_Docs").glob("*.md")))
        
        print(f"   📄 PDF Files: {pdf_count}")
        print(f"   🌐 HTML Files: {html_count}")
        print(f"   📚 Markdown Files: {md_count}")
        print(f"   📦 Total Size: {zip_path.stat().st_size / 1024 / 1024:.2f} MB")
        print(f"")
        print(f"🎉 Paket siap untuk distribusi!")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()