#!/usr/bin/env python3
"""
Generic script to import any standardized scraper data to the bikes table in the database

This script can import data from any standardized scraper file.
"""

import json
import os
import sys
import glob

# Add the scripts directory to the Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.join(current_dir, '..')
sys.path.insert(0, scripts_dir)

from db.models import init_db, get_session, Bike
from utils import clean_bike_field_value

def get_standardized_files():
    """Get list of all standardized scraper files"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    standardized_data_dir = os.path.join(current_dir, '..', '..', 'data', 'standardized_data')
    
    if not os.path.exists(standardized_data_dir):
        return []
    
    standardized_files = glob.glob(os.path.join(standardized_data_dir, "standardized_*.json"))
    # Exclude all_bikes_standardized.json
    standardized_files = [f for f in standardized_files if not f.endswith("all_bikes_standardized.json")]
    
    return standardized_files

def get_unimported_standardized_files():
    """Get list of standardized files that haven't been imported to database yet"""
    standardized_files = get_standardized_files()
    
    # For now, we'll import all standardized files
    # In the future, you could add a tracking mechanism to know which files have been imported
    return standardized_files

def import_standardized_file(standardized_file_path):
    """Import a single standardized file to the database"""
    filename = os.path.basename(standardized_file_path)
    scraper_name = filename.replace('standardized_', '').replace('.json', '')
    
    print(f"\n=== Importing {scraper_name} to Database ===")
    print(f"File: {standardized_file_path}")
    
    try:
        # Load standardized data
        with open(standardized_file_path, 'r', encoding='utf-8') as f:
            standardized_bikes = json.load(f)
        
        print(f"Found {len(standardized_bikes)} standardized bikes")
        
        # Initialize database
        init_db()
        session = get_session()
        
        # Add bikes to database
        added_count = 0
        skipped_count = 0
        
        for i, bike_data in enumerate(standardized_bikes):
            print(f"Processing bike {i+1}/{len(standardized_bikes)}: {bike_data.get('model', 'Unknown')}")
            
            # Generate ID if not present
            if not bike_data.get('id'):
                firm = bike_data.get('firm', '').replace(" ", "-")
                model = bike_data.get('model', '').replace(" ", "-")
                year = str(bike_data.get('year', ''))
                url_part = bike_data.get('product_url', '').split('/')[-1].split('.')[0] if bike_data.get('product_url') else 'unknown'
                bike_data['id'] = f"{firm}_{model}_{year}_{url_part}".lower()
                print(f"Generated ID for bike: {bike_data['id']}")
            
            # Check if bike already exists
            existing_bike = session.query(Bike).filter_by(id=bike_data['id']).first()
            if existing_bike:
                print(f"⚠️ Bike {bike_data['id']} already exists, skipping...")
                skipped_count += 1
                continue
            
            # Create new bike record with standardized fields
            bike = Bike(
                id=bike_data.get('id', ''),
                firm=clean_bike_field_value(bike_data.get('firm', '')),
                model=clean_bike_field_value(bike_data.get('model', '')),
                year=bike_data.get('year'),
                price=clean_bike_field_value(bike_data.get('price', '')),
                disc_price=clean_bike_field_value(bike_data.get('disc_price', '')),
                image_url=clean_bike_field_value(bike_data.get('image_url', '')),
                product_url=clean_bike_field_value(bike_data.get('product_url', '')),
                frame=clean_bike_field_value(bike_data.get('frame', '')),
                motor=clean_bike_field_value(bike_data.get('motor', '')),
                battery=clean_bike_field_value(bike_data.get('battery', '')),
                fork=clean_bike_field_value(bike_data.get('fork', '')),
                rear_shock=clean_bike_field_value(bike_data.get('rear_shock', '')),
                
                # Additional standardized fields
                stem=clean_bike_field_value(bike_data.get('stem', '')),
                handelbar=clean_bike_field_value(bike_data.get('handlebar', '')),
                front_brake=clean_bike_field_value(bike_data.get('front_brake', '')),
                rear_brake=clean_bike_field_value(bike_data.get('rear_brake', '')),
                shifter=clean_bike_field_value(bike_data.get('shifter', '')),
                rear_der=clean_bike_field_value(bike_data.get('rear_derailleur', '')),
                cassette=clean_bike_field_value(bike_data.get('cassette', '')),
                chain=clean_bike_field_value(bike_data.get('chain', '')),
                crank_set=clean_bike_field_value(bike_data.get('crank_set', '')),
                front_wheel=clean_bike_field_value(bike_data.get('front_wheel', '')),
                rear_wheel=clean_bike_field_value(bike_data.get('rear_wheel', '')),
                rims=clean_bike_field_value(bike_data.get('rims', '')),
                front_axle=clean_bike_field_value(bike_data.get('front_axle', '')),
                rear_axle=clean_bike_field_value(bike_data.get('rear_axle', '')),
                spokes=clean_bike_field_value(bike_data.get('spokes', '')),
                tubes=clean_bike_field_value(bike_data.get('tubes', '')),
                front_tire=clean_bike_field_value(bike_data.get('front_tire', '')),
                rear_tire=clean_bike_field_value(bike_data.get('rear_tire', '')),
                saddle=clean_bike_field_value(bike_data.get('saddle', '')),
                seat_post=clean_bike_field_value(bike_data.get('seat_post', '')),
                clamp=clean_bike_field_value(bike_data.get('clamp', '')),
                charger=clean_bike_field_value(bike_data.get('charger', '')),
                wheel_size=clean_bike_field_value(bike_data.get('wheel_size', '')),
                headset=clean_bike_field_value(bike_data.get('headset', '')),
                brake_lever=clean_bike_field_value(bike_data.get('brake_lever', '')),
                screen=clean_bike_field_value(bike_data.get('screen', '')),
                extras=clean_bike_field_value(bike_data.get('extras', '')),
                pedals=clean_bike_field_value(bike_data.get('pedals', '')),
                bb=clean_bike_field_value(bike_data.get('bottom_bracket', '')),
                gear_count=clean_bike_field_value(bike_data.get('gear_count', '')),
                
                # Additional fields that might be in standardized data
                weight=clean_bike_field_value(bike_data.get('weight', '')),
                size=clean_bike_field_value(bike_data.get('size', '')),
                hub=clean_bike_field_value(bike_data.get('hub', '')),
                brakes=clean_bike_field_value(bike_data.get('brakes', '')),
                tires=clean_bike_field_value(bike_data.get('tires', '')),
                
                # NEW FIELDS - Added based on JSON analysis
                wh=bike_data.get('wh'),
                gallery_images_urls=json.dumps(bike_data.get('gallery_images_urls', [])) if bike_data.get('gallery_images_urls') else None,
                fork_length=bike_data.get('fork_length') or bike_data.get('fork length'),
                sub_category=clean_bike_field_value(bike_data.get('sub_category') or bike_data.get('sub-category')),
                rear_wheel_maxtravel=clean_bike_field_value(bike_data.get('rear_wheel_maxtravel') or bike_data.get('rear wheel maxtravel')),
                battery_capacity=clean_bike_field_value(bike_data.get('battery_capacity')),
                front_wheel_size=clean_bike_field_value(bike_data.get('front_wheel_size') or bike_data.get('front wheel size')),
                rear_wheel_size=clean_bike_field_value(bike_data.get('rear_wheel_size') or bike_data.get('rear wheel size')),
                battery_watts_per_hour=clean_bike_field_value(bike_data.get('battery_watts_per_hour') or bike_data.get('battery watts per hour'))
            )
            
            session.add(bike)
            added_count += 1
            print(f"✅ Added bike: {bike_data['id']}")
        
        # Commit all changes
        session.commit()
        print(f"\n🎉 Successfully imported {scraper_name} to database")
        print(f"   Bikes added: {added_count}")
        print(f"   Bikes skipped (duplicates): {skipped_count}")
        
        session.close()
        return added_count, skipped_count
        
    except Exception as e:
        print(f"Error importing {scraper_name} to database: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return 0, 0

def import_all_standardized_data():
    """Import all standardized scraper data to the database"""
    print("🔍 Scanning for standardized scraper data files...")
    
    standardized_files = get_standardized_files()
    
    if not standardized_files:
        print("❌ No standardized scraper files found.")
        print("Please run the standardization script first.")
        return
    
    print(f"Found {len(standardized_files)} standardized files:")
    for file_path in standardized_files:
        print(f"  - {os.path.basename(file_path)}")
    
    total_processed = 0
    total_added = 0
    total_skipped = 0
    
    for standardized_file_path in standardized_files:
        added_count, skipped_count = import_standardized_file(standardized_file_path)
        
        if added_count > 0 or skipped_count > 0:
            total_processed += 1
            total_added += added_count
            total_skipped += skipped_count
    
    print(f"\n🎉 Database import complete!")
    print(f"   Files processed: {total_processed}")
    print(f"   Total bikes added: {total_added}")
    print(f"   Total bikes skipped: {total_skipped}")

def import_specific_scraper(scraper_name):
    """Import a specific scraper's standardized data to the database"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    standardized_data_dir = os.path.join(current_dir, '..', '..', 'data', 'standardized_data')
    standardized_file_path = os.path.join(standardized_data_dir, f"standardized_{scraper_name}.json")
    
    if not os.path.exists(standardized_file_path):
        print(f"❌ Standardized file not found: {standardized_file_path}")
        print("Please run the standardization script first.")
        return False
    
    added_count, skipped_count = import_standardized_file(standardized_file_path)
    
    if added_count > 0 or skipped_count > 0:
        print(f"\n✅ Successfully imported {scraper_name}")
        print(f"   Bikes added: {added_count}")
        print(f"   Bikes skipped: {skipped_count}")
        return True
    else:
        print(f"\n❌ Failed to import {scraper_name}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Import standardized scraper data to database')
    parser.add_argument('--scraper', '-s', type=str, help='Import specific scraper by name (e.g., rosen, cobra)')
    parser.add_argument('--all', '-a', action='store_true', help='Import all standardized scrapers (default)')
    
    args = parser.parse_args()
    
    if args.scraper:
        print(f"Importing specific scraper: {args.scraper}")
        import_specific_scraper(args.scraper)
    else:
        print("Importing all standardized scrapers...")
        import_all_standardized_data()
