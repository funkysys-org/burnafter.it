from supabase import create_client, Client
from typing import Optional
from backend.config import Config

_supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """Get or create Supabase client singleton"""
    global _supabase_client

    if _supabase_client is None:
        _supabase_client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_ANON_KEY
        )

    return _supabase_client

def init_supabase():
    """Initialize Supabase client at app startup"""
    get_supabase_client()
