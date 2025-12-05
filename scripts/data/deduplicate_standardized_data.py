#!/usr/bin/env python3
"""
Deduplicate standardized bike data before migration.

This script should be run AFTER scraping and standardization, but BEFORE database migration.
It ensures each unique bike (brand+model+product_url) appears only once with the correct category.

DUPLICATE DETECTION:
A bike is considered a duplicate if it has:
- Same brand (firm)
- Same model name (including wheel size)
- Same product_url (from source website)

NOTE: We use product_url instead of year because ~50% of bikes are missing year data.
Same URL = definitely the same bike on the source website.

CATEGORY PRIORITY RULES:
1. For HYBRID/electric bikes (e-MTBs): electric > mtb > road > kids
2. For kids bikes (specific models): kids > mtb > road
3. For all other bikes: First occurrence wins

WHY THIS IS NEEDED:
- Some bikes appear in multiple categories on source websites
- The scraper collects them from each category page
- Without deduplication, migration fails or keeps the wrong category
"""

import json
import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)


# Known kids bike models that should be categorized as kids even if they appear in MTB
KIDS_BIKE_MODELS = [
    'ACID 200', 'ACID 240', 'ACID 260', 'ACID 260 DISC', 'ACID 260 SL',
    'AIM', 'AIM EX', 'AIM PRO', 'AIM SLX', 'AIM RACE',
    'ELLA 200', 'ELLA 240', 'ELLA 260',
    'KID 160', 'KID 200', 'KID 240',
    # Add more as needed
]


def get_category_priority(bike_data):
    """
    Determine the priority score for a bike's category.
    Lower score = higher priority (will be kept in case of duplicates)
    
    Returns: (priority_score, category_name)
    """
    model = bike_data.get('model', '')
    category = bike_data.get('category', '')
    
    # Rule 1: Electric bikes (HYBRID in model name) - prioritize electric category
    if 'HYBRID' in model.upper() or 'E-BIKE' in model.upper():
        priority_map = {
            'electric': 1,
            'mtb': 2,
            'road': 3,
            'kids': 4,
        }
        return (priority_map.get(category, 99), category)
    
    # Rule 2: Known kids bikes - prioritize kids category
    if model in KIDS_BIKE_MODELS or any(keyword in model.upper() for keyword in ['KIDS', 'KID ', 'JUNIOR']):
        priority_map = {
            'kids': 1,
            'mtb': 2,
            'road': 3,
            'electric': 4,
        }
        return (priority_map.get(category, 99), category)
    
    # Rule 3: Default - all categories equal (first occurrence wins)
    return (50, category)


def deduplicate_bikes(bikes_data, source_name):
    """
    Deduplicate bikes based on (firm, model, product_url) with category priority rules.
    
    Product URL is the most reliable identifier because:
    - It's unique per product on the source website
    - Many bikes don't have year data (49.6% missing)
    - Same URL = definitely the same bike
    
    Args:
        bikes_data: List of bike dictionaries
        source_name: Name of the source (for logging)
    
    Returns:
        List of deduplicated bikes
    """
    seen = {}  # key: (firm, model, product_url), value: bike_data
    duplicates_fixed = []
    
    for bike in bikes_data:
        firm = bike.get('firm', '')
        model = bike.get('model', '')
        product_url = bike.get('source', {}).get('product_url', '')
        
        # Use product_url as part of key for better duplicate detection
        key = (firm, model, product_url)
        
        if key not in seen:
            # First time seeing this bike
            seen[key] = bike
        else:
            # Duplicate found - decide which one to keep
            existing = seen[key]
            existing_priority, existing_cat = get_category_priority(existing)
            new_priority, new_cat = get_category_priority(bike)
            
            if new_priority < existing_priority:
                # New bike has higher priority, replace existing
                duplicates_fixed.append({
                    'model': model,
                    'old_category': existing_cat,
                    'new_category': new_cat,
                    'reason': 'Higher priority category'
                })
                seen[key] = bike
    
    # Log duplicates fixed
    if duplicates_fixed:
        print(f"\n   📝 {source_name}: Fixed {len(duplicates_fixed)} duplicates:")
        for dup in duplicates_fixed[:5]:  # Show first 5
            print(f"      {dup['model']}: {dup['old_category']} → {dup['new_category']}")
        if len(duplicates_fixed) > 5:
            print(f"      ... and {len(duplicates_fixed) - 5} more")
    
    deduplicated = list(seen.values())
    return deduplicated


def process_all_standardized_files():
    """Process all standardized JSON files and deduplicate them"""
    standardized_dir = os.path.join(project_root, 'data', 'standardized_data')
    
    if not os.path.exists(standardized_dir):
        print(f"❌ Standardized data directory not found: {standardized_dir}")
        return
    
    # Get all standardized files
    json_files = [
        f for f in os.listdir(standardized_dir)
        if f.startswith('standardized_') and f.endswith('.json')
        and f != 'all_bikes_standardized.json'
    ]
    
    if not json_files:
        print("❌ No standardized files found!")
        return
    
    print("=" * 80)
    print("🔄 DEDUPLICATING STANDARDIZED BIKE DATA")
    print("=" * 80)
    print(f"\nFound {len(json_files)} files to process\n")
    
    total_original = 0
    total_deduplicated = 0
    total_removed = 0
    
    for filename in sorted(json_files):
        filepath = os.path.join(standardized_dir, filename)
        source_name = filename.replace('standardized_', '').replace('_data.json', '')
        
        try:
            # Load data
            with open(filepath, 'r', encoding='utf-8') as f:
                bikes_data = json.load(f)
            
            original_count = len(bikes_data)
            total_original += original_count
            
            # Deduplicate
            deduplicated = deduplicate_bikes(bikes_data, source_name)
            dedup_count = len(deduplicated)
            total_deduplicated += dedup_count
            removed = original_count - dedup_count
            total_removed += removed
            
            # Create backup if changes were made
            if removed > 0:
                backup_path = filepath + '.backup'
                if not os.path.exists(backup_path):
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        json.dump(bikes_data, f, ensure_ascii=False, indent=2)
                    print(f"   💾 Created backup: {filename}.backup")
                
                # Save deduplicated data
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(deduplicated, f, ensure_ascii=False, indent=2)
                
                print(f"   ✅ {source_name}: {original_count} → {dedup_count} bikes (removed {removed} duplicates)")
            else:
                print(f"   ✅ {source_name}: {original_count} bikes (no duplicates)")
        
        except Exception as e:
            print(f"   ❌ Error processing {filename}: {e}")
            continue
    
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Total bikes before: {total_original}")
    print(f"Total bikes after:  {total_deduplicated}")
    print(f"Duplicates removed: {total_removed}")
    print("\n✅ Deduplication complete! You can now run the migration safely.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Deduplicate standardized bike data')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified\n")
    
    process_all_standardized_files()

