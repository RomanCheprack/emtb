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
    """Determine frame material from bike data"""
    frame_val = bike.get('frame', '')
    model_val = bike.get('model', '')
    combined = f"{frame_val} {model_val}".lower()
    if 'carbon' in combined:
        return 'carbon'
    return 'aluminium'

def get_motor_brand(bike):
    """Determine motor brand from bike data"""
    motor_val = bike.get('motor', '')
    # Define motor brands locally to avoid circular import
    motor_brands = ['shimano', 'bosch', 'tq', 'specialized', 'giant', 'fazua', 'dji', 'yamaha']
    for brand in motor_brands:
        if brand.lower() in motor_val.lower():
            return brand.lower()
    return 'other'
