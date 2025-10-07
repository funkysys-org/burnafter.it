import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(32).hex())
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    # Supabase
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')

    # Upload limits
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB

    # Rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = "memory://"

    @staticmethod
    def validate():
        """Validate required configuration"""
        required = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
        missing = [key for key in required if not os.environ.get(key)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
