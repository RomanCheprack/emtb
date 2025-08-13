from flask import Blueprint, request, jsonify
from app.models.bike import get_session, Bike
from app.utils.helpers import clean_bike_data_for_json

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/bike/<path:bike_id>')
def get_bike_details(bike_id):
    """Get bike details by ID for AJAX requests"""
    try:
        db_session = get_session()
        
        # Find the bike with the exact ID
        bike = db_session.query(Bike).filter_by(id=bike_id).first()
        
        if not bike:
            return jsonify({'error': 'Bike not found'}), 404
        
        # Convert bike to dictionary with only needed fields
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
            'wh': str(bike.wh) if bike.wh else None,
            'fork_length': str(bike.fork_length) if bike.fork_length else None,
            'sub_category': str(bike.sub_category) if bike.sub_category else None,
        }
        
        # Clean the bike data to ensure it's safe for JSON serialization
        cleaned_bike_dict = clean_bike_data_for_json(bike_dict)
        
        return jsonify(cleaned_bike_dict)
        
    except Exception as e:
        print(f"Error getting bike details: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        db_session.close()
