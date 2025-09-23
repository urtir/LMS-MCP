#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced test script for Wazuh Archives RAG function
Includes database inspection and testing with available data
"""

import asyncio
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Add the src directory to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

# Import the RAG function
try:
    from src.api.wazuh_fastmcp_server import wazuh_archives_rag
except ImportError:
    # Alternative import path
    import sys
    sys.path.insert(0, str(project_root / "src" / "api"))
    from wazuh_fastmcp_server import wazuh_archives_rag

def inspect_database():
    """Inspect the Wazuh archives database to understand available data"""
    
    print("🔍 INSPECTING WAZUH ARCHIVES DATABASE")
    print("=" * 50)
    
    try:
        # Database path
        db_path = project_root / "data" / "wazuh_archives.db"
        
        if not db_path.exists():
            print(f"❌ Database not found at: {db_path}")
            return None
        
        print(f"📍 Database path: {db_path}")
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📊 Available tables: {[table[0] for table in tables]}")
        
        # Check if wazuh_archives table exists
        if ('wazuh_archives',) not in tables:
            print("❌ wazuh_archives table not found!")
            conn.close()
            return None
        
        # Get table schema
        cursor.execute("PRAGMA table_info(wazuh_archives);")
        columns = cursor.fetchall()
        print(f"\n📋 Table schema (wazuh_archives):")
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
        
        # Get total row count
        cursor.execute("SELECT COUNT(*) FROM wazuh_archives;")
        total_rows = cursor.fetchone()[0]
        print(f"\n📊 Total rows in database: {total_rows}")
        
        if total_rows == 0:
            print("❌ No data in wazuh_archives table!")
            conn.close()
            return None
        
        # Get date range of available data
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM wazuh_archives;")
        min_date, max_date = cursor.fetchone()
        print(f"📅 Data date range: {min_date} to {max_date}")
        
        # Get recent logs count by days
        print(f"\n📈 Log count by recent days:")
        for days in [1, 7, 30, 90, 365]:
            cursor.execute(f"""
                SELECT COUNT(*) FROM wazuh_archives 
                WHERE datetime(timestamp) >= datetime('now', '-{days} days')
            """)
            count = cursor.fetchone()[0]
            print(f"   Last {days:3d} days: {count:,} logs")
        
        # Get sample of recent logs
        cursor.execute("""
            SELECT timestamp, agent_name, rule_level, rule_description, location
            FROM wazuh_archives 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        recent_logs = cursor.fetchall()
        
        print(f"\n📝 Sample of most recent logs:")
        for i, log in enumerate(recent_logs, 1):
            print(f"   {i}. {log[0]} | {log[1]} | Level {log[2]} | {log[3][:50]}...")
        
        # Check for logs with specific keywords
        test_keywords = ['SQL', 'injection', 'attack', 'brute', 'force', 'login', 'failed']
        print(f"\n🔎 Keyword analysis:")
        
        for keyword in test_keywords:
            cursor.execute(f"""
                SELECT COUNT(*) FROM wazuh_archives 
                WHERE rule_description LIKE '%{keyword}%' 
                   OR full_log LIKE '%{keyword}%'
                   OR location LIKE '%{keyword}%'
            """)
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"   '{keyword}': {count} logs")
        
        conn.close()
        
        return {
            'total_rows': total_rows,
            'date_range': (min_date, max_date),
            'columns': [col[1] for col in columns]
        }
        
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")
        return None

