import json
import os
from collections import defaultdict

def clean_bike_field_value(value):
    """Clean bike field values to ensure they're safe for JSON serialization and database storage"""
    if value is None:
        return None
    
    # Convert to string and clean any problematic characters
    cleaned_value = str(value)
    # Remove or replace problematic characters that could break JSON or database operations
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

# Field mapping: various field names -> standardized names
FIELD_MAPPING = {
    # English fields
    'Firm': 'firm',
    'Model': 'model',
    'Year': 'year',
    'Price': 'price',
    'Disc_price': 'disc_price',
    'Frame': 'frame',
    'Motor': 'motor',
    'Battery': 'battery',
    'Fork': 'fork',
    'Rear Shox': 'rear_shock',
    'Image URL': 'image_url',
    'Product URL': 'product_url',
    'Stem': 'stem',
    'stem': 'stem',
    'Handlebar': 'handlebar',
    'Front Brake': 'front_brake',
    'Rear Brake': 'rear_brake',
    'Shifter': 'shifter',
    'Shifters': 'shifter',
    'Rear Der': 'rear_derailleur',
    'Cassette': 'cassette',
    'Chain': 'chain',
    'Crank Set': 'crank_set',
    'Front Wheel': 'front_wheel',
    'Rear Wheel': 'rear_wheel',
    'Rims': 'rims',
    'Front Axle': 'front_axle',
    'Rear Axle': 'rear_axle',
    'Spokes': 'spokes',
    'Tubes': 'tubes',
    'Front Tire': 'front_tire',
    'Rear Tire': 'rear_tire',
    'Saddle': 'saddle',
    'Seat Post': 'seat_post',
    'Seatpost': 'seat_post',
    'Clamp': 'clamp',
    'Charger': 'charger',
    'Wheel Size': 'wheel_size',
    'Headset': 'headset',
    'Brake Lever': 'brake_lever',
    'Screen': 'screen',
    'Extras': 'extras',
    'Pedals': 'pedals',
    'B.B': 'bottom_bracket',
    'gear count': 'gear_count',
    'display': 'screen',
    'shock': 'rear_shock',
    'Shock': 'rear_shock',
    'Front Derailleur': 'front_derailleur',
    'Rear Derailleur': 'rear_derailleur',
    'brakes': 'brakes',
    'Brakes': 'brakes',
    'Brake Levers': 'brake_levers',
    'Crankset': 'crank_set',
    'Hubs': 'hubs',
    'Rotors': 'rotors',
    'Shifters': 'shifter',
    'Tubes': 'tubes',
    'Wheels': 'wheels',
    'Grips': 'grips',
    'Weight': 'weight',
    'Tires': 'tires',
    'Display': 'screen',
    
    # NEW FIELDS - Added based on JSON analysis
    'wh': 'wh',
    'gallery_images_urls': 'gallery_images_urls',
    'fork_length': 'fork_length',
    'fork length': 'fork_length',
    'sub_category': 'sub_category',
    'sub-category': 'sub_category',
    'rear_wheel_maxtravel': 'rear_wheel_maxtravel',
    'rear wheel maxtravel': 'rear_wheel_maxtravel',
    'battery_capacity': 'battery_capacity',
    'front_wheel_size': 'front_wheel_size',
    'front wheel size': 'front_wheel_size',
    'rear_wheel_size': 'rear_wheel_size',
    'rear wheel size': 'rear_wheel_size',
    'battery_watts_per_hour': 'battery_watts_per_hour',
    'battery watts per hour': 'battery_watts_per_hour',
    
    # Additional field mappings found in JSON analysis
    'original_price': 'price',
    'image_URL': 'image_url',
    'product_URL': 'product_url',
    'shifters': 'shifter',
    'crankset': 'crank_set',
    'seatpost': 'seat_post',
    'display': 'screen',
    'rear_derailleur': 'rear_derailleur',
    'rear_shock': 'rear_shock',
    'rear derailleur': 'rear_derailleur',
    'rear shock': 'rear_shock',
    'sizes': 'size',
    'wheel_size': 'wheel_size',
    'front_tire': 'front_tire',
    'rear_tire': 'rear_tire',
    'front_hub': 'front_hub',
    'rear_hub': 'rear_hub',
    'front_wheel': 'front_wheel',
    'rear_wheel': 'rear_wheel',
    'front_brake': 'front_brake',
    'rear_brake': 'rear_brake',
    'brake_levers': 'brake_levers',
    'brake levers': 'brake_levers',
    'brake lever': 'brake_lever',
    'front_derailleur': 'front_derailleur',
    'front derailleur': 'front_derailleur',
    'bottom_bracket': 'bottom_bracket',
    'bottom bracket': 'bottom_bracket',
    'seat post': 'seat_post',
    'shock absorber': 'rear_shock',
    'sprocket': 'cassette',
    'tyres': 'tires',
    'shift lever': 'shifter',
    'wheel set': 'wheels',
    'brake': 'brakes',
    'model year': 'year',
    'Size': 'size',
    'Cockpit': 'handlebar',
    'Drive Unit': 'motor',
    'Battery Pack': 'battery',
    'Drive Unit Control': 'remote',
    'Crankset': 'crank_set',
    'Chainrings': 'chainring',
    'Cassette Size': 'cassette',
    'Gears': 'gear_count',
    'Brake Levers / Calipers': 'brake_levers',
    'Rotors': 'rotors',
    'Rotor Size (F/R)': 'rotor_size',
    'Hubs (F/R)': 'hubs',
    'Tubeless Information': 'tubeless',
    'Tire Clearance': 'tire_clearance',
    'ASTM Classification': 'astm_classification',
    'System Weight Limit': 'weight_limit',
    'chain_guide': 'chain_guide',
    'accessories': 'extras',
    'shifter': 'shifter',
    'front tire': 'front_tire',
    'rear tire': 'rear_tire',
    'material': 'frame_material',
    'Wheels': 'wheels',
    'Gearing': 'gear_count',
    'Front Suspension': 'fork',
    'Rear Suspension': 'rear_shock',
    'lighting': 'lights',
    'front guide': 'chain_guide',
    'front hub': 'front_hub',
    'front rim': 'front_rim',
    'rear hub': 'rear_hub',
    'rear rim': 'rear_rim',
    'spoke': 'spokes',
    'brake rotor': 'rotors',
    'seatclamp': 'seat_clamp',
    'secondary color': 'color_secondary',
    'rear wheel maxtravel': 'rear_wheel_maxtravel',
    'bottle cage mount': 'bottle_cage_mount',
    'frame description': 'frame_description',
    'frame material': 'frame_material',
    'rim': 'rims',
    'tyre': 'tires',
    'tyre size etrto': 'tire_size_etrto',
    'article model': 'model',
    'front fork max travel': 'fork_length',
    'damper': 'rear_shock',
    'derailleur': 'rear_derailleur',
    'handles': 'handlebar',
    'drive unit': 'motor',
    'front wheel': 'front_wheel',
    'rear wheel': 'rear_wheel',
    'brake rotors': 'rotors',
    'type kickstand mount': 'kickstand_mount',
    'front wheel set': 'front_wheel',
    'rear wheel set': 'rear_wheel',
    'front wheel hub': 'front_hub',
    'rear wheel hub': 'rear_hub',
    'finish_color': 'color',
    'front_suspension': 'fork',
    'rear_suspension': 'rear_shock',
    'drive_system': 'motor',
    'gears': 'gear_count',
    'front_derailleur': 'front_derailleur',
    'chain_guide': 'chain_guide',
    'accessories': 'extras',
    'lighting': 'lights',
    'rim_tape': 'rim_tape',
    'company': 'firm',
    'number_of_gears': 'gear_count',
    'number of assistance levels': 'assistance_levels',
    'brake rear': 'rear_brake',
    'front brake': 'front_brake',
    'grip kind': 'grip_type',
    'handgrip brand': 'grip_brand',
    'pedal': 'pedals',
    'derailleur rear': 'rear_derailleur',
    'gear': 'gear_count',
    'shifter right': 'shifter',
    'front fork': 'fork',
    'rear travel': 'rear_shock',
    'front wheel size': 'front_wheel_size',
    'rear wheel size': 'rear_wheel_size',
    'tyre size etrto': 'tire_size_etrto',
    'article model': 'model',
    'front fork max travel': 'fork_length',
    'damper': 'rear_shock',
    'derailleur': 'rear_derailleur',
    'handles': 'handlebar',
    'drive unit': 'motor',
    'brake rotors': 'rotors',
    'type kickstand mount': 'kickstand_mount',
    'finish_color': 'color',
    'drive_system': 'motor',
    'battery brand': 'battery_brand',
    'battery capacity': 'battery_capacity',
    'e-bike system': 'motor',
    'motor torque (nm)': 'motor_torque',
    'number of assistance levels': 'assistance_levels',
    'grip kind': 'grip_type',
    'handgrip brand': 'grip_brand',
    'pedal': 'pedals',
    'derailleur rear': 'rear_derailleur',
    'gear': 'gear_count',
    'shifter right': 'shifter',
    'front fork': 'fork',
    'rear travel': 'rear_shock',
    'tyre size etrto': 'tire_size_etrto',
    'article model': 'model',
    'front fork max travel': 'fork_length',
    'damper': 'rear_shock',
    'derailleur': 'rear_derailleur',
    'handles': 'handlebar',
    'drive unit': 'motor',
    'brake rotors': 'rotors',
    'type kickstand mount': 'kickstand_mount',
    'finish_color': 'color',
    'drive_system': 'motor',
    
    # Add lowercase versions of fields that are already standardized
    'firm': 'firm',
    'model': 'model',
    'year': 'year',
    'price': 'price',
    'original_price': 'price',
    'disc_price': 'disc_price',
    'frame': 'frame',
    'motor': 'motor',
    'battery': 'battery',
    'fork': 'fork',
    'rear_shock': 'rear_shock',
    'image_url': 'image_url',
    'product_url': 'product_url',
    'stem': 'stem',
    'handlebar': 'handlebar',
    'front_brake': 'front_brake',
    'rear_brake': 'rear_brake',
    'shifter': 'shifter',
    'shifters': 'shifter',
    'rear_derailleur': 'rear_derailleur',
    'cassette': 'cassette',
    'chain': 'chain',
    'crank_set': 'crank_set',
    'crankset': 'crank_set',
    'front_wheel': 'front_wheel',
    'rear_wheel': 'rear_wheel',
    'rims': 'rims',
    'front_axle': 'front_axle',
    'rear_axle': 'rear_axle',
    'spokes': 'spokes',
    'tubes': 'tubes',
    'front_tire': 'front_tire',
    'rear_tire': 'rear_tire',
    'saddle': 'saddle',
    'seat_post': 'seat_post',
    'seatpost': 'seat_post',
    'clamp': 'clamp',
    'charger': 'charger',
    'wheel_size': 'wheel_size',
    'headset': 'headset',
    'brake_lever': 'brake_lever',
    'screen': 'screen',
    'display': 'screen',
    'extras': 'extras',
    'pedals': 'pedals',
    'bottom_bracket': 'bottom_bracket',
    'gear_count': 'gear_count',
    'shock': 'rear_shock',
    'front_derailleur': 'front_derailleur',
    'brakes': 'brakes',
    'brake_levers': 'brake_levers',
    'hubs': 'hubs',
    'rotors': 'rotors',
    'wheels': 'wheels',
    'grips': 'grips',
    'weight': 'weight',
    'tires': 'tires',
    'wh': 'wh',
    'gallery_images_urls': 'gallery_images_urls',
    'fork_length': 'fork_length',
    'fork length': 'fork_length',
    'sub_category': 'sub_category',
    'sub-category': 'sub_category',
    'rear_wheel_maxtravel': 'rear_wheel_maxtravel',
    'rear wheel maxtravel': 'rear_wheel_maxtravel',
    'battery_capacity': 'battery_capacity',
    'front_wheel_size': 'front_wheel_size',
    'front wheel size': 'front_wheel_size',
    'rear_wheel_size': 'rear_wheel_size',
    'rear wheel size': 'rear_wheel_size',
    'battery_watts_per_hour': 'battery_watts_per_hour',
    'battery watts per hour': 'battery_watts_per_hour',
    'image_URL': 'image_url',
    'product_URL': 'product_url',
    'rear derailleur': 'rear_derailleur',
    'rear shock': 'rear_shock',
    'sizes': 'size',
    'front_hub': 'front_hub',
    'rear_hub': 'rear_hub',
    'brake levers': 'brake_levers',
    'brake lever': 'brake_lever',
    'front derailleur': 'front_derailleur',
    'bottom bracket': 'bottom_bracket',
    'seat post': 'seat_post',
    'shock absorber': 'rear_shock',
    'sprocket': 'cassette',
    'tyres': 'tires',
    'shift lever': 'shifter',
    'wheel set': 'wheels',
    'brake': 'brakes',
    'model year': 'year',
    'Size': 'size',
    'Cockpit': 'handlebar',
    'Drive Unit': 'motor',
    'Battery Pack': 'battery',
    'Drive Unit Control': 'remote',
    'Crankset': 'crank_set',
    'Chainrings': 'chainring',
    'Cassette Size': 'cassette',
    'Gears': 'gear_count',
    'Brake Levers / Calipers': 'brake_levers',
    'Rotors': 'rotors',
    'Rotor Size (F/R)': 'rotor_size',
    'Hubs (F/R)': 'hubs',
    'Tubeless Information': 'tubeless',
    'Tire Clearance': 'tire_clearance',
    'ASTM Classification': 'astm_classification',
    'System Weight Limit': 'weight_limit',
    'chain_guide': 'chain_guide',
    'accessories': 'extras',
    'front tire': 'front_tire',
    'rear tire': 'rear_tire',
    'material': 'frame_material',
    'Wheels': 'wheels',
    'Gearing': 'gear_count',
    'Front Suspension': 'fork',
    'Rear Suspension': 'rear_shock',
    'lighting': 'lights',
    'front guide': 'chain_guide',
    'front hub': 'front_hub',
    'front rim': 'front_rim',
    'rear hub': 'rear_hub',
    'rear rim': 'rear_rim',
    'spoke': 'spokes',
    'brake rotor': 'rotors',
    'seatclamp': 'seat_clamp',
    'secondary color': 'color_secondary',
    'rear wheel maxtravel': 'rear_wheel_maxtravel',
    'bottle cage mount': 'bottle_cage_mount',
    'frame description': 'frame_description',
    'frame material': 'frame_material',
    'rim': 'rims',
    'tyre': 'tires',
    'tyre size etrto': 'tire_size_etrto',
    'article model': 'model',
    'front fork max travel': 'fork_length',
    'damper': 'rear_shock',
    'derailleur': 'rear_derailleur',
    'handles': 'handlebar',
    'drive unit': 'motor',
    'front wheel': 'front_wheel',
    'rear wheel': 'rear_wheel',
    'brake rotors': 'rotors',
    'type kickstand mount': 'kickstand_mount',
    'front wheel set': 'front_wheel',
    'rear wheel set': 'rear_wheel',
    'front wheel hub': 'front_hub',
    'rear wheel hub': 'rear_hub',
    'finish_color': 'color',
    'front_suspension': 'fork',
    'rear_suspension': 'rear_shock',
    'drive_system': 'motor',
    'gears': 'gear_count',
    'rim_tape': 'rim_tape',
    'company': 'firm',
    'number_of_gears': 'gear_count',
    'number of assistance levels': 'assistance_levels',
    'brake rear': 'rear_brake',
    'front brake': 'front_brake',
    'grip kind': 'grip_type',
    'handgrip brand': 'grip_brand',
    'pedal': 'pedals',
    'derailleur rear': 'rear_derailleur',
    'gear': 'gear_count',
    'shifter right': 'shifter',
    'front fork': 'fork',
    'rear travel': 'rear_shock',
    'front wheel size': 'front_wheel_size',
    'rear wheel size': 'rear_wheel_size',
    'battery brand': 'battery_brand',
    'battery capacity': 'battery_capacity',
    'e-bike system': 'motor',
    'motor torque (nm)': 'motor_torque',
    'control_system': 'remote',
    'travel': 'fork_length',
    'full_title': 'title',
    'description': 'description',
    'specifications': 'specifications',
    'images': 'images',

}

