"""Clean up invalid snapshots (wrong step names)"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domains.seo_article.services.flow_service import get_supabase_client

def cleanup_invalid_snapshots():
    """Delete snapshots with incorrect step names"""
    supabase = get_supabase_client()

    print("="*80)
    print("CLEANING UP INVALID SNAPSHOTS")
    print("="*80)

    # Valid snapshot steps (only 3 allowed)
    VALID_STEPS = {'persona_generated', 'theme_proposed', 'outline_generated'}

    # Get all snapshots
    try:
        result = supabase.table('article_generation_step_snapshots').select('*').execute()

        if not result.data:
            print("\n✅ No snapshots found")
            return

        invalid_snapshots = []
        valid_snapshots = []

        for snapshot in result.data:
            if snapshot['step_name'] in VALID_STEPS:
                valid_snapshots.append(snapshot)
            else:
                invalid_snapshots.append(snapshot)

        print(f"\n📊 Total snapshots: {len(result.data)}")
        print(f"✅ Valid snapshots: {len(valid_snapshots)}")
        print(f"❌ Invalid snapshots: {len(invalid_snapshots)}")

        if invalid_snapshots:
            print(f"\n⚠️  Deleting {len(invalid_snapshots)} invalid snapshot(s)...")
            for snapshot in invalid_snapshots:
                print(f"  🗑️  Deleting: {snapshot['id']} (step: {snapshot['step_name']})")
                supabase.table('article_generation_step_snapshots').delete().eq('id', snapshot['id']).execute()

            print(f"\n✅ Successfully deleted {len(invalid_snapshots)} invalid snapshots")

        if valid_snapshots:
            print(f"\n✅ Valid snapshots remaining:")
            for snapshot in valid_snapshots:
                print(f"  📸 {snapshot['step_name']} - Process: {snapshot['process_id'][:8]}... - Created: {snapshot['created_at']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")

    print("\n" + "="*80)

if __name__ == "__main__":
    cleanup_invalid_snapshots()
