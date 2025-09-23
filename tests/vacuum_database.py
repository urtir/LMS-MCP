#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Force Vacuum Wazuh Database
Script to aggressively compact the database file after deletion
"""

import os
import sqlite3
import sys
from pathlib import Path

# Add config directory to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
from config.config_manager import ConfigManager

def force_vacuum_database():
    """Force aggressive database vacuum to reclaim space"""
    try:
        # Get database configuration
        config = ConfigManager()
        database_dir = config.get('database.DATABASE_DIR', './data')
        wazuh_db_name = config.get('database.WAZUH_DB_NAME', 'wazuh_archives.db')
        
        # Build full path
        wazuh_db_path = os.path.join(database_dir, wazuh_db_name)
        
        # Ensure absolute path
        if not os.path.isabs(wazuh_db_path):
            wazuh_db_path = os.path.join(project_root, wazuh_db_path)
        
        print(f"Database path: {wazuh_db_path}")
        
        # Check if database exists
        if not os.path.exists(wazuh_db_path):
            print(f"❌ Database file not found: {wazuh_db_path}")
            return False
        
        # Get file size before
        file_size_before = os.path.getsize(wazuh_db_path) / (1024 * 1024)  # MB
        print(f"📏 File size before optimization: {file_size_before:.2f} MB")
        
        # Connect to database
        print("🔌 Connecting to database...")
        conn = sqlite3.connect(wazuh_db_path)
        
        # Check record count
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM wazuh_archives")
        record_count = cursor.fetchone()[0]
        print(f"📊 Current records: {record_count:,}")
        
        # Step 1: Set auto_vacuum to FULL
        print("🔧 Setting auto_vacuum to FULL...")
        conn.execute("PRAGMA auto_vacuum = FULL")
        
        # Step 2: Run VACUUM (this forces immediate space reclaim)
        print("🗑️  Running VACUUM (this may take a moment)...")
        conn.execute("VACUUM")
        
        # Step 3: Run ANALYZE for optimization
        print("📊 Running ANALYZE...")
        conn.execute("ANALYZE")
        
        # Step 4: Check database integrity
        print("🔍 Checking database integrity...")
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]
        print(f"✅ Integrity check: {integrity_result}")
        
        conn.close()
        
        # Get file size after
        file_size_after = os.path.getsize(wazuh_db_path) / (1024 * 1024)  # MB
        size_reduction = file_size_before - file_size_after
        reduction_percent = (size_reduction / file_size_before) * 100 if file_size_before > 0 else 0
        
        print(f"\n📏 File size after optimization: {file_size_after:.2f} MB")
        print(f"💾 Space recovered: {size_reduction:.2f} MB ({reduction_percent:.1f}%)")
        
        if size_reduction > 0.1:  # More than 0.1 MB recovered
            print("✅ Database successfully compacted!")
        else:
            print("ℹ️  Database was already optimally sized.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error optimizing database: {e}")
        return False

def recreate_database():
    """Alternative: Recreate database from scratch (most aggressive)"""
    try:
        config = ConfigManager()
        database_dir = config.get('database.DATABASE_DIR', './data')
        wazuh_db_name = config.get('database.WAZUH_DB_NAME', 'wazuh_archives.db')
        
        wazuh_db_path = os.path.join(database_dir, wazuh_db_name)
        if not os.path.isabs(wazuh_db_path):
            wazuh_db_path = os.path.join(project_root, wazuh_db_path)
        
        # Get file size before
        file_size_before = os.path.getsize(wazuh_db_path) / (1024 * 1024)  # MB
        
        print(f"\n🔄 Recreating database from scratch...")
        print(f"📏 Original file size: {file_size_before:.2f} MB")
        
        # Create backup name
        backup_path = wazuh_db_path + ".backup"
        
        # Move original file to backup
        os.rename(wazuh_db_path, backup_path)
        print(f"📁 Original file backed up to: {backup_path}")
        
        # Create new database with proper schema
        conn = sqlite3.connect(wazuh_db_path)
        
        # Create the wazuh_archives table with proper schema
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS wazuh_archives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            agent_id TEXT,
            agent_name TEXT,
            agent_ip TEXT,
            manager_name TEXT,
            rule_id INTEGER,
            rule_level INTEGER,
            rule_description TEXT,
            rule_mitre_id TEXT,
            rule_mitre_tactic TEXT,
            rule_mitre_technique TEXT,
            location TEXT,
            decoder_name TEXT,
            full_log TEXT,
            json_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        conn.execute(create_table_sql)
        
        # Create indices for better performance
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON wazuh_archives(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_rule_level ON wazuh_archives(rule_level)",
            "CREATE INDEX IF NOT EXISTS idx_agent_name ON wazuh_archives(agent_name)",
            "CREATE INDEX IF NOT EXISTS idx_rule_id ON wazuh_archives(rule_id)",
            "CREATE INDEX IF NOT EXISTS idx_created_at ON wazuh_archives(created_at)"
        ]
        
        for index_sql in indices:
            conn.execute(index_sql)
        
        conn.commit()
        conn.close()
        
        # Get new file size
        file_size_after = os.path.getsize(wazuh_db_path) / (1024 * 1024)  # MB
        size_reduction = file_size_before - file_size_after
        
        print(f"📏 New file size: {file_size_after:.2f} MB")
        print(f"💾 Space saved: {size_reduction:.2f} MB")
        print("✅ Database recreated successfully!")
        print(f"📁 Backup available at: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error recreating database: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 WAZUH DATABASE VACUUM TOOL")
    print("=" * 60)
    print()
    
    print("Choose optimization method:")
    print("1. Force VACUUM (recommended)")
    print("2. Recreate database (most aggressive)")
    print()
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        print("\n🗑️  Running force VACUUM...")
        success = force_vacuum_database()
    elif choice == "2":
        print("\n⚠️  WARNING: This will recreate the database file completely.")
        confirm = input("Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            success = recreate_database()
        else:
            print("❌ Operation cancelled")
            success = False
    else:
        print("❌ Invalid choice")
        success = False
    
    if success:
        print("\n✅ Database optimization completed!")
    else:
        print("\n❌ Database optimization failed!")
    
    print("\n" + "=" * 60)