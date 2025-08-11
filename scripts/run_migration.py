#!/usr/bin/env python3
"""
Standalone migration script for PythonAnywhere
This script can be run directly without import issues
"""

import json
import os
import sys
import re
import urllib.parse

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import database models
from db.models import init_db, get_session, Bike

def clean_bike_field_value(value):
    """Clean bike field values to ensure they're safe for database storage"""
    if value is None:
        return None
    
    # Convert to string and clean any problematic characters
    cleaned_value = str(value)
    
    # Remove all control characters except basic whitespace
    cleaned_value = ''.join(char for char in cleaned_value if ord(char) >= 32 or char in ' \t\n\r')
    
    # Replace problematic characters that could break JSON
    cleaned_value = cleaned_value.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    cleaned_value = cleaned_value.replace('"', "'")   # Replace double quotes with single quotes
    cleaned_value = cleaned_value.replace('\\', '/')  # Replace backslashes with forward slashes
    cleaned_value = cleaned_value.replace(';', ', ')  # Replace semicolons with commas
    
    # Remove any remaining control characters
    cleaned_value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned_value)
    
    # Remove duplicate spaces
    cleaned_value = re.sub(r'\s+', ' ', cleaned_value)
    
    # Trim whitespace
    cleaned_value = cleaned_value.strip()
    
    return cleaned_value if cleaned_value else None

def load_bikes_from_json():
    """Load all bikes from standardized JSON files"""
    # Get the path to the standardized data directory
    standardized_data_dir = os.path.join(current_dir, '..', 'data', 'standardized_data')
    
    if not os.path.exists(standardized_data_dir):
        print(f"Warning: Standardized data directory not found: {standardized_data_dir}")
        return []
    
    # Try to load from combined standardized file first
    combined_file = os.path.join(standardized_data_dir, "all_bikes_standardized.json")
    if os.path.exists(combined_file):
        print(f"Loading from combined file: {combined_file}")
        with open(combined_file, 'r', encoding='utf-8') as f:
            bikes = json.load(f)
        return bikes
    
    # If no combined file, load from individual standardized files
    standardized_files = [f for f in os.listdir(standardized_data_dir) if f.startswith('standardized_') and f.endswith('.json')]
    
    if not standardized_files:
        print(f"Warning: No standardized JSON files found in {standardized_data_dir}")
        return []
    
    all_bikes = []
    for filename in standardized_files:
        filepath = os.path.join(standardized_data_dir, filename)
        print(f"Loading from {filename}...")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            bikes = json.load(f)
        
        all_bikes.extend(bikes)
        print(f"  Loaded {len(bikes)} bikes from {filename}")
    
    return all_bikes

def migrate_bikes_to_db():
    """Migrate all bikes from standardized JSON files to SQLite database"""
    print("Starting migration of standardized bikes to SQLite...")
    
    # Initialize database
    init_db()
    session = get_session()
    
    try:
        # Load all bikes from existing JSON files
        all_bikes = load_bikes_from_json()
        
        print(f"Found {len(all_bikes)} bikes to migrate")
        
        # Migrate each bike
        migrated_count = 0
        skipped_count = 0
        
        for bike_data in all_bikes:
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
                print(f"Bike {bike_data['id']} already exists, skipping...")
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
                
                # Additional fields
                weight=clean_bike_field_value(bike_data.get('weight', '')),
                size=clean_bike_field_value(bike_data.get('size', '')),
                hub=clean_bike_field_value(bike_data.get('hub', '')),
                brakes=clean_bike_field_value(bike_data.get('brakes', '')),
                tires=clean_bike_field_value(bike_data.get('tires', '')),
                
                # New fields
                wh=bike_data.get('wh'),
                gallery_images_urls=json.dumps(bike_data.get('gallery_images_urls', [])) if bike_data.get('gallery_images_urls') else None,
                fork_length=bike_data.get('fork_length') or bike_data.get('fork length'),
                sub_category=clean_bike_field_value(bike_data.get('sub_category', '')),
                rear_wheel_maxtravel=clean_bike_field_value(bike_data.get('rear_wheel_maxtravel', '')),
                battery_capacity=clean_bike_field_value(bike_data.get('battery_capacity', '')),
                front_wheel_size=clean_bike_field_value(bike_data.get('front_wheel_size', '')),
                rear_wheel_size=clean_bike_field_value(bike_data.get('rear_wheel_size', '')),
                battery_watts_per_hour=clean_bike_field_value(bike_data.get('battery_watts_per_hour', ''))
            )
            
            session.add(bike)
            migrated_count += 1
            
            if migrated_count % 10 == 0:
                print(f"Migrated {migrated_count} bikes...")
        
        # Commit all changes
        session.commit()
        print(f"Successfully migrated {migrated_count} bikes to database")
        print(f"Skipped {skipped_count} existing bikes")
        
        # Verify migration
        total_bikes = session.query(Bike).count()
        print(f"Total bikes in database: {total_bikes}")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("Starting database migration...")
    migrate_bikes_to_db()
    print("Migration completed successfully!")