def standardize_bike_data(bike_data):
    """Standardize a single bike's data using the field mapping"""
    standardized = {}

    for original_field, value in bike_data.items():
        # --- MODIFIED LINE: Strip whitespace from the original_field ---
        cleaned_original_field = original_field.strip()

        if cleaned_original_field in FIELD_MAPPING:
            standardized_field = FIELD_MAPPING[cleaned_original_field] # Use cleaned field here
            # Clean the value to handle semicolons and other problematic characters
            cleaned_value = clean_bike_field_value(value)
            
            # If field already exists, merge values (for cases like rims, wheels, etc.)
            if standardized_field in standardized and cleaned_value:
                if standardized[standardized_field]:
                    standardized[standardized_field] += f" / {cleaned_value}"
                else:
                    standardized[standardized_field] = cleaned_value
            else:
                standardized[standardized_field] = cleaned_value
        # Remove unknown fields - they won't be included in standardized output

    return standardized

def standardize_json_files():
    """Standardize all JSON files in the scraped_raw_data directory"""
    raw_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'scraped_raw_data')
    standardized_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'standardized_data')
    
    # Create standardized_data directory if it doesn't exist
    os.makedirs(standardized_data_dir, exist_ok=True)
    
    json_files = [f for f in os.listdir(raw_data_dir) if f.endswith('.json') and not f.startswith('standardized_') and f not in ['compare_counts.json', 'posts.json']] #

    print(f"Found {len(json_files)} JSON files to standardize")

    for filename in json_files:
        filepath = os.path.join(raw_data_dir, filename)
        print(f"Processing {filename}...")

        try:
            # Read original file
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different data structures
            if isinstance(data, list):
                bikes = data
            elif isinstance(data, dict):
                bikes = [data]  # Single bike object
            else:
                print(f"Warning: {filename} contains unexpected data type: {type(data)}, skipping...")
                continue

            # Standardize each bike
            standardized_bikes = []
            for bike in bikes:
                if isinstance(bike, dict):
                    standardized_bike = standardize_bike_data(bike)
                    standardized_bikes.append(standardized_bike)
                else:
                    print(f"Warning: Skipping non-dictionary bike in {filename}")

            # Save standardized file to the new directory
            output_filename = f"standardized_{filename}"
            output_filepath = os.path.join(standardized_data_dir, output_filename)

            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(standardized_bikes, f, ensure_ascii=False, indent=2)

            print(f"Saved standardized file: {output_filename}")
            print(f"  Original bikes: {len(bikes)}")
            print(f"  Standardized bikes: {len(standardized_bikes)}")

        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue

