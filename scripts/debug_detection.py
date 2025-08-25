#!/usr/bin/env python3
"""
Debug script to test file detection logic
"""

import os
import glob

def get_new_scraper_files():
    """Get list of new scraper files that haven't been standardized yet"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    raw_data_dir = os.path.join(current_dir, '..', 'data', 'scraped_raw_data')
    standardized_data_dir = os.path.join(current_dir, '..', 'data', 'standardized_data')
    
    print(f"Raw data directory: {raw_data_dir}")
    print(f"Standardized data directory: {standardized_data_dir}")
    
    # Get all JSON files in raw_data_dir (excluding already standardized ones)
    raw_files = glob.glob(os.path.join(raw_data_dir, "*.json"))
    print(f"Raw files found: {len(raw_files)}")
    for f in raw_files:
        print(f"  - {os.path.basename(f)}")
    
    # Get list of already standardized files
    standardized_files = []
    if os.path.exists(standardized_data_dir):
        standardized_files = [f.replace("standardized_", "") for f in os.listdir(standardized_data_dir) 
                            if f.startswith("standardized_") and f.endswith(".json")]
    
    print(f"Standardized files found: {len(standardized_files)}")
    for f in standardized_files:
        print(f"  - {f}")
    
    # Find new files that haven't been standardized yet
    new_files = []
    for raw_file in raw_files:
        filename = os.path.basename(raw_file)
        # Skip files that are not scraper data
        if filename in ['compare_counts.json', 'posts.json']:
            print(f"Skipping non-scraper file: {filename}")
            continue
        
        # Check if this file has already been standardized
        if filename not in standardized_files:
            new_files.append(raw_file)
            print(f"Adding as new file: {filename}")
        else:
            print(f"Already standardized: {filename}")
    
    return new_files

# Test the function
new_files = get_new_scraper_files()
print(f"\nFinal result: {len(new_files)} new files to process")
for f in new_files:
    print(f"  - {os.path.basename(f)}")
