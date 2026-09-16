"""
Supabase client initialization.

Provides a singleton Supabase client instance used across the backend.
"""

import os
from supabase import create_client, Client

_client: Client | None = None


def get_client() -> Client:
    """Get or create the Supabase client singleton."""
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env. "
                "Copy .env.example to .env and fill in your Supabase credentials."
            )
        _client = create_client(url, key)
    return _client
