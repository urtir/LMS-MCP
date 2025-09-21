#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clear Wazuh Archives Database
Script to delete all records from wazuh_archives table
"""

import os
import sqlite3
import sys
from pathlib import Path

# Add config directory to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
from config.config_manager import ConfigManager

def clear_wazuh_archives():
    """Clear all data from wazuh_archives table"""
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
        
        # Connect to database
        print("🔌 Connecting to database...")
        conn = sqlite3.connect(wazuh_db_path)
        cursor = conn.cursor()
        
        # Get current record count
        cursor.execute("SELECT COUNT(*) FROM wazuh_archives")
        current_count = cursor.fetchone()[0]
        print(f"📊 Current records in wazuh_archives: {current_count:,}")
        
        if current_count == 0:
            print("✅ Database is already empty!")
            conn.close()
            return True
        
        # Confirm deletion
        response = input(f"\n⚠️  WARNING: This will delete ALL {current_count:,} records from wazuh_archives table.\nContinue? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Operation cancelled by user")
            conn.close()
            return False
        
        print("\n🗑️  Deleting all records...")
        
        # Delete all records
        cursor.execute("DELETE FROM wazuh_archives")
        deleted_count = cursor.rowcount
        
        # Reset auto-increment counter
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='wazuh_archives'")
        
        # Commit changes
        conn.commit()
        
        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM wazuh_archives")
        remaining_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ Successfully deleted {deleted_count:,} records")
        print(f"📊 Remaining records: {remaining_count}")
        print("🔄 Auto-increment counter reset")
        
        if remaining_count == 0:
            print("\n🎉 Wazuh archives database cleared successfully!")
            return True
        else:
            print(f"\n⚠️  Warning: {remaining_count} records still remain")
            return False
        
    except Exception as e:
        print(f"❌ Error clearing database: {e}")
        return False

def vacuum_database():
    """Optimize database after deletion"""
    try:
        config = ConfigManager()
        database_dir = config.get('database.DATABASE_DIR', './data')
        wazuh_db_name = config.get('database.WAZUH_DB_NAME', 'wazuh_archives.db')
        
        wazuh_db_path = os.path.join(database_dir, wazuh_db_name)
        if not os.path.isabs(wazuh_db_path):
            wazuh_db_path = os.path.join(project_root, wazuh_db_path)
        
        # Get file size before optimization
        file_size_before = os.path.getsize(wazuh_db_path) / (1024 * 1024)  # MB
        print(f"\n🔧 Optimizing database...")
        print(f"📏 File size before VACUUM: {file_size_before:.2f} MB")
        
        conn = sqlite3.connect(wazuh_db_path)
        
        # More aggressive cleanup
        print("🗑️  Running VACUUM...")
        conn.execute("VACUUM")
        
        print("🧹 Running additional cleanup...")
        conn.execute("PRAGMA auto_vacuum = FULL")
        conn.execute("VACUUM")
        
        # Analyze for better performance
        print("📊 Analyzing database structure...")
        conn.execute("ANALYZE")
        
        conn.close()
        
        # Get file size after optimization
        file_size_after = os.path.getsize(wazuh_db_path) / (1024 * 1024)  # MB
        size_reduction = file_size_before - file_size_after
        
        print(f"📏 File size after VACUUM: {file_size_after:.2f} MB")
        print(f"💾 Space recovered: {size_reduction:.2f} MB")
        print("✅ Database optimized successfully!")
        
    except Exception as e:
        print(f"⚠️  Warning: Database optimization failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🗑️  WAZUH ARCHIVES DATABASE CLEANER")
    print("=" * 60)
    print()
    
    success = clear_wazuh_archives()
    
    if success:
        vacuum_database()
        print("\n✅ All operations completed successfully!")
        print("📝 Note: Wazuh realtime server will start collecting new data automatically.")
    else:
        print("\n❌ Operation failed or cancelled.")
    
    print("\n" + "=" * 60)