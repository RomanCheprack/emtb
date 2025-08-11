#!/usr/bin/env python3
"""
Complete workflow script for scraping and migrating bike data
"""

import os
import sys
import subprocess
from pathlib import Path

def run_script(script_name, description):
    """Run a script and handle errors"""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    
    script_path = Path(__file__).parent / script_name
    
    try:
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout:
                print("Output:")
                print(result.stdout)
        else:
            print(f"❌ {description} failed with return code {result.returncode}")
            if result.stderr:
                print("Error output:")
                print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False
    
    return True

def main():
    """Run the complete workflow"""
    print("🚀 Starting EMTB data workflow...")
    
    # Step 1: Run all scrapers
    if not run_script("scrapers/run_all_scrapers.py", "Running all scrapers"):
        print("❌ Scraping failed, stopping workflow")
        return
    
    # Step 2: Standardize JSON files
    if not run_script("data/standardize_json.py", "Standardizing JSON files"):
        print("❌ Standardization failed, stopping workflow")
        return
    
    # Step 3: Migrate to database
    if not run_script("db/migrate_to_db.py", "Migrating data to database"):
        print("❌ Migration failed, stopping workflow")
        return
    
    print(f"\n{'='*60}")
    print("🎉 Workflow completed successfully!")
    print("📊 Your bike data is now updated in the database")
    print(f"{'='*60}")

if __name__ == "__main__":
    main() 