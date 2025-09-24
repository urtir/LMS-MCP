#!/usr/bin/env python3
"""
Wazuh Real-time Data Fetcher to SQLite3
Fetches JSON data from Wazuh Manager Docker container and stores it in SQLite3 database.
"""

import sqlite3
import json
import os
import sys
import docker
import time
import threading
import logging
import signal
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import asyncio

# Add config directory to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
from config.config_manager import ConfigManager
config = ConfigManager()

# Configure logging - NO FALLBACKS!
LOG_DIR = config.get('database.LOG_DIR')
WAZUH_REALTIME_LOG = config.get('logs.WAZUH_REALTIME_LOG')
log_path = os.path.join(LOG_DIR, WAZUH_REALTIME_LOG)

# Ensure absolute path
if not os.path.isabs(log_path):
    log_path = str(Path(__file__).parent.parent.parent / log_path)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WazuhSQLiteDatabase:
    """Handle SQLite database operations for Wazuh data."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Get path relative to project root using config - NO FALLBACKS!
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            database_dir = config.get('database.DATABASE_DIR')
            wazuh_db_name = config.get('database.WAZUH_DB_NAME')
            db_path = str(project_root / database_dir / wazuh_db_name)
        self.db_path = db_path
        self.connection = None
        self.last_processed_timestamp = None
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required tables."""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
            
            # Check if tables exist and create only if they don't
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wazuh_archives'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                # Create main archives table only if it doesn't exist
                self.connection.execute("""
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
                """)
                
                # Create indexes
                self.connection.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON wazuh_archives(timestamp)")
                self.connection.execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON wazuh_archives(agent_id)")
                self.connection.execute("CREATE INDEX IF NOT EXISTS idx_rule_id ON wazuh_archives(rule_id)")
                self.connection.execute("CREATE INDEX IF NOT EXISTS idx_rule_level ON wazuh_archives(rule_level)")
                self.connection.execute("CREATE INDEX IF NOT EXISTS idx_agent_name ON wazuh_archives(agent_name)")
                self.connection.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON wazuh_archives(created_at)")
            
            # Create metadata table for tracking
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS fetch_metadata (
                    id INTEGER PRIMARY KEY,
                    last_fetch_time DATETIME,
                    total_records INTEGER DEFAULT 0,
                    last_file_position INTEGER DEFAULT 0,
                    last_processed_timestamp TEXT,
                    container_id TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert initial metadata if not exists
            self.connection.execute("""
                INSERT OR IGNORE INTO fetch_metadata (id, last_fetch_time, total_records) 
                VALUES (1, datetime('now'), 0)
            """)
            
            self.connection.commit()
            logger.info(f"Database initialized: {self.db_path}")
            
            # Load last processed timestamp
            self.load_last_processed_timestamp()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def load_last_processed_timestamp(self):
        """Load the last processed timestamp from metadata."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT last_processed_timestamp FROM fetch_metadata WHERE id = 1")
            result = cursor.fetchone()
            if result and result[0]:
                self.last_processed_timestamp = result[0]
                logger.info(f"Loaded last processed timestamp: {self.last_processed_timestamp}")
            else:
                self.last_processed_timestamp = None
                logger.info("No previous timestamp found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading last processed timestamp: {e}")
            self.last_processed_timestamp = None
    
    def insert_archive_record(self, record: Dict[str, Any]) -> bool:
        """Insert a single archive record into database."""
        try:
            # Extract commonly used fields with proper type conversion
            timestamp = str(record.get('timestamp', datetime.now().isoformat()))
            
            # Check if this record is newer than our last processed timestamp
            if self.last_processed_timestamp and timestamp <= self.last_processed_timestamp:
                logger.debug(f"Skipping record with timestamp {timestamp} (not newer than {self.last_processed_timestamp})")
                return False
            
            # Check for duplicate by creating a unique hash of the record
            record_hash = self.create_record_hash(record)
            if self.is_duplicate_record(record_hash, timestamp):
                logger.debug(f"Skipping duplicate record with timestamp {timestamp}")
                return False
            
            agent_id = str(record.get('agent', {}).get('id', '')) if record.get('agent') else ''
            agent_name = str(record.get('agent', {}).get('name', '')) if record.get('agent') else ''
            agent_ip = str(record.get('agent', {}).get('ip', '')) if record.get('agent') else ''
            manager_name = str(record.get('manager', {}).get('name', '')) if record.get('manager') else ''
            
            # Handle rule_id and rule_level properly
            rule_id = 0
            rule_level = 0
            rule_description = ''
            rule_mitre_id = ''
            rule_mitre_tactic = ''
            rule_mitre_technique = ''
            
            if record.get('rule'):
                rule_dict = record.get('rule', {})
                try:
                    rule_id = int(rule_dict.get('id', 0)) if rule_dict.get('id') else 0
                except (ValueError, TypeError):
                    rule_id = 0
                    
                try:
                    rule_level = int(rule_dict.get('level', 0)) if rule_dict.get('level') else 0
                except (ValueError, TypeError):
                    rule_level = 0
                    
                rule_description = str(rule_dict.get('description', ''))
                
                # Handle MITRE information
                mitre = rule_dict.get('mitre', {})
                if isinstance(mitre, dict):
                    rule_mitre_id = str(mitre.get('id', ''))
                    rule_mitre_tactic = str(mitre.get('tactic', ''))
                    rule_mitre_technique = str(mitre.get('technique', ''))
            
            location = str(record.get('location', ''))
            decoder_name = str(record.get('decoder', {}).get('name', '')) if record.get('decoder') else ''
            full_log = str(record.get('full_log', ''))
            
            self.connection.execute("""
                INSERT INTO wazuh_archives (
                    timestamp, agent_id, agent_name, agent_ip, manager_name, rule_id, rule_level,
                    rule_description, rule_mitre_id, rule_mitre_tactic, rule_mitre_technique, 
                    location, decoder_name, full_log, json_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, agent_id, agent_name, agent_ip, manager_name, rule_id, rule_level,
                rule_description, rule_mitre_id, rule_mitre_tactic, rule_mitre_technique,
                location, decoder_name, full_log, json.dumps(record)
            ))
            
            # Update last processed timestamp
            if not self.last_processed_timestamp or timestamp > self.last_processed_timestamp:
                self.last_processed_timestamp = timestamp
            
            return True
            
        except Exception as e:
            logger.error(f"Error inserting record: {e}")
            logger.debug(f"Record data: {record}")
            return False
    
    def create_record_hash(self, record: Dict[str, Any]) -> str:
        """Create a unique hash for a record to detect duplicates."""
        import hashlib
        # Use timestamp + full_log + rule_id to create unique hash
        unique_string = f"{record.get('timestamp', '')}{record.get('full_log', '')}{record.get('rule', {}).get('id', '')}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def is_duplicate_record(self, record_hash: str, timestamp: str) -> bool:
        """Check if record already exists based on content hash and recent timestamp."""
        try:
            cursor = self.connection.cursor()
            # Check for records with same hash in the last hour to avoid far duplicates
            cursor.execute("""
                SELECT COUNT(*) FROM wazuh_archives 
                WHERE json_data LIKE ? AND timestamp >= datetime(?, '-1 hour')
            """, (f'%{record_hash[:8]}%', timestamp))
            
            result = cursor.fetchone()
            return result[0] > 0 if result else False
        except Exception as e:
            logger.debug(f"Error checking for duplicates: {e}")
            return False
    
    def batch_insert_records(self, records: List[Dict[str, Any]]) -> int:
        """Insert multiple records in a batch."""
        successful_inserts = 0
        
        try:
            for record in records:
                if self.insert_archive_record(record):
                    successful_inserts += 1
            
            self.connection.commit()
            
            # Update metadata
            self.connection.execute("""
                UPDATE fetch_metadata 
                SET last_fetch_time = datetime('now'), 
                    total_records = total_records + ?,
                    last_processed_timestamp = ?,
                    updated_at = datetime('now')
                WHERE id = 1
            """, (successful_inserts, self.last_processed_timestamp))
            
            self.connection.commit()
            logger.info(f"Successfully inserted {successful_inserts}/{len(records)} records")
            
        except Exception as e:
            logger.error(f"Error in batch insert: {e}")
            self.connection.rollback()
        
        return successful_inserts
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            cursor = self.connection.cursor()
            
            # Get total records
            cursor.execute("SELECT COUNT(*) FROM wazuh_archives")
            total_records = cursor.fetchone()[0]
            
            # Get last fetch info
            cursor.execute("SELECT last_fetch_time, total_records FROM fetch_metadata WHERE id = 1")
            metadata = cursor.fetchone()
            
            # Get latest record timestamp
            cursor.execute("SELECT MAX(timestamp) FROM wazuh_archives")
            latest_record = cursor.fetchone()[0]
            
            return {
                'total_records': total_records,
                'last_fetch_time': metadata[0] if metadata else None,
                'metadata_total': metadata[1] if metadata else 0,
                'latest_record_time': latest_record,
                'database_file': self.db_path
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

class WazuhDockerClient:
    """Handle Docker operations to fetch data from Wazuh Manager container."""
    
    def __init__(self):
        self.docker_client = None
        self.wazuh_container = None
        self.container_name = config.get('network.DOCKER_CONTAINER_NAME')
        self.archives_path = config.get('network.WAZUH_ARCHIVES_PATH')
        # Remove file position tracking - we'll use tail for newest records only
        
        self.connect_docker()
        self.find_wazuh_container()
    
    def connect_docker(self):
        """Connect to Docker daemon."""
        try:
            self.docker_client = docker.from_env()
            logger.info("Connected to Docker daemon")
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise
    
    def find_wazuh_container(self):
        """Find the Wazuh Manager container."""
        try:
            containers = self.docker_client.containers.list()
            for container in containers:
                if self.container_name in container.name:
                    self.wazuh_container = container
                    logger.info(f"Found Wazuh container: {container.name} ({container.id[:12]})")
                    return
            
            logger.error(f"Wazuh container '{self.container_name}' not found")
            raise Exception(f"Container {self.container_name} not found")
            
        except Exception as e:
            logger.error(f"Error finding container: {e}")
            raise
    
    def read_newest_archives(self, max_lines: int = 50) -> List[str]:
        """Read only the newest lines from archives.json file in container."""
        try:
            # Use tail to get only the newest lines
            exec_result = self.wazuh_container.exec_run(
                f"tail -n {max_lines} {self.archives_path}",
                stdout=True,
                stderr=True
            )
            
            if exec_result.exit_code == 0:
                content = exec_result.output.decode('utf-8')
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                logger.debug(f"Read {len(lines)} newest lines from archives file")
                return lines
            else:
                logger.warning(f"Failed to read archives file: {exec_result.output.decode('utf-8')}")
                return []
                
        except Exception as e:
            logger.error(f"Error reading newest archives: {e}")
            return []
    
    def get_file_size(self) -> int:
        """Get current size of archives.json file."""
        try:
            exec_result = self.wazuh_container.exec_run(
                f"wc -c {self.archives_path}",
                stdout=True,
                stderr=True
            )
            
            if exec_result.exit_code == 0:
                size_output = exec_result.output.decode('utf-8').strip()
                size = int(size_output.split()[0])
                return size
            
            return 0
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            return 0
    
    def check_file_has_new_data(self) -> bool:
        """Check if the archives file has been modified recently."""
        try:
            # Check if file was modified in the last 10 seconds
            exec_result = self.wazuh_container.exec_run(
                f"find {self.archives_path} -newermt '10 seconds ago'",
                stdout=True,
                stderr=True
            )
            
            if exec_result.exit_code == 0:
                output = exec_result.output.decode('utf-8').strip()
                return bool(output)  # Returns True if file was found (modified recently)
            
            return False
        except Exception as e:
            logger.debug(f"Error checking file modification: {e}")
            return True  # Default to true to attempt reading
    
    def parse_json_lines(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Parse JSON lines into dictionaries."""
        parsed_records = []
        
        for line in lines:
            try:
                if line:
                    record = json.loads(line)
                    parsed_records.append(record)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON line: {line[:100]}... Error: {e}")
                continue
        
        return parsed_records

class WazuhRealtimeServer:
    """Main server class for real-time Wazuh data fetching."""
    
    def __init__(self, fetch_interval: int = 5):
        self.fetch_interval = fetch_interval
        self.database = WazuhSQLiteDatabase()
        self.docker_client = WazuhDockerClient()
        self.running = False
        self.fetch_thread = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start the real-time fetching service."""
        logger.info("Starting Wazuh Real-time Data Fetcher...")
        self.running = True
        
        # Start fetching in separate thread
        self.fetch_thread = threading.Thread(target=self.fetch_loop, daemon=True)
        self.fetch_thread.start()
        
        # Print initial stats
        self.print_stats()
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(10)
                self.print_stats()
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()
    
    def fetch_loop(self):
        """Main fetching loop running in separate thread."""
        logger.info(f"Fetch loop started with interval: {self.fetch_interval}s")
        
        while self.running:
            try:
                # Check if file has been modified recently
                if self.docker_client.check_file_has_new_data():
                    logger.debug("Archives file has recent modifications, fetching newest records...")
                    
                    # Read newest lines only (last 50 lines should be enough for 5-second intervals)
                    lines = self.docker_client.read_newest_archives(max_lines=50)
                    
                    if lines:
                        # Parse JSON records
                        records = self.docker_client.parse_json_lines(lines)
                        
                        if records:
                            # Filter and insert new records only
                            new_records = self.filter_new_records(records)
                            
                            if new_records:
                                # Insert into database
                                inserted_count = self.database.batch_insert_records(new_records)
                                logger.info(f"Processed {len(lines)} lines, found {len(new_records)} new records, inserted {inserted_count}")
                            else:
                                logger.debug(f"All {len(records)} records were duplicates or old")
                        else:
                            logger.debug(f"No valid JSON records found in {len(lines)} lines")
                    else:
                        logger.debug("No new data available")
                else:
                    logger.debug("No recent file modifications detected")
                
            except Exception as e:
                logger.error(f"Error in fetch loop: {e}")
            
            # Wait before next fetch
            time.sleep(self.fetch_interval)
    
    def filter_new_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter records to only include new ones based on timestamp."""
        if not self.database.last_processed_timestamp:
            logger.info("No previous timestamp found, processing all records")
            return records
        
        new_records = []
        for record in records:
            timestamp = record.get('timestamp', '')
            if timestamp > self.database.last_processed_timestamp:
                new_records.append(record)
            else:
                logger.debug(f"Skipping old record with timestamp {timestamp}")
        
        return new_records
    
    def print_stats(self):
        """Print current statistics."""
        stats = self.database.get_stats()
        logger.info("="*50)
        logger.info("WAZUH REALTIME SERVER STATS")
        logger.info("="*50)
        logger.info(f"Total Records: {stats.get('total_records', 0)}")
        logger.info(f"Last Fetch: {stats.get('last_fetch_time', 'Never')}")
        logger.info(f"Latest Record: {stats.get('latest_record_time', 'None')}")
        logger.info(f"Database File: {stats.get('database_file', 'Unknown')}")
        logger.info(f"Last Processed Timestamp: {self.database.last_processed_timestamp or 'None'}")
        logger.info("="*50)
    
    def stop(self):
        """Stop the fetching service."""
        logger.info("Stopping Wazuh Real-time Data Fetcher...")
        self.running = False
        
        if self.fetch_thread and self.fetch_thread.is_alive():
            self.fetch_thread.join(timeout=10)
        
        self.database.close()
        logger.info("Service stopped")

def main():
    """Main entry point."""
    container_name = config.get('network.DOCKER_CONTAINER_NAME')
    archives_path = config.get('network.WAZUH_ARCHIVES_PATH')
    
    print("="*60)
    print("WAZUH REAL-TIME DATA FETCHER TO SQLITE3")
    print("="*60)
    print(f"Fetching data from: {archives_path}")
    print(f"Container: {container_name}")
    # Calculate database path using environment variables
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    database_dir = config.get('database.DATABASE_DIR')
    wazuh_db_name = config.get('database.WAZUH_DB_NAME')
    db_path = project_root / database_dir / wazuh_db_name
    print(f"Database: {db_path}")
    print("="*60)
    
    try:
        # Create server instance
        server = WazuhRealtimeServer(fetch_interval=5)  # Check every 5 seconds
        
        # Start the server
        server.start()
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
