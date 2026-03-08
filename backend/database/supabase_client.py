"""
Supabase client initialization and utilities
"""
from typing import Optional
from supabase import create_client, Client
from config import get_settings

settings = get_settings()


class SupabaseClient:
    """Supabase client wrapper"""
    
    _instance: Optional[Client] = None
    _service_client: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get Supabase client with anon key"""
        if cls._instance is None:
            cls._instance = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
        return cls._instance
    
    @classmethod
    def get_service_client(cls) -> Client:
        """Get Supabase client with service role key"""
        if cls._service_client is None:
            cls._service_client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
        return cls._service_client


def get_supabase() -> Client:
    """Get Supabase client instance"""
    return SupabaseClient.get_client()


def get_service_supabase() -> Client:
    """Get Supabase service client instance"""
    return SupabaseClient.get_service_client()
