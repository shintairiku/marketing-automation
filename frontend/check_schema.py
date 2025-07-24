#!/usr/bin/env python3
"""
Script to check the current schema of generated_articles_state table
"""
import os
import sys
sys.path.append('/home/als0028/work/shintairiku/saas-products/next-supabase-starter/backend')

from supabase import create_client
from app.core.config import settings

def check_schema():
    """Check the current schema of generated_articles_state table"""
    try:
        # Create Supabase client
        supabase = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        
        # Try to get a sample record to understand the schema
        try:
            result = supabase.from_('generated_articles_state').select('*').limit(1).execute()
            
            if result.data:
                sample_record = result.data[0]
                existing_columns = list(sample_record.keys())
            else:
                # If no data, try to insert and rollback to see schema
                try:
                    test_result = supabase.from_('generated_articles_state').select('*').limit(0).execute()
                    # This will fail but might give us column info
                    existing_columns = []
                except Exception as e:
                    print(f"No data found in table, trying alternative method...")
                    existing_columns = []
                    
        except Exception as e:
            print(f"Could not access table directly: {e}")
            existing_columns = []
        
        print("Current schema for generated_articles_state table:")
        print("-" * 60)
        
        if existing_columns:
            print("Found columns:")
            for col in sorted(existing_columns):
                print(f"  - {col}")
        else:
            print("Could not determine column structure from sample data")
        
        # Check for specific required columns
        required_columns = [
            'current_step',
            'current_step_name', 
            'progress_percentage',
            'is_waiting_for_input',
            'input_type',
            'auto_resume_eligible',
            'step_history',
            'process_metadata'
        ]
        
        # existing_columns is already set above
        
        print("\n" + "="*60)
        print("Required columns status:")
        print("="*60)
        
        missing_columns = []
        for col in required_columns:
            if col in existing_columns:
                print(f"✅ {col} - EXISTS")
            else:
                print(f"❌ {col} - MISSING")
                missing_columns.append(col)
        
        if missing_columns:
            print(f"\nMissing columns: {', '.join(missing_columns)}")
            return missing_columns
        else:
            print("\n✅ All required columns are present!")
            return []
            
    except Exception as e:
        print(f"Error checking schema: {e}")
        return None

if __name__ == "__main__":
    missing = check_schema()
    if missing:
        print(f"\nYou need to add the following columns: {missing}")
    elif missing is None:
        print("\nError occurred while checking schema")
    else:
        print("\nSchema check completed successfully!")