#!/usr/bin/env python3
"""
Database migration script to add user_id column to existing chat_sessions table
"""
import sqlite3
import uuid
from pathlib import Path

def migrate_database():
    """Migrate existing database to include user authentication support"""
    
    # Get database path
    current_dir = Path(__file__).parent
    db_path = current_dir / "data" / "chat_history.db"
    
    print(f"Migrating database at: {db_path}")
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        users_table_exists = cursor.fetchone() is not None
        
        if not users_table_exists:
            print("Creating users table...")
            cursor.execute('''
                CREATE TABLE users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
        
        # Check if user_id column exists in chat_sessions
        cursor.execute("PRAGMA table_info(chat_sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in columns:
            print("Adding user_id column to chat_sessions table...")
            
            # Create a default user for existing sessions
            default_user_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT OR IGNORE INTO users (id, username, email, password_hash, full_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (default_user_id, 'admin', 'admin@example.com', 
                  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewvV4tYktzHNOyPK', 'Default Admin'))
            
            # Add user_id column with default value
            cursor.execute('ALTER TABLE chat_sessions ADD COLUMN user_id TEXT')
            
            # Update existing sessions to use the default user
            cursor.execute('UPDATE chat_sessions SET user_id = ? WHERE user_id IS NULL', (default_user_id,))
            
            print(f"Updated existing chat sessions to use default user: {default_user_id}")
            print("Default login credentials:")
            print("Username: admin")
            print("Password: admin123")
        
        # Check if foreign key constraint exists, if not recreate table
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='chat_sessions'")
        table_sql = cursor.fetchone()
        
        if table_sql and 'FOREIGN KEY' not in table_sql[0]:
            print("Recreating chat_sessions table with foreign key constraint...")
            
            # Create backup table
            cursor.execute('''
                CREATE TABLE chat_sessions_backup AS 
                SELECT * FROM chat_sessions
            ''')
            
            # Drop original table
            cursor.execute('DROP TABLE chat_sessions')
            
            # Create new table with foreign key
            cursor.execute('''
                CREATE TABLE chat_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Restore data
            cursor.execute('''
                INSERT INTO chat_sessions 
                SELECT * FROM chat_sessions_backup
            ''')
            
            # Drop backup table
            cursor.execute('DROP TABLE chat_sessions_backup')
        
        # Create indexes if they don't exist
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_updated ON chat_sessions(updated_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON chat_sessions(user_id)')
        
        conn.commit()
        print("Database migration completed successfully!")

if __name__ == "__main__":
    migrate_database()
