"""Apply the fix migration for snapshot functions directly to Supabase"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domains.seo_article.services.flow_service import get_supabase_client

def apply_fix_migration():
    """Apply the fix migration SQL directly"""

    # Read the migration file
    migration_path = Path(__file__).parent.parent.parent / "shared" / "supabase" / "migrations" / "20251002000001_fix_snapshot_functions.sql"

    with open(migration_path, 'r') as f:
        migration_sql = f.read()

    print(f"📄 Reading migration from: {migration_path}")
    print(f"\n{'='*60}")
    print("SQL to execute:")
    print(f"{'='*60}")
    print(migration_sql)
    print(f"{'='*60}\n")

    # Get Supabase client with service role
    supabase = get_supabase_client()

    try:
        # Execute the SQL directly
        print("🔧 Applying migration to Supabase...")
        result = supabase.rpc('exec_sql', {'sql': migration_sql}).execute()

        print("✅ Migration applied successfully!")
        print(f"Result: {result.data}")

    except Exception as e:
        print(f"❌ Error applying migration: {e}")

        # Try alternative approach - execute SQL as raw query
        print("\n🔄 Trying alternative approach...")
        try:
            # Split by semicolons and execute each statement
            statements = [s.strip() for s in migration_sql.split(';') if s.strip()]

            for i, stmt in enumerate(statements, 1):
                if stmt:
                    print(f"\n📝 Executing statement {i}/{len(statements)}...")
                    # Note: postgrest client doesn't support raw SQL execution
                    # We'll need to use psql or dashboard
                    print(f"Statement: {stmt[:100]}...")

            print("\n⚠️  Cannot execute raw SQL via Supabase client.")
            print("Please run this SQL in Supabase Dashboard SQL Editor:")
            print(f"\n{migration_sql}")

        except Exception as e2:
            print(f"❌ Alternative approach also failed: {e2}")

if __name__ == "__main__":
    apply_fix_migration()
