#!/usr/bin/env python3
"""
Script to recreate the bikes table with current schema and migrate existing data
Includes database backup, data cleaning, and comprehensive migration
"""

import sqlite3
import os
import json
import shutil
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import init_db, get_session, Bike, Comparison, CompareCount

def clean_bike_field_value(value):
    """Clean bike field values to ensure they're safe for database storage"""
    if value is None:
        return None
    
    # Convert to string and clean any problematic characters
    cleaned_value = str(value)
    # Remove or replace problematic characters that could break database operations
    cleaned_value = cleaned_value.replace('\n', ' ').replace('\r', ' ')
    cleaned_value = cleaned_value.replace('\t', ' ')
    # Handle semicolons and other special characters that might cause issues
    cleaned_value = cleaned_value.replace(';', ', ')  # Replace semicolons with commas
    cleaned_value = cleaned_value.replace('"', "'")   # Replace double quotes with single quotes
    cleaned_value = cleaned_value.replace('\\', '/')  # Replace backslashes with forward slashes
    # Remove any null bytes or other control characters
    cleaned_value = ''.join(char for char in cleaned_value if ord(char) >= 32 or char in '\n\r\t')
    # Trim whitespace
    cleaned_value = cleaned_value.strip()
    
    return cleaned_value if cleaned_value else None

def load_bikes_from_json():
    """Load all bikes from standardized JSON files for migration purposes"""
    standardized_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'standardized_data')

    # Try to load from combined file first
    combined_file = os.path.join(standardized_data_dir, "all_bikes_standardized.json")
    if os.path.exists(combined_file):
        print(f"Loading from combined file: {combined_file}")
        with open(combined_file, 'r', encoding='utf-8') as f:
            bikes = json.load(f)
        return bikes
    
    # If no combined file, load from individual standardized files
    standardized_files = [f for f in os.listdir(standardized_data_dir) if f.startswith('standardized_') and f.endswith('.json')]
    
    all_bikes = []
    for filename in standardized_files:
        filepath = os.path.join(standardized_data_dir, filename)
        print(f"Loading from {filename}...")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            bikes = json.load(f)
        
        all_bikes.extend(bikes)
        print(f"  Loaded {len(bikes)} bikes from {filename}")
    
    return all_bikes

def drop_and_recreate_bikes_table():
    """Drop the bikes table and recreate it with current schema and cleaned data"""
    print("Starting bikes table recreation...")
    
    # Get the database file path
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bikes.db')
    
    # Backup existing database if it exists
    if os.path.exists(db_path):
        backup_path = db_path + '.backup'
        print(f"Backing up existing database to {backup_path}")
        shutil.copy2(db_path, backup_path)
        print("✓ Backup created successfully")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Drop the bikes table
        print("Dropping bikes table...")
        cursor.execute("DROP TABLE IF EXISTS bikes")
        print("✓ Bikes table dropped successfully")
        
        # Commit the drop
        conn.commit()
        
        # Close connection
        conn.close()
        
        # Recreate the table using SQLAlchemy
        print("Recreating bikes table with current schema...")
        init_db()
        print("✓ Bikes table recreated with current schema")
        
        # Now migrate the standardized data with cleaning
        print("Migrating standardized data to new table...")
        migrate_standardized_data_with_cleaning()
        
    except Exception as e:
        print(f"Error during table recreation: {e}")
        conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def migrate_standardized_data_with_cleaning():
    """Migrate all standardized bikes to the new table with data cleaning"""
    session = get_session()
    
    try:
        # Load standardized data
        all_bikes = load_bikes_from_json()
        
        if not all_bikes:
            print("No bikes found in JSON files. Migration completed.")
            return
        
        print(f"Found {len(all_bikes)} bikes to migrate")
        
        # Migrate each bike with cleaning
        migrated_count = 0
        skipped_count = 0
        seen_ids = set()
        
        for bike_data in all_bikes:
            # Generate ID if not present
            if not bike_data.get('id'):
                firm = bike_data.get('firm', '').replace(" ", "-")
                model = bike_data.get('model', '').replace(" ", "-")
                year = str(bike_data.get('year', ''))
                url_part = bike_data.get('product_url', '').split('/')[-1].split('.')[0] if bike_data.get('product_url') else 'unknown'
                bike_data['id'] = f"{firm}_{model}_{year}_{url_part}".lower()
            
            # Handle duplicate IDs by adding a suffix
            original_id = bike_data['id']
            counter = 1
            while bike_data['id'] in seen_ids:
                bike_data['id'] = f"{original_id}_{counter}"
                counter += 1
            seen_ids.add(bike_data['id'])
            
            if counter > 1:
                print(f"Fixed duplicate ID: {original_id} -> {bike_data['id']}")
            
            # Check if bike already exists
            existing_bike = session.query(Bike).filter_by(id=bike_data['id']).first()
            if existing_bike:
                print(f"Bike {bike_data['id']} already exists, skipping...")
                skipped_count += 1
                continue
            
            # Create new bike record with cleaned data
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
                weight=clean_bike_field_value(bike_data.get('weight', '')),
                size=clean_bike_field_value(bike_data.get('size', '')),
                hub=clean_bike_field_value(bike_data.get('hub', '')),
                brakes=clean_bike_field_value(bike_data.get('brakes', '')),
                tires=clean_bike_field_value(bike_data.get('tires', '')),
                wh=bike_data.get('wh'),
                gallery_images_urls=bike_data.get('gallery_images_urls'),
                fork_length=bike_data.get('fork_length'),
                sub_category=clean_bike_field_value(bike_data.get('sub_category', '')),
                rear_wheel_maxtravel=clean_bike_field_value(bike_data.get('rear_wheel_maxtravel', '')),
                battery_capacity=clean_bike_field_value(bike_data.get('battery_capacity', '')),
                front_wheel_size=clean_bike_field_value(bike_data.get('front_wheel_size', '')),
                rear_wheel_size=clean_bike_field_value(bike_data.get('rear_wheel_size', '')),
                battery_watts_per_hour=clean_bike_field_value(bike_data.get('battery_watts_per_hour', ''))
            )
            
            session.add(bike)
            migrated_count += 1
            
            if migrated_count % 50 == 0:
                print(f"Migrated {migrated_count} bikes...")
        
        # Commit all changes
        session.commit()
        print(f"✓ Successfully migrated {migrated_count} bikes")
        if skipped_count > 0:
            print(f"  Skipped {skipped_count} duplicate bikes")
        
    except Exception as e:
        print(f"Error during data migration: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def migrate_standardized_data():
    """Legacy function - kept for backward compatibility"""
    migrate_standardized_data_with_cleaning()

if __name__ == "__main__":
    drop_and_recreate_bikes_table() 