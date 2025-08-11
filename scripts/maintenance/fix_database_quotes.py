import os
import sys

# Add the scripts directory to the Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.join(current_dir, '..')
sys.path.insert(0, scripts_dir)

from db.models import get_session, Bike
import re

def clean_bike_field_value(value):
    """Clean bike field values to ensure they're safe for database storage and JSON serialization"""
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

def fix_database_quotes():
    """Fix all problematic characters in the database"""
    print("Starting comprehensive database cleanup...")
    
    session = get_session()
    try:
        # Get all bikes
        bikes = session.query(Bike).all()
        print(f"Found {len(bikes)} bikes to process")
        
        updated_count = 0
        
        for bike in bikes:
            original_fork = bike.fork
            original_frame = bike.frame
            original_motor = bike.motor
            original_battery = bike.battery
            original_rear_shock = bike.rear_shock
            
            # Clean all string fields
            bike.fork = clean_bike_field_value(bike.fork)
            bike.frame = clean_bike_field_value(bike.frame)
            bike.motor = clean_bike_field_value(bike.motor)
            bike.battery = clean_bike_field_value(bike.battery)
            bike.rear_shock = clean_bike_field_value(bike.rear_shock)
            bike.firm = clean_bike_field_value(bike.firm)
            bike.model = clean_bike_field_value(bike.model)
            bike.price = clean_bike_field_value(bike.price)
            bike.disc_price = clean_bike_field_value(bike.disc_price)
            bike.image_url = clean_bike_field_value(bike.image_url)
            bike.product_url = clean_bike_field_value(bike.product_url)
            bike.stem = clean_bike_field_value(bike.stem)
            bike.handelbar = clean_bike_field_value(bike.handelbar)
            bike.front_brake = clean_bike_field_value(bike.front_brake)
            bike.rear_brake = clean_bike_field_value(bike.rear_brake)
            bike.shifter = clean_bike_field_value(bike.shifter)
            bike.rear_der = clean_bike_field_value(bike.rear_der)
            bike.cassette = clean_bike_field_value(bike.cassette)
            bike.chain = clean_bike_field_value(bike.chain)
            bike.crank_set = clean_bike_field_value(bike.crank_set)
            bike.front_wheel = clean_bike_field_value(bike.front_wheel)
            bike.rear_wheel = clean_bike_field_value(bike.rear_wheel)
            bike.rims = clean_bike_field_value(bike.rims)
            bike.front_axle = clean_bike_field_value(bike.front_axle)
            bike.rear_axle = clean_bike_field_value(bike.rear_axle)
            bike.spokes = clean_bike_field_value(bike.spokes)
            bike.tubes = clean_bike_field_value(bike.tubes)
            bike.front_tire = clean_bike_field_value(bike.front_tire)
            bike.rear_tire = clean_bike_field_value(bike.rear_tire)
            bike.saddle = clean_bike_field_value(bike.saddle)
            bike.seat_post = clean_bike_field_value(bike.seat_post)
            bike.clamp = clean_bike_field_value(bike.clamp)
            bike.charger = clean_bike_field_value(bike.charger)
            bike.wheel_size = clean_bike_field_value(bike.wheel_size)
            bike.headset = clean_bike_field_value(bike.headset)
            bike.brake_lever = clean_bike_field_value(bike.brake_lever)
            bike.screen = clean_bike_field_value(bike.screen)
            bike.extras = clean_bike_field_value(bike.extras)
            bike.pedals = clean_bike_field_value(bike.pedals)
            bike.bb = clean_bike_field_value(bike.bb)
            bike.gear_count = clean_bike_field_value(bike.gear_count)
            bike.weight = clean_bike_field_value(bike.weight)
            bike.size = clean_bike_field_value(bike.size)
            bike.hub = clean_bike_field_value(bike.hub)
            bike.brakes = clean_bike_field_value(bike.brakes)
            bike.tires = clean_bike_field_value(bike.tires)
            bike.sub_category = clean_bike_field_value(bike.sub_category)
            bike.rear_wheel_maxtravel = clean_bike_field_value(bike.rear_wheel_maxtravel)
            bike.battery_capacity = clean_bike_field_value(bike.battery_capacity)
            bike.front_wheel_size = clean_bike_field_value(bike.front_wheel_size)
            bike.rear_wheel_size = clean_bike_field_value(bike.rear_wheel_size)
            bike.battery_watts_per_hour = clean_bike_field_value(bike.battery_watts_per_hour)
            
            # Check if any field was actually changed
            if (original_fork != bike.fork or original_frame != bike.frame or 
                original_motor != bike.motor or original_battery != bike.battery or 
                original_rear_shock != bike.rear_shock):
                updated_count += 1
                print(f"Updated bike {bike.id}")
        
        # Commit all changes
        session.commit()
        print(f"Successfully updated {updated_count} bikes")
        
    except Exception as e:
        print(f"Error during database cleanup: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    fix_database_quotes()
