#!/usr/bin/env python3
"""
Check for duplicate entries in raw JSON files before standardization.

A duplicate is defined as:
- Same product_url (from source.product_url)
- Same specifications (normalized comparison)
- Same structure (same keys in specs)

This script removes duplicates automatically, keeping the first occurrence.
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)


def normalize_spec_value(value):
    """Normalize a spec value for comparison (case-insensitive, whitespace trimmed)"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return str(value).strip()
    return str(value).strip().lower()


def normalize_specs(specs_dict):
    """Normalize specifications dictionary for comparison"""
    if not isinstance(specs_dict, dict):
        return {}
    
    normalized = {}
    for key, value in specs_dict.items():
        # Normalize key (lowercase, strip)
        norm_key = key.strip().lower()
        # Normalize value
        norm_value = normalize_spec_value(value)
        if norm_value:  # Only include non-empty values
            normalized[norm_key] = norm_value
    
    return normalized


def compare_specs(specs1, specs2):
    """Compare two specs dictionaries (normalized)"""
    norm1 = normalize_specs(specs1)
    norm2 = normalize_specs(specs2)
    
    # Compare keys (structure)
    if set(norm1.keys()) != set(norm2.keys()):
        return False
    
    # Compare values
    for key in norm1.keys():
        if norm1[key] != norm2[key]:
            return False
    
    return True


def get_product_url(bike_data):
    """Extract product_url from bike data (handles nested source structure)"""
    if isinstance(bike_data, dict):
        # New structure: source.product_url
        source = bike_data.get('source', {})
        if isinstance(source, dict):
            return source.get('product_url', '')
        # Old structure: product_url at root
        return bike_data.get('product_url', '')
    return ''


