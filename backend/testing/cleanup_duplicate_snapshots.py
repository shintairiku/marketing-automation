"""Clean up duplicate snapshots (keep only index=1 for each step/branch)"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domains.seo_article.services.flow_service import get_supabase_client

def cleanup_duplicate_snapshots():
    """Delete duplicate snapshots, keep only the first one (index=1) for each step/branch"""
    supabase = get_supabase_client()

    print("="*80)
    print("CLEANING UP DUPLICATE SNAPSHOTS")
    print("="*80)

    # Get all snapshots
    try:
        result = supabase.table('article_generation_step_snapshots').select('*').order('created_at').execute()

        if not result.data:
            print("\n✅ No snapshots found")
            return

        # Group by (process_id, step_name, branch_id)
        groups = {}
        for snapshot in result.data:
            key = (snapshot['process_id'], snapshot['step_name'], snapshot['branch_id'])
            if key not in groups:
                groups[key] = []
            groups[key].append(snapshot)

        total_deleted = 0
        for key, snapshots in groups.items():
            if len(snapshots) > 1:
                print(f"\n📦 Process: {key[0][:8]}..., Step: {key[1]}, Branch: {key[2][:8]}...")
                print(f"   Found {len(snapshots)} duplicates")

                # Keep the first one (lowest index or earliest created)
                snapshots.sort(key=lambda s: (s['step_index'], s['created_at']))
                keep = snapshots[0]
                delete = snapshots[1:]

                print(f"   ✅ Keeping: index={keep['step_index']}, created={keep['created_at']}")

                for snap in delete:
                    print(f"   🗑️  Deleting: index={snap['step_index']}, created={snap['created_at']}")
                    supabase.table('article_generation_step_snapshots').delete().eq('id', snap['id']).execute()
                    total_deleted += 1

        if total_deleted > 0:
            print(f"\n✅ Successfully deleted {total_deleted} duplicate snapshots")
        else:
            print(f"\n✅ No duplicate snapshots found")

    except Exception as e:
        print(f"\n❌ Error: {e}")

    print("\n" + "="*80)

if __name__ == "__main__":
    cleanup_duplicate_snapshots()
