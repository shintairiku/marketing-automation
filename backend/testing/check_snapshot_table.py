#!/usr/bin/env python3
"""
Check if article_generation_step_snapshots table and functions exist
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings
from app.domains.seo_article.services.flow_service import get_supabase_client

def main():
    print("=" * 80)
    print("CHECKING SNAPSHOT TABLE AND FUNCTIONS")
    print("=" * 80)

    supabase = get_supabase_client()

    # 1. Check if table exists by trying to query it
    print("\n1. Checking if article_generation_step_snapshots table exists...")
    try:
        result = supabase.table("article_generation_step_snapshots").select("id").limit(1).execute()
        print("✅ Table exists!")
        print(f"   Response: {result}")
    except Exception as e:
        print(f"❌ Table does not exist or error: {e}")
        return

    # 2. Check if save_step_snapshot function exists
    print("\n2. Checking if save_step_snapshot function exists...")
    try:
        # Try to call with dummy data (will fail validation but proves function exists)
        result = supabase.rpc(
            'save_step_snapshot',
            {
                'p_process_id': '00000000-0000-0000-0000-000000000000',
                'p_step_name': 'test',
                'p_article_context': {},
                'p_step_description': 'test',
                'p_step_category': 'test',
                'p_snapshot_metadata': {}
            }
        ).execute()
        print("✅ Function save_step_snapshot exists!")
        print(f"   Response: {result}")
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg or "unknown function" in error_msg.lower():
            print(f"❌ Function save_step_snapshot does not exist: {e}")
        else:
            print(f"✅ Function exists (failed with validation error as expected): {e}")

    # 3. Check if get_available_snapshots function exists
    print("\n3. Checking if get_available_snapshots function exists...")
    try:
        result = supabase.rpc(
            'get_available_snapshots',
            {'p_process_id': '00000000-0000-0000-0000-000000000000'}
        ).execute()
        print("✅ Function get_available_snapshots exists!")
        print(f"   Response: {result}")
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg or "unknown function" in error_msg.lower():
            print(f"❌ Function get_available_snapshots does not exist: {e}")
        else:
            print(f"✅ Function exists: {e}")

    # 4. Check if restore_from_snapshot function exists
    print("\n4. Checking if restore_from_snapshot function exists...")
    try:
        result = supabase.rpc(
            'restore_from_snapshot',
            {'p_snapshot_id': '00000000-0000-0000-0000-000000000000'}
        ).execute()
        print("✅ Function restore_from_snapshot exists!")
        print(f"   Response: {result}")
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg or "unknown function" in error_msg.lower():
            print(f"❌ Function restore_from_snapshot does not exist: {e}")
        else:
            print(f"✅ Function exists (failed with validation error as expected): {e}")

    print("\n" + "=" * 80)
    print("CHECK COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
