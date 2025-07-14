import json
import os
from models import init_db, get_session, Bike

def load_bikes_from_json():
    """Load all bikes from standardized JSON files for migration purposes"""
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    
    # Try to load from combined standardized file first
    combined_file = os.path.join(data_dir, "all_bikes_standardized.json")
    if os.path.exists(combined_file):
        print(f"Loading from combined file: {combined_file}")
        with open(combined_file, 'r', encoding='utf-8') as f:
            bikes = json.load(f)
        return bikes
    
    # If no combined file, load from individual standardized files
    standardized_files = [f for f in os.listdir(data_dir) if f.startswith('standardized_') and f.endswith('.json')]
    
    all_bikes = []
    for filename in standardized_files:
        filepath = os.path.join(data_dir, filename)
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
                rear_shox=bike_data.get('rear_shock', ''),
                
                
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
                tires=bike_data.get('tires', '')
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