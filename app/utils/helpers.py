def format_number_with_commas(value):
    """Format a number with commas for better readability"""
    if value is None:
        return ""
    
    # Handle edge cases
    if isinstance(value, (dict, list)):
        return str(value)
    
    # Convert to string first to check if it's a text value
    value_str = str(value).strip()
    
    # If it's the Hebrew text "צור קשר", return it as-is
    if value_str == "צור קשר":
        return value_str
    
    try:
        # Convert to integer and format with commas
        return "{:,}".format(int(float(value)))
    except (ValueError, TypeError):
        # If conversion fails, return the original value
        return value_str

def clean_bike_data_for_json(bike_dict):
    """Clean bike data to ensure it's safe for JSON serialization"""
    cleaned = {}
    for key, value in bike_dict.items():
        if value is None:
            cleaned[key] = None
        elif isinstance(value, str):
            # Remove any problematic characters that might cause JSON issues
            cleaned_value = value.replace('\x00', '').replace('\r', ' ').replace('\n', ' ')
            cleaned[key] = cleaned_value
        else:
            cleaned[key] = str(value)
    return cleaned

def parse_price(price_str):
    """Parse price string to integer"""
    if not price_str:
        return None
    # Remove non-digit characters except decimal point
    import re
    price_clean = re.sub(r'[^\d.]', '', str(price_str))
    try:
        return int(float(price_clean))
    except (ValueError, TypeError):
        return None

def get_frame_material(bike):
    """
    Determine frame material from bike data.
    Returns 'carbon', 'aluminium', or None if unknown.
    """
    # Check if frame_material field exists and has a value
    frame_material = bike.get('frame_material', '').strip()
    if frame_material:
        frame_material_lower = frame_material.lower()
        if 'carbon' in frame_material_lower:
            return 'carbon'
        elif 'aluminium' in frame_material_lower or 'aluminum' in frame_material_lower:
            return 'aluminium'
    
    # Check frame field description
    frame_val = bike.get('frame', '').strip()
    model_val = bike.get('model', '').strip()
    
    # If both are empty, frame material is unknown
    if not frame_val and not model_val:
        return None
    
    # Search for material indicators in frame description and model
    combined = f"{frame_val} {model_val}".lower()
    
    if 'carbon' in combined:
        return 'carbon'
    elif 'aluminium' in combined or 'aluminum' in combined:
        return 'aluminium'
    
    # If we have frame/model info but no material indicator, return None (unknown)
    return None

def get_motor_brand(bike):
    """Determine motor brand from bike data"""
    motor_val = bike.get('motor', '')
    # Define motor brands locally to avoid circular import
    motor_brands = ['shimano', 'bosch', 'tq', 'specialized', 'giant', 'fazua', 'dji', 'yamaha']
    for brand in motor_brands:
        if brand.lower() in motor_val.lower():
            return brand.lower()
    return 'other'

