#!/usr/bin/env python3
"""
Generic script to standardize any new scraper data and add it to standardized_data folder
and all_bikes_standardized.json

This script automatically detects new scraper files and processes them.
"""

import json
import os
import sys
import glob

# Add the scripts directory to the Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.join(current_dir, '..')
sys.path.insert(0, scripts_dir)

from data.standardize_json import standardize_bike_data
from utils import clean_bike_field_value

def get_new_scraper_files():
    """Get list of new scraper files that haven't been standardized yet"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    raw_data_dir = os.path.join(current_dir, '..', '..', 'data', 'scraped_raw_data')
    standardized_data_dir = os.path.join(current_dir, '..', '..', 'data', 'standardized_data')
    
    # Get all JSON files in raw_data_dir (excluding already standardized ones)
    raw_files = glob.glob(os.path.join(raw_data_dir, "*.json"))
    
    # Get list of already standardized files
    standardized_files = []
    if os.path.exists(standardized_data_dir):
        standardized_files = [f.replace("standardized_", "") for f in os.listdir(standardized_data_dir) 
                            if f.startswith("standardized_") and f.endswith(".json")]
    
    # Find new files that haven't been standardized yet
    new_files = []
    for raw_file in raw_files:
        filename = os.path.basename(raw_file)
        # Skip files that are not scraper data
        if filename in ['compare_counts.json', 'posts.json']:
            continue
        
        # Check if this file has already been standardized
        if filename not in standardized_files:
            new_files.append(raw_file)
    
    return new_files

def standardize_scraper_data(raw_file_path):
    """Standardize a single scraper data file"""
    filename = os.path.basename(raw_file_path)
    scraper_name = filename.replace('.json', '')
    
    print(f"\n=== Processing {scraper_name} Data ===")
    print(f"Raw file: {raw_file_path}")
    
    try:
        # Read raw data
        with open(raw_file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        print(f"Found {len(raw_data)} bikes in {scraper_name} data")
        
        # Standardize each bike
        standardized_bikes = []
        for i, bike in enumerate(raw_data):
            print(f"Standardizing bike {i+1}/{len(raw_data)}: {bike.get('model', 'Unknown')}")
            standardized_bike = standardize_bike_data(bike)
            standardized_bikes.append(standardized_bike)
        
        return standardized_bikes, scraper_name
        
    except Exception as e:
        print(f"Error processing {scraper_name} data: {e}")
        return None, scraper_name

def save_standardized_data(standardized_bikes, scraper_name):
    """Save standardized data to individual file"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    standardized_data_dir = os.path.join(current_dir, '..', '..', 'data', 'standardized_data')
    
    # Create standardized_data directory if it doesn't exist
    os.makedirs(standardized_data_dir, exist_ok=True)
    
    # Save standardized data
    standardized_file = os.path.join(standardized_data_dir, f"standardized_{scraper_name}.json")
    with open(standardized_file, 'w', encoding='utf-8') as f:
        json.dump(standardized_bikes, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Saved standardized {scraper_name} data: {standardized_file}")
    print(f"   Original bikes: {len(standardized_bikes)}")
    print(f"   Standardized bikes: {len(standardized_bikes)}")
    
    return standardized_file

def update_all_bikes_standardized(new_bikes, scraper_name):
    """Add new bikes to all_bikes_standardized.json"""
    print(f"\n=== Updating all_bikes_standardized.json with {scraper_name} data ===")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    standardized_data_dir = os.path.join(current_dir, '..', '..', 'data', 'standardized_data')
    all_bikes_file = os.path.join(standardized_data_dir, "all_bikes_standardized.json")
    
    # Load existing all_bikes_standardized.json if it exists
    existing_bikes = []
    if os.path.exists(all_bikes_file):
        print(f"Loading existing all_bikes_standardized.json...")
        with open(all_bikes_file, 'r', encoding='utf-8') as f:
            existing_bikes = json.load(f)
        print(f"Found {len(existing_bikes)} existing bikes")
    
    # Add source_file field to new bikes
    for bike in new_bikes:
        bike['source_file'] = f'{scraper_name}.json'
    
    # Check for duplicates based on product_url
    existing_urls = {bike.get('product_url', '') for bike in existing_bikes}
    new_unique_bikes = []
    duplicates = 0
    
    for bike in new_bikes:
        product_url = bike.get('product_url', '')
        if product_url and product_url in existing_urls:
            print(f"⚠️ Skipping duplicate bike: {bike.get('model', 'Unknown')} - URL already exists")
            duplicates += 1
        else:
            new_unique_bikes.append(bike)
            if product_url:
                existing_urls.add(product_url)
    
    # Combine existing and new bikes
    all_bikes = existing_bikes + new_unique_bikes
    
    # Save updated all_bikes_standardized.json
    with open(all_bikes_file, 'w', encoding='utf-8') as f:
        json.dump(all_bikes, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Updated all_bikes_standardized.json")
    print(f"   Previous total: {len(existing_bikes)}")
    print(f"   New bikes added: {len(new_unique_bikes)}")
    print(f"   Duplicates skipped: {duplicates}")
    print(f"   New total: {len(all_bikes)}")
    
    return len(new_unique_bikes), duplicates

def process_all_new_scrapers():
    """Process all new scraper files that haven't been standardized yet"""
    print("🔍 Scanning for new scraper data files...")
    
    new_files = get_new_scraper_files()
    
    if not new_files:
        print("✅ No new scraper files found. All existing files have been standardized.")
        return
    
    print(f"Found {len(new_files)} new scraper files to process:")
    for file_path in new_files:
        print(f"  - {os.path.basename(file_path)}")
    
    total_processed = 0
    total_added = 0
    total_duplicates = 0
    
    for raw_file_path in new_files:
        # Standardize the data
        standardized_bikes, scraper_name = standardize_scraper_data(raw_file_path)
        
        if standardized_bikes is None:
            print(f"❌ Failed to process {scraper_name}, skipping...")
            continue
        
        # Save standardized data
        save_standardized_data(standardized_bikes, scraper_name)
        
        # Update all_bikes_standardized.json
        added_count, duplicates = update_all_bikes_standardized(standardized_bikes, scraper_name)
        
        total_processed += 1
        total_added += added_count
        total_duplicates += duplicates
    
    print(f"\n🎉 Processing complete!")
    print(f"   Files processed: {total_processed}")
    print(f"   Total bikes added: {total_added}")
    print(f"   Total duplicates skipped: {total_duplicates}")

def process_specific_scraper(scraper_name):
    """Process a specific scraper by name"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    raw_data_dir = os.path.join(current_dir, '..', '..', 'data', 'scraped_raw_data')
    raw_file_path = os.path.join(raw_data_dir, f"{scraper_name}.json")
    
    if not os.path.exists(raw_file_path):
        print(f"❌ Scraper file not found: {raw_file_path}")
        return False
    
    # Standardize the data
    standardized_bikes, scraper_name = standardize_scraper_data(raw_file_path)
    
    if standardized_bikes is None:
        print(f"❌ Failed to process {scraper_name}")
        return False
    
    # Save standardized data
    save_standardized_data(standardized_bikes, scraper_name)
    
    # Update all_bikes_standardized.json
    added_count, duplicates = update_all_bikes_standardized(standardized_bikes, scraper_name)
    
    print(f"\n✅ Successfully processed {scraper_name}")
    print(f"   Bikes added: {added_count}")
    print(f"   Duplicates skipped: {duplicates}")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Standardize new scraper data')
    parser.add_argument('--scraper', '-s', type=str, help='Process specific scraper by name (e.g., rosen, cobra)')
    parser.add_argument('--all', '-a', action='store_true', help='Process all new scrapers (default)')
    
    args = parser.parse_args()
    
    if args.scraper:
        print(f"Processing specific scraper: {args.scraper}")
        process_specific_scraper(args.scraper)
    else:
        print("Processing all new scrapers...")
        process_all_new_scrapers()
