#!/usr/bin/env python3
"""
Helper script to run organized scripts easily
Usage: python scripts/run.py <category> <script_name>
"""

import sys
import os
import subprocess
from pathlib import Path

def show_help():
    """Show available scripts and usage"""
    print("""
🚀 EMTB Scripts Runner

Usage: python scripts/run.py <category> <script_name>

Available categories and scripts:

🗄️  DATABASE (db):
  - migrate_to_db.py          - Migrate JSON data to database
  - migrate_database_schema.py - Run database schema migrations
  - recreate_bikes_table.py   - Recreate bikes table with current schema

📊  DATA PROCESSING (data):
  - standardize_json.py       - Standardize scraped JSON data
  - migrate_compare_counts.py - Migrate comparison statistics

🕷️  SCRAPERS (scrapers):
  - run_all_scrapers.py       - Run all web scrapers

🔧  MAINTENANCE (maintenance):
  - fix_database_quotes.py    - Fix problematic characters in database
  - fix_bike_ids.py          - Clean bike IDs

📋  WORKFLOW:
  - workflow.py              - Run complete data pipeline

Examples:
  python scripts/run.py db migrate_to_db
  python scripts/run.py data standardize_json
  python scripts/run.py maintenance fix_database_quotes
  python scripts/run.py workflow
""")

def run_script(category, script_name):
    """Run a specific script"""
    script_path = Path(__file__).parent / category / f"{script_name}.py"
    
    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return False
    
    print(f"🚀 Running: {category}/{script_name}.py")
    print(f"📁 Path: {script_path}")
    print("=" * 60)
    
    try:
        # Change to scripts directory to ensure proper imports
        original_dir = os.getcwd()
        os.chdir(Path(__file__).parent)
        
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=False, text=True)
        
        os.chdir(original_dir)
        
        if result.returncode == 0:
            print("=" * 60)
            print(f"✅ {script_name}.py completed successfully")
            return True
        else:
            print("=" * 60)
            print(f"❌ {script_name}.py failed with return code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error running {script_name}.py: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    if sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
        return
    
    if len(sys.argv) == 2:
        # Single argument - could be workflow or help
        if sys.argv[1] == 'workflow':
            run_script('', 'workflow')
        else:
            print(f"❌ Unknown command: {sys.argv[1]}")
            show_help()
        return
    
    if len(sys.argv) == 3:
        category = sys.argv[1]
        script_name = sys.argv[2]
        
        # Validate category
        valid_categories = ['db', 'data', 'scrapers', 'maintenance']
        if category not in valid_categories:
            print(f"❌ Invalid category: {category}")
            print(f"Valid categories: {', '.join(valid_categories)}")
            return
        
        run_script(category, script_name)
        return
    
    print("❌ Invalid number of arguments")
    show_help()

if __name__ == "__main__":
    main()
