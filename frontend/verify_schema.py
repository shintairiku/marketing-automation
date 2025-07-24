#!/usr/bin/env python3
"""
Script to verify that all required columns exist after migration
"""
import os
import sys
sys.path.append('/home/als0028/work/shintairiku/saas-products/next-supabase-starter/backend')

from supabase import create_client
from app.core.config import settings

def verify_schema():
    """Verify that all required columns exist in generated_articles_state table"""
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
                # If no data, we'll assume columns exist if we can select them
                test_result = supabase.from_('generated_articles_state').select('current_step').limit(1).execute()
                existing_columns = ['current_step']  # If this doesn't fail, column exists
                
                # Try to get all columns by attempting to select them
                all_columns = [
                    'current_step', 'current_step_name', 'progress_percentage',
                    'is_waiting_for_input', 'input_type', 'auto_resume_eligible',
                    'step_history', 'process_metadata', 'id', 'user_id', 'status'
                ]
                
                for col in all_columns:
                    try:
                        supabase.from_('generated_articles_state').select(col).limit(1).execute()
                        if col not in existing_columns:
                            existing_columns.append(col)
                    except:
                        pass
                    
        except Exception as e:
            print(f"Could not access table directly: {e}")
            existing_columns = []
        
        print("Schema verification for generated_articles_state table:")
        print("=" * 60)
        
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
        
        print("Required columns status:")
        print("-" * 40)
        
        all_present = True
        missing_columns = []
        
        for col in required_columns:
            if col in existing_columns:
                print(f"✅ {col:<25} - EXISTS")
            else:
                print(f"❌ {col:<25} - MISSING")
                all_present = False
                missing_columns.append(col)
        
        print("\n" + "=" * 60)
        
        if all_present:
            print("🎉 SUCCESS: All required columns are present!")
            print("The generated_articles_state table is ready for use.")
            return True
        else:
            print(f"⚠️  WARNING: Missing columns: {', '.join(missing_columns)}")
            print("Please run the migration manually in Supabase dashboard.")
            return False
            
    except Exception as e:
        print(f"Error verifying schema: {e}")
        return False

if __name__ == "__main__":
    success = verify_schema()
    if success:
        print("\n✅ Schema verification completed successfully!")
    else:
        print("\n❌ Schema verification failed. Manual intervention required.")