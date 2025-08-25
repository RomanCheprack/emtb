#!/usr/bin/env python3
"""
Comprehensive pipeline script to process any new scraper data:
1. Standardize the data and add to standardized_data folder
2. Add the standardized data to all_bikes_standardized.json
3. Import the data into the database

This script automatically detects and processes any new scraper files.
"""

import os
import sys
import argparse

# Add the scripts directory to the Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def main():
    """Run the complete new scraper data processing pipeline"""
    parser = argparse.ArgumentParser(description='Process new scraper data pipeline')
    parser.add_argument('--scraper', '-s', type=str, help='Process specific scraper by name (e.g., rosen, cobra)')
    parser.add_argument('--all', '-a', action='store_true', help='Process all new scrapers (default)')
    parser.add_argument('--standardize-only', action='store_true', help='Only standardize data, skip database import')
    parser.add_argument('--import-only', action='store_true', help='Only import to database, skip standardization')
    
    args = parser.parse_args()
    
    print("🚀 Starting New Scraper Data Processing Pipeline")
    print("=" * 60)
    
    # Step 1: Standardize new scraper data
    if not args.import_only:
        print("\n📋 Step 1: Standardizing new scraper data...")
        try:
            from data.standardize_new_scrapers import process_all_new_scrapers, process_specific_scraper
            
            if args.scraper:
                print(f"Processing specific scraper: {args.scraper}")
                success = process_specific_scraper(args.scraper)
                if not success:
                    print(f"❌ Failed to standardize {args.scraper}")
                    if not args.standardize_only:
                        return
            else:
                print("Processing all new scrapers...")
                process_all_new_scrapers()
            
            print("✅ Step 1 completed successfully!")
        except Exception as e:
            print(f"❌ Error in Step 1: {e}")
            if not args.standardize_only:
                print("Please ensure the scraper has been run and the data file exists")
                return
    else:
        print("\n⏭️ Skipping standardization (import-only mode)")
    
    # Step 2: Import to database
    if not args.standardize_only:
        print("\n🗄️ Step 2: Importing standardized data to database...")
        try:
            from db.import_standardized_data import import_all_standardized_data, import_specific_scraper
            
            if args.scraper:
                print(f"Importing specific scraper: {args.scraper}")
                success = import_specific_scraper(args.scraper)
                if not success:
                    print(f"❌ Failed to import {args.scraper} to database")
                    return
            else:
                print("Importing all standardized scrapers...")
                import_all_standardized_data()
            
            print("✅ Step 2 completed successfully!")
        except Exception as e:
            print(f"❌ Error in Step 2: {e}")
            print("Please check the database connection and schema")
            return
    else:
        print("\n⏭️ Skipping database import (standardize-only mode)")
    
    print("\n🎉 New Scraper Data Processing Pipeline completed successfully!")
    print("=" * 60)
    print("Summary:")
    if not args.import_only:
        print("- New scraper data has been standardized and saved to standardized_data/")
        print("- Data has been added to all_bikes_standardized.json")
    if not args.standardize_only:
        print("- Standardized bikes have been added to the database")
    print("\nYou can now view the new bikes in your application!")

def show_usage_examples():
    """Show usage examples for the script"""
    print("\n📖 Usage Examples:")
    print("=" * 40)
    print()
    print("1. Process all new scrapers (recommended):")
    print("   python process_new_scrapers.py")
    print()
    print("2. Process a specific scraper:")
    print("   python process_new_scrapers.py --scraper rosen")
    print("   python process_new_scrapers.py -s cobra")
    print()
    print("3. Only standardize data (skip database import):")
    print("   python process_new_scrapers.py --standardize-only")
    print("   python process_new_scrapers.py --scraper rosen --standardize-only")
    print()
    print("4. Only import to database (skip standardization):")
    print("   python process_new_scrapers.py --import-only")
    print("   python process_new_scrapers.py --scraper rosen --import-only")
    print()
    print("5. Process all scrapers explicitly:")
    print("   python process_new_scrapers.py --all")
    print()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments provided, show usage examples
        show_usage_examples()
        print("Running with default settings (process all new scrapers)...")
        print()
    
    main()