async def test_rag_with_available_data():
    """Test RAG function with data that actually exists in database"""
    
    print("\n🧪 TESTING RAG WITH AVAILABLE DATA")
    print("=" * 50)
    
    try:
        # Database path
        db_path = project_root / "data" / "wazuh_archives.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get the actual date range of data
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM wazuh_archives;")
        min_date, max_date = cursor.fetchone()
        
        if not min_date or not max_date:
            print("❌ No timestamp data available")
            return
        
        print(f"📅 Available data: {min_date} to {max_date}")
        
        # Calculate days from oldest to newest
        min_dt = datetime.fromisoformat(min_date.replace('Z', '+00:00'))
        max_dt = datetime.fromisoformat(max_date.replace('Z', '+00:00'))
        total_days = (max_dt - min_dt).days + 1
        
        print(f"📊 Using {total_days} days to cover all available data")
        
        # Test with very broad search to get any results
        test_queries = [
            "security event",
            "log entry",
            "agent",
            "rule",
            "alert"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            print("-" * 30)
            
            try:
                # Use enough days to cover all data
                results = await wazuh_archives_rag(query, days_range=total_days + 30)
                
                if results:
                    print(f"✅ Found {len(results)} relevant logs")
                    print(f"🎯 Similarity scores: {results[0]['similarity_score']:.4f} to {results[-1]['similarity_score']:.4f}")
                    
                    # Show top result details
                    top_result = results[0]
                    print(f"📝 Top result:")
                    print(f"   Timestamp: {top_result.get('timestamp', 'N/A')}")
                    print(f"   Agent: {top_result.get('agent_name', 'N/A')}")
                    print(f"   Rule: {top_result.get('rule_description', 'N/A')}")
                    
                    # Save results for this query
                    output_file = project_root / f"rag_results_{query.replace(' ', '_')}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
                    print(f"💾 Results saved: {output_file}")
                    
                    break  # Found working query, exit loop
                else:
                    print("❌ No results found")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error testing with available data: {e}")

async def test_specific_sql_injection():
    """Test specifically for SQL injection if any exists"""
    
    print("\n🎯 TESTING SPECIFIC SQL INJECTION DETECTION")
    print("=" * 50)
    
    try:
        # Check if there are any SQL-related logs first
        db_path = project_root / "data" / "wazuh_archives.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Look for SQL-related content
        cursor.execute("""
            SELECT COUNT(*) FROM wazuh_archives 
            WHERE LOWER(rule_description) LIKE '%sql%' 
               OR LOWER(full_log) LIKE '%sql%'
               OR LOWER(location) LIKE '%sql%'
        """)
        sql_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM wazuh_archives 
            WHERE LOWER(rule_description) LIKE '%injection%' 
               OR LOWER(full_log) LIKE '%injection%'
        """)
        injection_count = cursor.fetchone()[0]
        
        print(f"📊 SQL-related logs: {sql_count}")
        print(f"📊 Injection-related logs: {injection_count}")
        
        if sql_count > 0 or injection_count > 0:
            print("✅ Found SQL/injection related logs, testing RAG...")
            
            # Use maximum days to ensure we capture all data
            results = await wazuh_archives_rag("SQL injection", days_range=3650)  # 10 years
            
            if results:
                print(f"🎉 SUCCESS! Found {len(results)} SQL injection related logs")
                
                # Show detailed results
                for i, result in enumerate(results[:3], 1):
                    print(f"\n📝 Result #{i} (Score: {result['similarity_score']:.4f}):")
                    print(f"   Agent: {result.get('agent_name', 'N/A')}")
                    print(f"   Rule: {result.get('rule_description', 'N/A')}")
                    print(f"   Location: {result.get('location', 'N/A')}")
                    if result.get('full_log'):
                        preview = result['full_log'][:150] + "..." if len(result['full_log']) > 150 else result['full_log']
                        print(f"   Log: {preview}")
            else:
                print("❌ No SQL injection results despite having SQL-related logs")
        else:
            print("ℹ️  No SQL or injection related logs in database")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error in SQL injection test: {e}")

async def main():
    """Main test function"""
    
    print("🧪 COMPREHENSIVE WAZUH ARCHIVES RAG TEST")
    print("=" * 60)
    
    # Step 1: Inspect database
    db_info = inspect_database()
    
    if not db_info:
        print("\n❌ Cannot proceed without database access")
        return
    
    # Step 2: Test with available data
    await test_rag_with_available_data()
    
    # Step 3: Test specific SQL injection
    await test_specific_sql_injection()
    
    print("\n🏁 Comprehensive testing completed!")

if __name__ == "__main__":
    asyncio.run(main())