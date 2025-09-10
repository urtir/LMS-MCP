"""
Database models and operations for chat history and user authentication
"""
import sqlite3
import json
import uuid
import bcrypt
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

class ChatDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Get path relative to project root
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            db_path = str(project_root / "data" / "chat_history.db")
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
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
            
            # Create chat_sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create chat_messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tools_used TEXT,
                    thinking_process TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_updated ON chat_sessions(updated_at DESC)')
            
            conn.commit()
    
    def create_session(self, user_id: str, title: str = None) -> str:
        """Create a new chat session for a user"""
        session_id = str(uuid.uuid4())
        if not title:
            title = f"Chat Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chat_sessions (id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, user_id, title, datetime.now(), datetime.now()))
            conn.commit()
        
        return session_id
    
    def get_sessions(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get all chat sessions for a user ordered by most recent"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, created_at, updated_at, message_count
                FROM chat_sessions
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'id': row[0],
                    'title': row[1],
                    'created_at': row[2],
                    'updated_at': row[3],
                    'message_count': row[4]
                })
            
            return sessions
    
    def get_session(self, session_id: str, user_id: str = None) -> Optional[Dict]:
        """Get a specific session, optionally filtered by user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute('''
                    SELECT id, user_id, title, created_at, updated_at, message_count
                    FROM chat_sessions
                    WHERE id = ? AND user_id = ?
                ''', (session_id, user_id))
            else:
                cursor.execute('''
                    SELECT id, user_id, title, created_at, updated_at, message_count
                    FROM chat_sessions
                    WHERE id = ?
                ''', (session_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'title': row[2],
                    'created_at': row[3],
                    'updated_at': row[4],
                    'message_count': row[5]
                }
            return None
    
    def update_session_title(self, session_id: str, title: str):
        """Update session title"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE chat_sessions
                SET title = ?, updated_at = ?
                WHERE id = ?
            ''', (title, datetime.now(), session_id))
            conn.commit()
    
    def delete_session(self, session_id: str):
        """Delete a session and all its messages"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chat_sessions WHERE id = ?', (session_id,))
            conn.commit()
    
    def add_message(self, session_id: str, role: str, content: str, 
                   tools_used: List[Dict] = None, thinking_process: str = None) -> str:
        """Add a message to a session"""
        message_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert message
            cursor.execute('''
                INSERT INTO chat_messages (id, session_id, role, content, tools_used, thinking_process, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_id, session_id, role, content,
                json.dumps(tools_used) if tools_used else None,
                thinking_process,
                datetime.now()
            ))
            
            # Update session message count and updated_at
            cursor.execute('''
                UPDATE chat_sessions
                SET message_count = message_count + 1,
                    updated_at = ?
                WHERE id = ?
            ''', (datetime.now(), session_id))
            
            conn.commit()
        
        return message_id
    
    def get_messages(self, session_id: str, limit: int = 100) -> List[Dict]:
        """Get messages for a session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, role, content, tools_used, thinking_process, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ?
            ''', (session_id, limit))
            
            messages = []
            for row in cursor.fetchall():
                message = {
                    'id': row[0],
                    'role': row[1],
                    'content': row[2],
                    'tools_used': json.loads(row[3]) if row[3] else None,
                    'thinking_process': row[4],
                    'created_at': row[5]
                }
                messages.append(message)
            
            return messages
    
    def search_sessions(self, query: str, limit: int = 20) -> List[Dict]:
        """Search sessions by title or message content"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT s.id, s.title, s.created_at, s.updated_at, s.message_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.id = m.session_id
                WHERE s.title LIKE ? OR m.content LIKE ?
                ORDER BY s.updated_at DESC
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'id': row[0],
                    'title': row[1],
                    'created_at': row[2],
                    'updated_at': row[3],
                    'message_count': row[4]
                })
            
            return sessions
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total sessions
            cursor.execute('SELECT COUNT(*) FROM chat_sessions')
            total_sessions = cursor.fetchone()[0]
            
            # Total messages
            cursor.execute('SELECT COUNT(*) FROM chat_messages')
            total_messages = cursor.fetchone()[0]
            
            # Recent activity (last 7 days)
            cursor.execute('''
                SELECT COUNT(*) FROM chat_sessions
                WHERE created_at >= datetime('now', '-7 days')
            ''')
            recent_sessions = cursor.fetchone()[0]
            
            return {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'recent_sessions': recent_sessions
            }

    # User Authentication Methods
    def create_user(self, username: str, email: str, password: str, full_name: str = None) -> str:
        """Create a new user"""
        user_id = str(uuid.uuid4())
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (id, username, email, password_hash, full_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, email, password_hash, full_name))
            conn.commit()
        
        return user_id
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user by username and password"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, password_hash, full_name, is_active
                FROM users 
                WHERE username = ? AND is_active = 1
            ''', (username,))
            
            user = cursor.fetchone()
            if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
                # Update last login
                cursor.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
                ''', (user[0],))
                conn.commit()
                
                return {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'full_name': user[4],
                    'is_active': user[5]
                }
        
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, full_name, is_active, created_at, last_login
                FROM users 
                WHERE id = ? AND is_active = 1
            ''', (user_id,))
            
            user = cursor.fetchone()
            if user:
                return {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'full_name': user[3],
                    'is_active': user[4],
                    'created_at': user[5],
                    'last_login': user[6]
                }
        
        return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, full_name, is_active, created_at, last_login
                FROM users 
                WHERE username = ? AND is_active = 1
            ''', (username,))
            
            user = cursor.fetchone()
            if user:
                return {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'full_name': user[3],
                    'is_active': user[4],
                    'created_at': user[5],
                    'last_login': user[6]
                }
        
        return None
    
    def user_exists(self, username: str = None, email: str = None) -> bool:
        """Check if user exists by username or email"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if username:
                cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', (username,))
            elif email:
                cursor.execute('SELECT COUNT(*) FROM users WHERE email = ?', (email,))
            else:
                return False
            
            return cursor.fetchone()[0] > 0
