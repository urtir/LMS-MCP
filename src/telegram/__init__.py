"""
Telegram package - Contains all telegram bot related modules
"""

# Delayed imports to avoid circular import issues
__all__ = [
    'TelegramSecurityBot',
    'PDFReportGenerator', 
    'SecurityReportGenerator',
    'get_report_generator'
]

def get_telegram_security_bot():
    """Get TelegramSecurityBot class with delayed import"""
    from .telegram_security_bot import TelegramSecurityBot
    return TelegramSecurityBot

def get_pdf_generator():
    """Get PDFReportGenerator class with delayed import"""
    from .telegram_pdf_generator import PDFReportGenerator
    return PDFReportGenerator

def get_security_report_generator():
    """Get SecurityReportGenerator class with delayed import"""
    from .telegram_report_generator import SecurityReportGenerator
    return SecurityReportGenerator

def get_report_generator():
    """Get report generator instance with delayed import"""
    from .telegram_report_generator import get_report_generator
    return get_report_generator()
