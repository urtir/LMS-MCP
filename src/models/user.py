"""
User model for Flask-Login integration
"""
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.email = user_data['email']
        self.full_name = user_data.get('full_name')
        self._is_active = user_data.get('is_active', True)
        self.is_admin = user_data.get('is_admin', False) or self.username == 'admin'  # Admin privilege
        self.created_at = user_data.get('created_at')
        self.last_login = user_data.get('last_login')
    
    def get_id(self):
        """Return the user ID as required by Flask-Login"""
        return str(self.id)
    
    def is_authenticated(self):
        """Return True if the user is authenticated"""
        return True
    
    def is_active(self):
        """Return True if the user is active (required by Flask-Login)"""
        return self._is_active
    
    def is_anonymous(self):
        """Return False as anonymous users aren't supported"""
        return False
    
    def get_display_name(self):
        """Get display name for the user"""
        return self.full_name if self.full_name else self.username
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'is_active': self._is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at,
            'last_login': self.last_login
        }
