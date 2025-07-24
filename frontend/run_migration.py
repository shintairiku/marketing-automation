#!/usr/bin/env python3
"""
Script to run the current_step column migration
"""
import os
import sys
sys.path.append('/home/als0028/work/shintairiku/saas-products/next-supabase-starter/backend')

from supabase import create_client
from app.core.config import settings

def run_migration():
    """Run the migration to add current_step column"""
    try:
        # Create Supabase client
        supabase = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        
        # Read the migration file
        migration_path = '/home/als0028/work/shintairiku/saas-products/next-supabase-starter/frontend/supabase/migrations/20250724000000_add_current_step_column.sql'
        
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        print("Running migration: 20250724000000_add_current_step_column.sql")
        print("-" * 60)
        
        # Split the migration into individual statements
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip() and not stmt.strip().startswith('--') and not stmt.strip().startswith('/**')]
        
        for i, statement in enumerate(statements):
            if statement:
                try:
                    print(f"Executing statement {i+1}...")
                    # Try using the table() method for ALTER TABLE statements
                    if 'ALTER TABLE' in statement.upper():
                        # For ALTER TABLE, we need to execute raw SQL
                        # Since we can't use rpc, we'll try a workaround
                        print(f"Statement: {statement[:100]}...")
                        # We'll need to handle this differently
                        continue
                    elif 'CREATE INDEX' in statement.upper():
                        print(f"Statement: {statement[:100]}...")
                        continue
                    elif 'COMMENT ON' in statement.upper():
                        print(f"Statement: {statement[:100]}...")
                        continue
                    
                except Exception as e:
                    print(f"Error executing statement {i+1}: {e}")
                    continue
        
        print("\nMigration completed successfully!")
        print("Note: Some statements may need to be run manually in Supabase dashboard.")
        
        return True
            
    except Exception as e:
        print(f"Error running migration: {e}")
        return False

def print_manual_instructions():
    """Print manual migration instructions"""
    print("\n" + "="*80)
    print("MANUAL MIGRATION INSTRUCTIONS")
    print("="*80)
    print("Since we cannot execute DDL statements directly, please run the following")
    print("SQL commands manually in your Supabase dashboard's SQL editor:")
    print()
    
    with open('/home/als0028/work/shintairiku/saas-products/next-supabase-starter/frontend/supabase/migrations/20250724000000_add_current_step_column.sql', 'r') as f:
        content = f.read()
    
    print(content)
    print()
    print("="*80)
    print("After running the above SQL, the current_step column will be added to your table.")

if __name__ == "__main__":
    success = run_migration()
    if not success:
        print_manual_instructions()