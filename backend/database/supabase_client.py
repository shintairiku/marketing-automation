# -*- coding: utf-8 -*-
"""
Supabase client for backend operations
"""
from supabase import create_client, Client
from core.config import settings
import logging

logger = logging.getLogger(__name__)

def create_supabase_client() -> Client:
    """Create a Supabase client with service role key for backend operations"""
    try:
        supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        return supabase_client
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        raise

# Global client instance
supabase: Client = create_supabase_client()

def test_connection() -> bool:
    """Test Supabase connection"""
    try:
        # Simple test query to verify connection
        result = supabase.from_("company_info").select("id").limit(1).execute()
        logger.info("Supabase connection successful")
        return True
    except Exception as e:
        logger.error(f"Supabase connection test failed: {e}")
        return False