import sqlite3
import os
import json
from models import init_db, get_session, Bike

def drop_and_recreate_bikes_table():
    """Drop the bikes table and recreate it with standardized data"""
    print("Starting bikes table recreation...")
    
    # Get the database file path
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'emtb.db')
    
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
        print("Recreating bikes table with new schema...")
        init_db()
        print("✓ Bikes table recreated with new schema")
        
        # Now migrate the standardized data
        print("Migrating standardized data to new table...")
        migrate_standardized_data()
        
    except Exception as e:
        print(f"Error during table recreation: {e}")
        conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def migrate_standardized_data():
    """Migrate all standardized bikes to the new table"""
    session = get_session()
    
    try:
        # Load standardized data
        standardized_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'standardized_data')
        
        # Try to load from combined standardized file first
        combined_file = os.path.join(standardized_data_dir, "all_bikes_standardized.json")
        if os.path.exists(combined_file):
            print(f"Loading from combined file: {combined_file}")
            with open(combined_file, 'r', encoding='utf-8') as f:
                bikes = json.load(f)
        else:
            print("Combined file not found, loading individual files...")
            # Load from individual standardized files
            standardized_files = [f for f in os.listdir(standardized_data_dir) if f.startswith('standardized_') and f.endswith('.json')]
            bikes = []
            for filename in standardized_files:
                filepath = os.path.join(standardized_data_dir, filename)
                print(f"Loading from {filename}...")
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_bikes = json.load(f)
                    bikes.extend(file_bikes)
                print(f"  Loaded {len(file_bikes)} bikes from {filename}")
        
        print(f"Found {len(bikes)} bikes to migrate")
        
        # Migrate each bike
        migrated_count = 0
        duplicate_count = 0
        seen_ids = set()
        
        for bike_data in bikes:
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
                duplicate_count += 1
                print(f"Fixed duplicate ID: {original_id} -> {bike_data['id']}")
            
            # Create new bike record with all standardized fields
            bike = Bike(
                id=bike_data.get('id', ''),
                firm=bike_data.get('firm', ''),
                model=bike_data.get('model', ''),
                year=bike_data.get('year'),
                price=bike_data.get('price', ''),
                disc_price=bike_data.get('disc_price', ''),
                image_url=bike_data.get('image_url', ''),
                product_url=bike_data.get('product_url', ''),
                frame=bike_data.get('frame', ''),
                motor=bike_data.get('motor', ''),
                battery=bike_data.get('battery', ''),
                fork=bike_data.get('fork', ''),
                rear_shock=bike_data.get('rear_shock', ''),
                
                # Additional standardized fields
                stem=bike_data.get('stem', ''),
                handelbar=bike_data.get('handlebar', ''),
                front_brake=bike_data.get('front_brake', ''),
                rear_brake=bike_data.get('rear_brake', ''),
                shifter=bike_data.get('shifter', ''),
                rear_der=bike_data.get('rear_derailleur', ''),
                cassette=bike_data.get('cassette', ''),
                chain=bike_data.get('chain', ''),
                crank_set=bike_data.get('crank_set', ''),
                front_wheel=bike_data.get('front_wheel', ''),
                rear_wheel=bike_data.get('rear_wheel', ''),
                rims=bike_data.get('rims', ''),
                front_axle=bike_data.get('front_axle', ''),
                rear_axle=bike_data.get('rear_axle', ''),
                spokes=bike_data.get('spokes', ''),
                tubes=bike_data.get('tubes', ''),
                front_tire=bike_data.get('front_tire', ''),
                rear_tire=bike_data.get('rear_tire', ''),
                saddle=bike_data.get('saddle', ''),
                seat_post=bike_data.get('seat_post', ''),
                clamp=bike_data.get('clamp', ''),
                charger=bike_data.get('charger', ''),
                wheel_size=bike_data.get('wheel_size', ''),
                headset=bike_data.get('headset', ''),
                brake_lever=bike_data.get('brake_lever', ''),
                screen=bike_data.get('screen', ''),
                extras=bike_data.get('extras', ''),
                pedals=bike_data.get('pedals', ''),
                bb=bike_data.get('bottom_bracket', ''),
                gear_count=bike_data.get('gear_count', ''),
                
                # Additional fields that might be in standardized data
                weight=bike_data.get('weight', ''),
                size=bike_data.get('size', ''),
                hub=bike_data.get('hub', ''),
                brakes=bike_data.get('brakes', ''),
                tires=bike_data.get('tires', ''),
                
                # NEW FIELDS - Added based on JSON analysis
                wh=bike_data.get('wh'),
                gallery_images_urls=json.dumps(bike_data.get('gallery_images_urls', [])) if bike_data.get('gallery_images_urls') else None,
                fork_length=bike_data.get('fork_length') or bike_data.get('fork length'),
                sub_category=bike_data.get('sub_category') or bike_data.get('sub-category'),
                rear_wheel_maxtravel=bike_data.get('rear_wheel_maxtravel') or bike_data.get('rear wheel maxtravel'),
                battery_capacity=bike_data.get('battery_capacity'),
                front_wheel_size=bike_data.get('front_wheel_size') or bike_data.get('front wheel size'),
                rear_wheel_size=bike_data.get('rear_wheel_size') or bike_data.get('rear wheel size'),
                battery_watts_per_hour=bike_data.get('battery_watts_per_hour') or bike_data.get('battery watts per hour')
            )
            
            session.add(bike)
            migrated_count += 1
            
            if migrated_count % 50 == 0:
                print(f"Migrated {migrated_count} bikes...")
        
        # Commit all changes
        session.commit()
        print(f"✓ Successfully migrated {migrated_count} bikes to new table")
        if duplicate_count > 0:
            print(f"  Fixed {duplicate_count} duplicate IDs")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("=== Bikes Table Recreation Tool ===")
    print("This will DROP the existing bikes table and recreate it with standardized data.")
    print("Make sure you have backed up any important data!")
    print()
    
    # Ask for confirmation
    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        drop_and_recreate_bikes_table()
        print("\n✓ Bikes table recreation completed successfully!")
    else:
        print("Operation cancelled.") 