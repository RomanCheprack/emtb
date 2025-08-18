from flask import Blueprint, request, jsonify
from app.models.bike import get_session, Bike
from app.utils.helpers import clean_bike_data_for_json
import hmac
import hashlib
import subprocess
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/test', methods=['GET'])
def api_test():
    """Simple test endpoint to verify API blueprint is working"""
    return jsonify({'status': 'ok', 'message': 'API blueprint is working'}), 200

@bp.route('/webhook/github', methods=['POST'])
def github_webhook():
    """GitHub webhook to automatically pull changes"""
    logger.info("GitHub webhook received")
    
    try:
        # Log request details for debugging
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request method: {request.method}")
        
        # Verify webhook signature
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            logger.error("No signature found in request")
            return jsonify({'error': 'No signature'}), 401
        
        # Get the webhook secret from config
        from app import create_app
        app = create_app()
        webhook_secret = app.config.get('GITHUB_WEBHOOK_SECRET')
        
        if not webhook_secret:
            logger.error("GITHUB_WEBHOOK_SECRET not configured")
            return jsonify({'error': 'Webhook secret not configured'}), 500
        
        # Verify the signature
        expected_signature = 'sha256=' + hmac.new(
            webhook_secret.encode('utf-8'),
            request.data,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            logger.error(f"Invalid signature. Expected: {expected_signature}, Got: {signature}")
            return jsonify({'error': 'Invalid signature'}), 401
        
        # Check if this is a push event
        event_type = request.headers.get('X-GitHub-Event')
        logger.info(f"GitHub event type: {event_type}")
        
        if event_type != 'push':
            logger.info(f"Ignoring non-push event: {event_type}")
            return jsonify({'message': 'Ignored non-push event'}), 200
        
        # Get the repository path (adjust this to your actual path on PythonAnywhere)
        repo_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logger.info(f"Repository path: {repo_path}")
        
        # Check if git is available
        try:
            git_version = subprocess.run(['git', '--version'], capture_output=True, text=True)
            logger.info(f"Git version: {git_version.stdout.strip()}")
        except Exception as e:
            logger.error(f"Git not available: {e}")
            return jsonify({'error': 'Git not available'}), 500
        
        # Pull the latest changes
        try:
            logger.info("Starting git pull...")
            result = subprocess.run(
                ['git', 'pull', 'origin', 'main'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60  # Increased timeout
            )
            
            logger.info(f"Git pull return code: {result.returncode}")
            logger.info(f"Git pull stdout: {result.stdout}")
            logger.info(f"Git pull stderr: {result.stderr}")
            
            if result.returncode == 0:
                logger.info("Successfully pulled changes")
                
                # Touch the WSGI file to trigger a reload (PythonAnywhere specific)
                wsgi_file = os.path.join(repo_path, 'wsgi.py')
                if os.path.exists(wsgi_file):
                    os.utime(wsgi_file, None)
                    logger.info("Touched wsgi.py to trigger reload")
                else:
                    logger.warning(f"wsgi.py not found at {wsgi_file}")
                
                # Alternative: Create a reload trigger file
                reload_file = os.path.join(repo_path, 'reload.txt')
                try:
                    with open(reload_file, 'w') as f:
                        f.write(f"Reload triggered at {os.popen('date').read().strip()}")
                    logger.info("Created reload trigger file")
                except Exception as e:
                    logger.warning(f"Could not create reload file: {e}")
                
                return jsonify({
                    'message': 'Successfully pulled changes and triggered reload',
                    'stdout': result.stdout,
                    'repo_path': repo_path
                }), 200
            else:
                logger.error(f"Git pull failed with return code {result.returncode}")
                return jsonify({
                    'error': 'Failed to pull changes',
                    'stderr': result.stderr,
                    'return_code': result.returncode
                }), 500
                
        except subprocess.TimeoutExpired:
            logger.error("Git pull timed out")
            return jsonify({'error': 'Git pull timed out'}), 500
        except Exception as e:
            logger.error(f"Git pull failed: {str(e)}")
            return jsonify({'error': f'Git pull failed: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/webhook/test', methods=['GET'])
def webhook_test():
    """Test endpoint to verify webhook configuration"""
    try:
        from app import create_app
        app = create_app()
        webhook_secret = app.config.get('GITHUB_WEBHOOK_SECRET')
        
        # Get repository path
        repo_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Check if git is available
        git_available = False
        git_version = "Not available"
        try:
            git_result = subprocess.run(['git', '--version'], capture_output=True, text=True)
            git_available = git_result.returncode == 0
            git_version = git_result.stdout.strip() if git_available else "Error"
        except Exception as e:
            git_version = f"Error: {str(e)}"
        
        # Check if wsgi.py exists
        wsgi_file = os.path.join(repo_path, 'wsgi.py')
        wsgi_exists = os.path.exists(wsgi_file)
        
        return jsonify({
            'status': 'ok',
            'webhook_secret_configured': bool(webhook_secret),
            'git_available': git_available,
            'git_version': git_version,
            'repo_path': repo_path,
            'wsgi_file_exists': wsgi_exists,
            'wsgi_file_path': wsgi_file,
            'environment': os.getenv('FLASK_ENV', 'development')
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

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
