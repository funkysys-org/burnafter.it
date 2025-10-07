import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(32).hex())
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    # Supabase (Database only)
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

    # S3-Compatible Storage (Minio, AWS S3, etc.)
    S3_ENDPOINT_URL = os.environ.get('S3_ENDPOINT_URL')
    S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY')
    S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY')
    S3_BUCKET = os.environ.get('S3_BUCKET', 'burnafterit')
    S3_REGION = os.environ.get('S3_REGION', 'us-east-1')
    S3_USE_SSL = os.environ.get('S3_USE_SSL', 'True').lower() == 'true'
    S3_SIGNATURE_VERSION = os.environ.get('S3_SIGNATURE_VERSION', 's3v4')

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
        # Database is required
        required = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
        missing = [key for key in required if not os.environ.get(key)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        # Storage is required
        storage_required = ['S3_ENDPOINT_URL', 'S3_ACCESS_KEY', 'S3_SECRET_KEY']
        storage_missing = [key for key in storage_required if not os.environ.get(key)]
        if storage_missing:
            raise ValueError(f"Missing required S3 storage variables: {', '.join(storage_missing)}")
