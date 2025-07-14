import json
import os
from collections import defaultdict

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
    'shock': 'rear_shox',
    'Shock': 'rear_shox',
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

    # Hebrew fields -> standardized English names
    'אוכף': 'saddle',
    'קראנק': 'crank_set',
    'מעביר אחורי': 'rear_derailleur',
    'מעביר קדמי': 'front_derailleur',
    'גלגל אחורי': 'rear_wheel',
    'גלגל קדמי': 'front_wheel',
    'חישוק אחורי': 'rear_rim',
    'חישוק קדמי': 'front_rim',
    'צינור אחורי': 'rear_tube',
    'צינור קדמי': 'front_tube',
    'חוטים': 'spokes',
    'חישוקים': 'rims',
    'צינור אחורי/קדמי': 'tubes',
    'צינור קדמי/אחורי': 'tubes',
    'חישוק קדמי': 'front rim',
    'חישוק אחורי': 'rear rim',
    'גלגל קדמי': 'front wheel',
    'גלגל אחורי': 'rear wheel',
    'מעביר קדמי': 'front derailleurs',
    'מעביר אחורי': 'rear derailleur',
    'תצוגה': 'screen',
    'גלגלים': 'wheels',
    'גריפים': 'grip',
    'מטען': 'charger',
    'לוח תצוגה': 'screen',
    'מוט אוכף': 'seat_post',
    'מוט כיסא': 'seat_post',
    'מוט כידון': 'stem',
    'בלמים': 'brakes',
    'ברקסים': 'brakes',
    'קסטה': 'cassette',
    'רוטורים': 'Rotors',
    'סטם': 'stem',
    'לוח תצוגה': 'screen',
    'שרשרת': 'chain',
    'צמיגים': 'tires',
    'גלגל הינע': 'hub',
    'מעצורים': 'brakes',
    'מערכת שליטה': 'remote',
    'מספר הילוכים:': 'gear_count',
    'פדלים': 'pedals',
    'ידיות הילוכים': 'shifter',
    'כידון': 'handlebar',
    'הדסט': 'headset',
    'הד-סט': 'headset',
    'מידות': 'size',
    'ציר מרכזי': 'bottom_bracket',
    'משקל': 'weight',
    'תוספות': 'extras',
    'סט גלגלים': 'wheels',
    'סוג מנוע': 'motor',
    'מסך': 'screen',
    'ידית הילוכים': 'shifter',
    'סוללה': 'battery',
    'שלדה': 'frame',
    'מידה': 'size',
    'בולם קדמי': 'fork',
    'בולם אחורי': 'rear_shox',
    'קרנק': 'crank_set',
    'שלט מצבי מנוע': 'remote',
    'כיסא': 'seat',
    'בטריה': 'battery',
    'מסך תצוגה': 'screen',
    'מערכת הנעה': 'motor',
    'נאבה אחורית': 'rear_hub',
    'נאבה קדמית': 'front_hub',
    'צמיג קדמי': 'front_tire',
    'צמיג אחורי': 'rear_tire',
    'צמיג קידמי': 'front_tire',
    'דיסקים': 'rotors',
    'משקל משוער': 'weight',
    'מנוע': 'motor',
    'מנוע חשמלי': 'motor',

}

def standardize_bike_data(bike_data):
    """Standardize a single bike's data using the field mapping"""
    standardized = {}

    for original_field, value in bike_data.items():
        # --- MODIFIED LINE: Strip whitespace from the original_field ---
        cleaned_original_field = original_field.strip()

        if cleaned_original_field in FIELD_MAPPING:
            standardized_field = FIELD_MAPPING[cleaned_original_field] # Use cleaned field here
            # If field already exists, merge values (for cases like rims, wheels, etc.)
            if standardized_field in standardized and value:
                if standardized[standardized_field]:
                    standardized[standardized_field] += f" / {value}"
                else:
                    standardized[standardized_field] = value
            else:
                standardized[standardized_field] = value
        # Remove unknown fields - they won't be included in standardized output

    return standardized

def standardize_json_files():
    """Standardize all JSON files in the data directory"""
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json') and not f.startswith('standardized_') and f not in ['compare_counts.json', 'posts.json']] #

    print(f"Found {len(json_files)} JSON files to standardize")

    for filename in json_files:
        filepath = os.path.join(data_dir, filename)
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

            # Save standardized file
            output_filename = f"standardized_{filename}"
            output_filepath = os.path.join(data_dir, output_filename)

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
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
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
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json') and not f.startswith('standardized_') and f not in ['compare_counts.json', 'posts.json']] #

    all_standardized_bikes = []

    for filename in json_files:
        filepath = os.path.join(data_dir, filename)
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

    # Save combined file
    combined_filepath = os.path.join(data_dir, "all_bikes_standardized.json")
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