"""
Path configuration for the LMS MCP project
"""

import os
from pathlib import Path

# Get the project root directory (parent of src)
PROJECT_ROOT = Path(__file__).parent.parent

# Define common paths
PATHS = {
    'root': PROJECT_ROOT,
    'src': PROJECT_ROOT / 'src',
    'data': PROJECT_ROOT / 'data',
    'logs': PROJECT_ROOT / 'logs',
    'docs': PROJECT_ROOT / 'docs',
    'config': PROJECT_ROOT / 'config',
    'templates': PROJECT_ROOT / 'templates',
    'tests': PROJECT_ROOT / 'tests',
}

# Database paths
DATABASE_PATHS = {
    'wazuh_archives': PATHS['data'] / 'wazuh_archives.db',
    'chat_history': PATHS['data'] / 'chat_history.db',
}

def get_path(key: str) -> Path:
    """Get a predefined path by key"""
    return PATHS.get(key, PROJECT_ROOT)

def get_database_path(db_name: str) -> str:
    """Get database path as string"""
    return str(DATABASE_PATHS.get(db_name, PATHS['data'] / f'{db_name}.db'))

def ensure_directory_exists(path: Path) -> None:
    """Ensure a directory exists, create if it doesn't"""
    path.mkdir(parents=True, exist_ok=True)

# Ensure data and logs directories exist
ensure_directory_exists(PATHS['data'])
ensure_directory_exists(PATHS['logs'])
