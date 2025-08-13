from app.models.bike import get_session, Bike
from app.extensions import cache
from app.utils.helpers import clean_bike_data_for_json

@cache.memoize(timeout=300)  # Cache for 5 minutes
def load_all_bikes():
    """Load all bikes from the database with optimized querying"""
    db_session = get_session()
    try:
        # Use more efficient query with specific columns
        bikes = db_session.query(Bike).all()
        
        # Convert to dictionaries more efficiently
        bikes_data = []
        for bike in bikes:
            # Convert all values to strings to avoid any complex object issues
            bike_dict = {
                'id': str(bike.id) if bike.id else None,
                'firm': str(bike.firm) if bike.firm else None,
                'model': str(bike.model) if bike.model else None,
                'year': str(bike.year) if bike.year else None,
                'price': str(bike.price) if bike.price else None,
                'disc_price': str(bike.disc_price) if bike.disc_price else None,
                'frame': str(bike.frame) if bike.frame else None,
                'motor': str(bike.motor) if bike.motor else None,
                'battery': str(bike.battery) if bike.battery else None,
                'fork': str(bike.fork) if bike.fork else None,
                'rear_shock': str(bike.rear_shock) if bike.rear_shock else None,
                'image_url': str(bike.image_url) if bike.image_url else None,
                'product_url': str(bike.product_url) if bike.product_url else None,
                'stem': str(bike.stem) if bike.stem else None,
                'handelbar': str(bike.handelbar) if bike.handelbar else None,
                'front_brake': str(bike.front_brake) if bike.front_brake else None,
                'rear_brake': str(bike.rear_brake) if bike.rear_brake else None,
                'shifter': str(bike.shifter) if bike.shifter else None,
                'rear_der': str(bike.rear_der) if bike.rear_der else None,
                'cassette': str(bike.cassette) if bike.cassette else None,
                'chain': str(bike.chain) if bike.chain else None,
                'crank_set': str(bike.crank_set) if bike.crank_set else None,
                'front_wheel': str(bike.front_wheel) if bike.front_wheel else None,
                'rear_wheel': str(bike.rear_wheel) if bike.rear_wheel else None,
                'rims': str(bike.rims) if bike.rims else None,
                'front_axle': str(bike.front_axle) if bike.front_axle else None,
                'rear_axle': str(bike.rear_axle) if bike.rear_axle else None,
                'spokes': str(bike.spokes) if bike.spokes else None,
                'tubes': str(bike.tubes) if bike.tubes else None,
                'front_tire': str(bike.front_tire) if bike.front_tire else None,
                'rear_tire': str(bike.rear_tire) if bike.rear_tire else None,
                'saddle': str(bike.saddle) if bike.saddle else None,
                'seat_post': str(bike.seat_post) if bike.seat_post else None,
                'clamp': str(bike.clamp) if bike.clamp else None,
                'charger': str(bike.charger) if bike.charger else None,
                'wheel_size': str(bike.wheel_size) if bike.wheel_size else None,
                'headset': str(bike.headset) if bike.headset else None,
                'brake_lever': str(bike.brake_lever) if bike.brake_lever else None,
                'screen': str(bike.screen) if bike.screen else None,
                'extras': str(bike.extras) if bike.extras else None,
                'pedals': str(bike.pedals) if bike.pedals else None,
                'bb': str(bike.bb) if bike.bb else None,
                'weight': str(bike.weight) if bike.weight else None,
                'size': str(bike.size) if bike.size else None,
                'hub': str(bike.hub) if bike.hub else None,
                'brakes': str(bike.brakes) if bike.brakes else None,
                'tires': str(bike.tires) if bike.tires else None,
                'wh': str(bike.wh) if bike.wh else None,
                'gallery_images_urls': str(bike.gallery_images_urls) if bike.gallery_images_urls else None,
                'fork_length': str(bike.fork_length) if bike.fork_length else None,
                'sub_category': str(bike.sub_category) if bike.sub_category else None,
                'rear_wheel_maxtravel': str(bike.rear_wheel_maxtravel) if bike.rear_wheel_maxtravel else None,
                'battery_capacity': str(bike.battery_capacity) if bike.battery_capacity else None,
                'front_wheel_size': str(bike.front_wheel_size) if bike.front_wheel_size else None,
                'rear_wheel_size': str(bike.rear_wheel_size) if bike.rear_wheel_size else None,
                'battery_watts_per_hour': str(bike.battery_watts_per_hour) if bike.battery_watts_per_hour else None,
            }
            # Clean the bike data to ensure it's safe for JSON serialization
            cleaned_bike_dict = clean_bike_data_for_json(bike_dict)
            bikes_data.append(cleaned_bike_dict)
        return bikes_data
    finally:
        db_session.close()

@cache.memoize(timeout=600)  # Cache for 10 minutes
def get_all_firms():
    """Get all unique firms from database"""
    db_session = get_session()
    try:
        firms = db_session.query(Bike.firm).distinct().all()
        return sorted([firm[0] for firm in firms if firm[0]])
    finally:
        db_session.close()

@cache.memoize(timeout=600)  # Cache for 10 minutes
def get_all_sub_categories():
    """Get all unique sub-categories from database"""
    db_session = get_session()
    try:
        sub_categories = db_session.query(Bike.sub_category).distinct().all()
        return sorted([cat[0] for cat in sub_categories if cat[0] and cat[0].lower() != 'unknown'])
    finally:
        db_session.close()
