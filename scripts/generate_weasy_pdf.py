#!/usr/bin/env python3
"""
AISOC MCP - PDF Generator dengan WeasyPrint (Bahasa Indonesia)
Mengkonversi HTML menjadi PDF dengan kualitas tinggi

Author: Tim AISOC MCP
Date: 26 September 2025
Version: 1.1.0
"""

import os
import sys
from pathlib import Path
import logging
from datetime import datetime
import weasyprint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WeasyPrintPDFGenerator:
    """Generator PDF menggunakan WeasyPrint untuk kualitas terbaik"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docs_dir = project_root / "docs" / "pdf"
        
        # Cari file HTML yang sudah dibuat
        html_files = list(self.docs_dir.glob("Panduan_AISOC_MCP_*.html"))
        if html_files:
            self.html_path = html_files[0]  # Ambil yang terbaru
        else:
            raise FileNotFoundError("File HTML tidak ditemukan. Jalankan generate_html_guide.py terlebih dahulu.")
    
    def generate_pdf_from_html(self):
        """Generate PDF dari file HTML yang sudah ada"""
        try:
            logger.info("🚀 Memulai konversi HTML ke PDF dengan WeasyPrint...")
            
            if not self.html_path.exists():
                raise FileNotFoundError(f"File HTML tidak ditemukan: {self.html_path}")
            
            # Output PDF path
            output_pdf = self.docs_dir / f"Panduan_AISOC_MCP_WeasyPrint_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            logger.info(f"📖 Membaca file HTML: {self.html_path}")
            
            # Generate PDF dengan WeasyPrint
            logger.info("🔨 Mengkonversi ke PDF...")
            weasyprint.HTML(filename=str(self.html_path)).write_pdf(str(output_pdf))
            
            logger.info(f"✅ PDF berhasil dibuat dengan WeasyPrint: {output_pdf}")
            return output_pdf
            
        except Exception as e:
            logger.error(f"❌ Error membuat PDF: {e}")
            raise

def main():
    """Main function"""
    print("=" * 55)
    print("🛡️  AISOC MCP - WeasyPrint PDF Generator (Bahasa Indonesia)")
    print("=" * 55)
    
    try:
        # Get project root
        project_root = Path(__file__).parent.parent
        
        # Create generator
        generator = WeasyPrintPDFGenerator(project_root)
        
        # Generate PDF
        output_file = generator.generate_pdf_from_html()
        
        print(f"")
        print(f"✅ PDF berhasil dibuat dengan WeasyPrint!")
        print(f"📄 File PDF: {output_file}")
        print(f"📁 Direktori output: {generator.docs_dir}")
        print(f"")
        print(f"🎉 Panduan AISOC MCP dengan kualitas tinggi siap digunakan!")
        print(f"💡 WeasyPrint menghasilkan PDF dengan kualitas layout yang sangat baik!")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()