def translate_spec_key_to_hebrew(key):
    """
    Translate English spec key to Hebrew for display.
    Based on the translation dictionary used in bikes.js
    """
    # Comprehensive translation dictionary (English -> Hebrew)
    translations = {
        'brand': 'מותג',
        'model': 'דגם',
        'year': 'שנה',
        'bike_type': 'סוג אופניים',
        'bike_series': 'סדרה',
        'price': 'מחיר',
        'disc_price': 'מחיר מבצע',
        'motor': 'מנוע',
        'battery': 'סוללה',
        'wh': '(WH) סוללה',
        'fork': 'בולם קדמי',
        'rear_shock': 'בולם אחורי',
        'shock': 'בולם',
        'frame': 'שלדה',
        'tires': 'צמיגים',
        'brakes': 'בלמים',
        'weight': 'משקל',
        'wheel_size': 'גודל גלגלים',
        'sub_category': 'סוג אופניים',
        'size': 'מידה',
        'sizes': 'מידות',
        'sku': 'מק"ט',
        'gear_count': 'מספר הילוכים',
        'number_of_gears': 'מספר הילוכים',
        'front_brake': 'ברקס קידמי',
        'rear_brake': 'ברקס אחורי',
        'front_tire': 'צמיג קדמי',
        'rear_tire': 'צמיג אחורי',
        'saddle': 'אוכף',
        'pedals': 'דוושות',
        'charger': 'מטען',
        'screen': 'מסך',
        'extras': 'תוספות',
        'additionals': 'תוספות',
        'rear_der': 'מעביר אחורי',
        'shifter': 'שיפטר',
        'shifters': 'שיפטרים',
        'crank_set': 'קראנק',
        'crankset': 'קראנק',
        'crank': 'קראנק',
        'chain': 'שרשרת',
        'chainring': 'גלגל שיניים',
        'chainset': 'קראנק',
        'chainstay': 'זרוע אחורית',
        'cassette': 'קסטה',
        'rotors': 'רוטורים',
        'rotor': 'רוטור',
        'handlebar': 'כידון',
        'handelbar': 'כידון',
        'bar': 'כידון',
        'seat_post': 'מוט אוכף',
        'seatpost': 'מוט אוכף',
        'seatpost_clamp': 'מהדק מוט אוכף',
        'stem': 'סטם',
        'lights': 'תאורה',
        'lighting': 'תאורה',
        'wheels': 'גלגלים',
        'wheelset': 'סט גלגלים',
        'wheelbase': 'בסיס גלגלים',
        'rims': 'חישוקים',
        'spokes': 'חישורים',
        'front_hub': 'ציר קדמי',
        'rear_hub': 'ציר אחורי',
        'hub': 'רכזת',
        'hubs': 'רכזות',
        'headset': 'הד סט',
        'head_tube': 'צינור היגוי',
        'remote': 'שלט',
        'fork_length': 'אורך בולמים',
        'chain_guide': 'מדריך שרשרת',
        'chainguide': 'מדריך שרשרת',
        'tubes': 'פנימיות',
        'front_wheel': 'גלגל קדמי',
        'rear_wheel': 'גלגל אחורי',
        'rear_derailleur': 'מעביר אחורי',
        'rear derailleur': 'מעביר אחורי',
        'front_derailleur': 'מעביר קדמי',
        'front derailleur': 'מעביר קדמי',
        'derailleur': 'מעביר',
        'mech': 'מעביר',
        'bb': 'בראקט תחתון',
        'bottom_bracket': 'בראקט תחתון',
        'battery_capacity': 'קיבולת סוללה',
        'front_wheel_size': 'גודל גלגל קדמי',
        'rear_wheel_size': 'גודל גלגל אחורי',
        'battery_watts_per_hour': 'סוללה (WH)',
        'rear_wheel_maxtravel': 'מהלך מקסימלי אחורי',
        'brake_lever': 'ידית בלם',
        'brake_levers': 'ידיות בלם',
        'brake levers': 'ידיות בלם',
        'clamp': 'מהדק',
        'seat_clamp': 'מהדק אוכף',
        'front_axle': 'ציר קדמי',
        'rear_axle': 'ציר אחורי',
        'axle': 'ציר',
        'category': 'קטגוריה',
        'style': 'סגנון',
        'suspension': 'מתלה',
        'groupset': 'קבוצת העברה',
        'drivetrain': 'מערכת הינע',
        'display': 'תצוגה',
        'controller': 'בקר',
        'control_system': 'מערכת בקרה',
        'accessories': 'אביזרים',
        'grips': 'גריפים',
        'grip': 'גריפ',
        'seat': 'אוכף',
        'tire': 'צמיג',
        'tyres': 'צמיגים',
        'valve': 'ונטיל',
        'speed': 'מהירות',
        'speeds': 'הילוכים',
        'gears': 'הילוכים',
        'color': 'צבע',
        'colours': 'צבעים',
        'colors': 'צבעים',
        'material': 'חומר',
        'travel': 'מהלך',
        'trail': 'טרייל',
        'seat angle': 'זווית אוכף',
        'bottom bracket drop': 'ירידת בראקט',
        'front guide': 'מדריך קדמי',
        'diameter': 'קוטר',
        'width': 'רוחב',
        'length': 'אורך',
        'height': 'גובה',
        'angle': 'זווית',
        'reach': 'ריץ\'',
        'stack': 'סטאק',
        'range': 'טווח',
        'torque': 'מומנט',
        'power': 'עוצמה',
        'voltage': 'מתח',
        'amperage': 'עוצמת זרם',
        'charge_time': 'זמן טעינה',
        'charging_time': 'זמן טעינה',
        'rim_tape': 'סרט חישוק',
        'handlebar_tape': 'סרט כידון',
        'drive_system': 'מערכת הינע',
        'finish_color': 'גימור / צבע',
        'max_weight': 'משקל מקסימלי',
        'weight_limit': 'מגבלת משקל',
    }
    
    # Normalize key: lowercase and replace underscores/spaces
    normalized_key = key.lower().strip().replace('_', ' ').replace('-', ' ')
    
    # Try exact match first
    if key in translations:
        return translations[key]
    
    # Try normalized match
    if normalized_key in translations:
        return translations[normalized_key]
    
    # Try matching with spaces replaced by underscores
    key_with_underscores = normalized_key.replace(' ', '_')
    if key_with_underscores in translations:
        return translations[key_with_underscores]
    
    # If no translation found, return original key (might already be in Hebrew)
    return key