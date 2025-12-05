from flask import Blueprint, request, jsonify
from app.extensions import csrf, cache, db
from app.models import Bike, BikeListing
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

@bp.route('/webhook/github', methods=['POST'])
@csrf.exempt
def github_webhook():
    """GitHub webhook to automatically pull changes"""
    logger.info("GitHub webhook received")
    
    try:
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
        try:
            expected_signature = 'sha256=' + hmac.new(
                webhook_secret.encode('utf-8'),
                request.data,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.error(f"Invalid signature. Expected: {expected_signature}, Got: {signature}")
                return jsonify({'error': 'Invalid signature'}), 401
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return jsonify({'error': 'Signature verification failed'}), 400
        
        # Check if this is a push event
        event_type = request.headers.get('X-GitHub-Event')
        logger.info(f"GitHub event type: {event_type}")
        
        if event_type != 'push':
            logger.info(f"Ignoring non-push event: {event_type}")
            return jsonify({'message': 'Ignored non-push event'}), 200
        
        # Get the repository path
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
                timeout=60
            )
            
            logger.info(f"Git pull return code: {result.returncode}")
            
            if result.returncode == 0:
                logger.info("Successfully pulled changes")
                
                # Touch the WSGI file to trigger a reload (PythonAnywhere specific)
                wsgi_file = os.path.join(repo_path, 'wsgi.py')
                if os.path.exists(wsgi_file):
                    os.utime(wsgi_file, None)
                    logger.info("Touched wsgi.py to trigger reload")
                
                # Create a reload trigger file as backup
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

@bp.route('/bike/<path:bike_id>')
def get_bike_details(bike_id):
    """Get bike details by UUID for AJAX requests"""
    try:
        # Find the bike by UUID (bike_id is actually UUID in new schema)
        # Load with raw_specs relationship
        bike = db.session.query(Bike).options(
            db.joinedload(Bike.brand),
            db.joinedload(Bike.listings).joinedload(BikeListing.raw_specs),
            db.joinedload(Bike.listings).joinedload(BikeListing.prices),
            db.joinedload(Bike.images)
        ).filter_by(uuid=bike_id).first()
        
        if not bike:
            return jsonify({'error': 'Bike not found'}), 404
        
        # Convert to template-compatible format
        bike_dict = bike.to_dict()
        
        # Clean the bike data to ensure it's safe for JSON serialization
        cleaned_bike_dict = clean_bike_data_for_json(bike_dict)
        
        # Debug logging
        print(f"=== API DEBUG for bike {bike_id} ===")
        print(f"Gallery field in dict: {bike_dict.get('gallery_images_urls')}")
        print(f"Gallery field in cleaned: {cleaned_bike_dict.get('gallery_images_urls')}")
        print(f"Raw specs count: {len(bike.listings[0].raw_specs) if bike.listings and bike.listings[0].raw_specs else 0}")
        print("=== END API DEBUG ===")
        
        return jsonify(cleaned_bike_dict)
        
    except Exception as e:
        print(f"Error getting bike details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@bp.route('/v2/bike/<path:bike_id>')
def get_bike_details_v2(bike_id):
    """Get bike details using NEW normalized format (for testing)"""
    try:
        # Find the bike by UUID
        bike = db.session.query(Bike).filter_by(uuid=bike_id).first()
        
        if not bike:
            return jsonify({'error': 'Bike not found'}), 404
        
        # Use to_dict() method
        bike_dict = bike.to_dict()
        
        # Clean the bike data to ensure it's safe for JSON serialization
        cleaned_bike_dict = clean_bike_data_for_json(bike_dict)
        
        return jsonify(cleaned_bike_dict)
        
    except Exception as e:
        print(f"Error getting bike details (v2): {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@bp.route('/clear-cache')
def clear_cache():
    """Clear all caches for debugging"""
    try:
        cache.clear()
        return jsonify({'message': 'Cache cleared successfully'})
    except Exception as e:
        return jsonify({'error': f'Failed to clear cache: {str(e)}'}), 500
