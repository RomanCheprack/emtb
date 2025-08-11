import json
import os
from models import init_db, get_session, Bike
from ..utils import clean_bike_field_value, load_bikes_from_json

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
            migrated_count += 1
            print(f"Added bike: {bike_data['id']}")
        
        # Commit all changes
        session.commit()
        print(f"Successfully migrated {migrated_count} standardized bikes to database")
        print(f"Skipped {skipped_count} existing bikes")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def migrate_compare_counts():
    """Migrate compare counts from JSON to database (if needed)"""
    print("Migrating compare counts...")
    
    try:
        with open("data/compare_counts.json", "r", encoding="utf-8") as f:
            compare_counts = json.load(f)
        
        # You can add a CompareCount model if you want to store this in DB
        # For now, we'll keep it as JSON since it's simple
        print(f"Compare counts loaded: {len(compare_counts)} entries")
        
    except FileNotFoundError:
        print("No compare_counts.json found, skipping...")

if __name__ == "__main__":
    print("Starting migration process...")
    migrate_bikes_to_db()
    migrate_compare_counts()
    print("Migration completed!") 