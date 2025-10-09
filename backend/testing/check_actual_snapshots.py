"""Check if any snapshots exist in the database"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domains.seo_article.services.flow_service import get_supabase_client

def check_snapshots():
    """Check for snapshots in the database"""
    supabase = get_supabase_client()

    print("="*80)
    print("CHECKING FOR ACTUAL SNAPSHOTS IN DATABASE")
    print("="*80)

    # Get all snapshots
    try:
        result = supabase.table('article_generation_step_snapshots').select('*').execute()

        if result.data:
            print(f"\n✅ Found {len(result.data)} snapshot(s):")
            for snapshot in result.data:
                print(f"\n  Snapshot ID: {snapshot['id']}")
                print(f"  Process ID: {snapshot['process_id']}")
                print(f"  Step: {snapshot['step_name']}")
                print(f"  Created: {snapshot['created_at']}")
                print(f"  Description: {snapshot.get('step_description', 'N/A')}")
                print(f"  Can Restore: {snapshot.get('can_restore', 'N/A')}")
        else:
            print("\n❌ No snapshots found in database")

    except Exception as e:
        print(f"\n❌ Error checking snapshots: {e}")

    # Also check recent processes
    print("\n" + "="*80)
    print("CHECKING RECENT PROCESSES")
    print("="*80)

    try:
        result = supabase.table('generated_articles_state').select('id, user_id, created_at').order('created_at', desc=True).limit(5).execute()

        if result.data:
            print(f"\n✅ Found {len(result.data)} recent process(es):")
            for process in result.data:
                print(f"\n  Process ID: {process['id']}")
                print(f"  User ID: {process['user_id']}")
                print(f"  Created: {process['created_at']}")

                # Check snapshots for this process
                snap_result = supabase.table('article_generation_step_snapshots').select('id, step_name').eq('process_id', process['id']).execute()
                if snap_result.data:
                    print(f"  Snapshots: {len(snap_result.data)} - Steps: {[s['step_name'] for s in snap_result.data]}")
                else:
                    print(f"  Snapshots: 0")
        else:
            print("\n❌ No recent processes found")

    except Exception as e:
        print(f"\n❌ Error checking processes: {e}")

    print("\n" + "="*80)

if __name__ == "__main__":
    check_snapshots()
