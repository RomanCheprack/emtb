from flask import Blueprint, request, jsonify
from app.models.bike import get_session, Bike
from app.utils.helpers import clean_bike_data_for_json
import hmac
import hashlib
import subprocess
import os

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/webhook/github', methods=['POST'])
def github_webhook():
    """GitHub webhook to automatically pull changes"""
    try:
        # Verify webhook signature
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            return jsonify({'error': 'No signature'}), 401
        
        # Get the webhook secret from config
        from app import create_app
        app = create_app()
        webhook_secret = app.config.get('GITHUB_WEBHOOK_SECRET')
        
        if not webhook_secret:
            return jsonify({'error': 'Webhook secret not configured'}), 500
        
        # Verify the signature
        expected_signature = 'sha256=' + hmac.new(
            webhook_secret.encode('utf-8'),
            request.data,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return jsonify({'error': 'Invalid signature'}), 401
        
        # Check if this is a push event
        event_type = request.headers.get('X-GitHub-Event')
        if event_type != 'push':
            return jsonify({'message': 'Ignored non-push event'}), 200
        
        # Get the repository path (adjust this to your actual path on PythonAnywhere)
        repo_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Pull the latest changes
        try:
            result = subprocess.run(
                ['git', 'pull', 'origin', 'main'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"Successfully pulled changes: {result.stdout}")
                
                # Touch the WSGI file to trigger a reload (PythonAnywhere specific)
                wsgi_file = os.path.join(repo_path, 'wsgi.py')
                if os.path.exists(wsgi_file):
                    os.utime(wsgi_file, None)
                    print("Touched wsgi.py to trigger reload")
                
                return jsonify({
                    'message': 'Successfully pulled changes and triggered reload',
                    'stdout': result.stdout
                }), 200
            else:
                print(f"Error pulling changes: {result.stderr}")
                return jsonify({
                    'error': 'Failed to pull changes',
                    'stderr': result.stderr
                }), 500
                
        except subprocess.TimeoutExpired:
            return jsonify({'error': 'Git pull timed out'}), 500
        except Exception as e:
            return jsonify({'error': f'Git pull failed: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

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
            'weight': str(bike.weight) if bike.weight else None,
            'rear_derailleur': str(bike.rear_der) if bike.rear_der else None,
            'shifter': str(bike.shifter) if bike.shifter else None,
            'crank_set': str(bike.crank_set) if bike.crank_set else None,
            'chain_guide': None,  # Field not in database model
            'chain': str(bike.chain) if bike.chain else None,
            'cassette': str(bike.cassette) if bike.cassette else None,
            'brakes': str(bike.brakes) if bike.brakes else None,
            'rotors': None,  # Field not in database model
            'handlebar': str(bike.handelbar) if bike.handelbar else None,
            'seat_post': str(bike.seat_post) if bike.seat_post else None,
            'saddle': str(bike.saddle) if bike.saddle else None,
            'headset': str(bike.headset) if bike.headset else None,
            'front_hub': str(bike.front_axle) if bike.front_axle else None,
            'rear_hub': str(bike.rear_axle) if bike.rear_axle else None,
            'rims': str(bike.rims) if bike.rims else None,
            'spokes': str(bike.spokes) if bike.spokes else None,
            'front_tire': str(bike.front_tire) if bike.front_tire else None,
            'rear_tire': str(bike.rear_tire) if bike.rear_tire else None,
            'stem': str(bike.stem) if bike.stem else None,
            'front_wheel': str(bike.front_wheel) if bike.front_wheel else None,
            'rear_wheel': str(bike.rear_wheel) if bike.rear_wheel else None,
            'tubes': str(bike.tubes) if bike.tubes else None,
        }
        
        # Clean the bike data to ensure it's safe for JSON serialization
        cleaned_bike_dict = clean_bike_data_for_json(bike_dict)
        
        return jsonify(cleaned_bike_dict)
        
    except Exception as e:
        print(f"Error getting bike details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500
    finally:
        if 'db_session' in locals():
            db_session.close()