def check_duplicates_in_file(filepath, dry_run=False):
    """
    Check for duplicates in a single JSON file.
    
    Returns:
        (total_count, unique_count, duplicates_removed, duplicates_info)
    """
    print(f"\n📄 Processing: {Path(filepath).name}")
    
    try:
        # Load JSON file
        with open(filepath, 'r', encoding='utf-8') as f:
            bikes_data = json.load(f)
        
        if not isinstance(bikes_data, list):
            print(f"   ⚠️  File is not a list, skipping...")
            return 0, 0, 0, []
        
        total_count = len(bikes_data)
        print(f"   📊 Total entries: {total_count}")
        
        # Group by product_url
        url_groups = defaultdict(list)
        for idx, bike in enumerate(bikes_data):
            product_url = get_product_url(bike)
            if product_url:
                url_groups[product_url].append((idx, bike))
            else:
                print(f"   ⚠️  Entry {idx} has no product_url, skipping duplicate check")
        
        # Check for duplicates within each URL group
        duplicates_info = []
        indices_to_remove = set()
        
        for product_url, entries in url_groups.items():
            if len(entries) > 1:
                # Multiple entries with same URL - check if they're duplicates
                print(f"   🔍 Found {len(entries)} entries with URL: {product_url[:60]}...")
                
                # Compare each pair
                for i in range(len(entries)):
                    idx1, bike1 = entries[i]
                    if idx1 in indices_to_remove:
                        continue
                    
                    specs1 = bike1.get('specs', {})
                    
                    for j in range(i + 1, len(entries)):
                        idx2, bike2 = entries[j]
                        if idx2 in indices_to_remove:
                            continue
                        
                        specs2 = bike2.get('specs', {})
                        
                        # Compare specs
                        if compare_specs(specs1, specs2):
                            # Duplicate found - show detailed comparison
                            firm1 = bike1.get('firm', 'Unknown')
                            model1 = bike1.get('model', 'Unknown')
                            firm2 = bike2.get('firm', 'Unknown')
                            model2 = bike2.get('model', 'Unknown')
                            
                            print(f"\n      🔴 DUPLICATE FOUND:")
                            print(f"         Entry {idx1} (KEEP): {firm1} {model1}")
                            print(f"         Entry {idx2} (REMOVE): {firm2} {model2}")
                            print(f"         URL: {product_url[:80]}...")
                            print(f"         Specs match: ✅")
                            
                            # Show a few key specs for verification
                            key_specs = ['frame', 'motor', 'battery', 'fork', 'rear_shock']
                            print(f"         Key specs comparison:")
                            for spec_key in key_specs:
                                val1 = specs1.get(spec_key, 'N/A')
                                val2 = specs2.get(spec_key, 'N/A')
                                if val1 and val2:
                                    match = "✅" if normalize_spec_value(val1) == normalize_spec_value(val2) else "❌"
                                    print(f"           {spec_key}: {match}")
                            
                            duplicates_info.append({
                                'url': product_url,
                                'kept_index': idx1,
                                'removed_index': idx2,
                                'bike': f"{firm1} {model1}",
                                'kept_entry': bike1,
                                'removed_entry': bike2
                            })
                            indices_to_remove.add(idx2)
                            print(f"      ✅ Will remove Entry {idx2}")
        
        duplicates_removed = len(indices_to_remove)
        unique_count = total_count - duplicates_removed
        
        if duplicates_removed > 0:
            print(f"   📝 Found {duplicates_removed} duplicate(s)")
            
            if not dry_run:
                # Remove duplicates (keep first occurrence)
                cleaned_data = [bike for idx, bike in enumerate(bikes_data) if idx not in indices_to_remove]
                
                # Create backup
                backup_path = filepath + '.backup'
                if not os.path.exists(backup_path):
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        json.dump(bikes_data, f, ensure_ascii=False, indent=2)
                    print(f"   💾 Created backup: {Path(backup_path).name}")
                
                # Save cleaned data
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
                
                print(f"   ✅ Removed {duplicates_removed} duplicate(s), saved {unique_count} unique entries")
            else:
                print(f"   🔍 DRY RUN: Would remove {duplicates_removed} duplicate(s)")
        else:
            print(f"   ✅ No duplicates found")
        
        return total_count, unique_count, duplicates_removed, duplicates_info
        
    except json.JSONDecodeError as e:
        print(f"   ❌ JSON decode error: {e}")
        return 0, 0, 0, []
    except Exception as e:
        print(f"   ❌ Error processing file: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0, 0, []


def main():
    """Main function to check duplicates in all raw JSON files"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check and remove duplicates in raw JSON files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--file', help='Process only a specific file (relative to scraped_raw_data/)')
    
    args = parser.parse_args()
    
    # Get raw data directory
    raw_data_dir = os.path.join(project_root, 'data', 'scraped_raw_data')
    
    if not os.path.exists(raw_data_dir):
        print(f"❌ Raw data directory not found: {raw_data_dir}")
        return
    
    print("=" * 80)
    print("🔍 CHECKING DUPLICATES IN RAW JSON FILES")
    print("=" * 80)
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No files will be modified\n")
    
    # Get JSON files
    if args.file:
        json_files = [os.path.join(raw_data_dir, args.file)]
        if not os.path.exists(json_files[0]):
            print(f"❌ File not found: {json_files[0]}")
            return
    else:
        json_files = [
            os.path.join(raw_data_dir, f)
            for f in os.listdir(raw_data_dir)
            if f.endswith('.json') and not f.startswith('standardized_') and f not in ['compare_counts.json', 'posts.json']
        ]
    
    if not json_files:
        print("❌ No JSON files found!")
        return
    
    print(f"\nFound {len(json_files)} file(s) to process\n")
    
    # Process each file
    total_stats = {
        'total': 0,
        'unique': 0,
        'duplicates': 0
    }
    all_duplicates = []
    
    for filepath in sorted(json_files):
        total, unique, duplicates, dup_info = check_duplicates_in_file(filepath, dry_run=args.dry_run)
        total_stats['total'] += total
        total_stats['unique'] += unique
        total_stats['duplicates'] += duplicates
        all_duplicates.extend(dup_info)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Total entries processed: {total_stats['total']}")
    print(f"Unique entries: {total_stats['unique']}")
    print(f"Duplicates removed: {total_stats['duplicates']}")
    
    if all_duplicates:
        print(f"\n📝 Duplicate details (showing first 10):")
        for dup in all_duplicates[:10]:
            print(f"   - {dup['bike']}: {dup['url'][:60]}...")
        if len(all_duplicates) > 10:
            print(f"   ... and {len(all_duplicates) - 10} more")
    
    if args.dry_run:
        print("\n💡 To actually remove duplicates, run without --dry-run flag")
    else:
        print("\n✅ Duplicate checking complete!")
    
    print("=" * 80)


if __name__ == "__main__":
    main()