def show_field_statistics():
    """Show statistics about field usage across all JSON files"""
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'scraped_raw_data')
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json') and not f.startswith('standardized_') and f not in ['compare_counts.json', 'posts.json']] #

    field_counts = defaultdict(int)
    total_bikes = 0

    for filename in json_files:
        filepath = os.path.join(data_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different data structures
            if isinstance(data, list):
                bikes = data
            elif isinstance(data, dict):
                bikes = [data]  # Single bike object
            else:
                print(f"Warning: {filename} contains unexpected data type: {type(data)}")
                continue

            total_bikes += len(bikes)
            for bike in bikes:
                if isinstance(bike, dict):
                    for field in bike.keys():
                        field_counts[field.strip()] += 1 # Strip space for counting statistics
                else:
                    print(f"Warning: Bike in {filename} is not a dictionary: {type(bike)}")

        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue

    print(f"Field usage across {len(json_files)} files ({total_bikes} bikes):")
    for field, count in sorted(field_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_bikes) * 100
        print(f"  {field}: {count} bikes ({percentage:.1f}%)")

def create_combined_standardized_file():
    """Create one combined JSON file with all standardized bikes"""
    raw_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'scraped_raw_data')
    standardized_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'standardized_data')
    
    # Create standardized_data directory if it doesn't exist
    os.makedirs(standardized_data_dir, exist_ok=True)
    
    json_files = [f for f in os.listdir(raw_data_dir) if f.endswith('.json') and not f.startswith('standardized_') and f not in ['compare_counts.json', 'posts.json']] #

    all_standardized_bikes = []

    for filename in json_files:
        filepath = os.path.join(raw_data_dir, filename)
        print(f"Processing {filename} for combined file...")

        try:
            # Read original file
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different data structures
            if isinstance(data, list):
                bikes = data
            elif isinstance(data, dict):
                bikes = [data]  # Single bike object
            else:
                print(f"Warning: {filename} contains unexpected data type: {type(data)}, skipping...")
                continue

            # Standardize each bike
            for bike in bikes:
                if isinstance(bike, dict):
                    standardized_bike = standardize_bike_data(bike)
                    # Add source file info
                    standardized_bike['source_file'] = filename
                    all_standardized_bikes.append(standardized_bike)
                else:
                    print(f"Warning: Skipping non-dictionary bike in {filename}")

        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue

    # Save combined file to the new directory
    combined_filepath = os.path.join(standardized_data_dir, "all_bikes_standardized.json")
    with open(combined_filepath, 'w', encoding='utf-8') as f:
        json.dump(all_standardized_bikes, f, ensure_ascii=False, indent=2)

    print(f"Created combined file: all_bikes_standardized.json")
    print(f"Total bikes in combined file: {len(all_standardized_bikes)}")

if __name__ == "__main__":
    print("=== JSON Standardization Tool ===")
    print()

    print("1. Field statistics:")
    show_field_statistics()
    print()

    print("2. Standardizing individual files...")
    standardize_json_files()
    print()

    print("3. Creating combined standardized file...")
    create_combined_standardized_file()
    print()

    print("Standardization complete!")