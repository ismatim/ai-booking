"""Supabase database client initialization."""

from typing import Optional
from services.supabase_service import SupabaseService

_db_service: Optional[SupabaseService] = None


def get_db() -> SupabaseService:
    """Return a singleton instance of the SupabaseService wrapper."""
    global _db_service
    if _db_service is None:
        _db_service = SupabaseService()
    return _db_service
