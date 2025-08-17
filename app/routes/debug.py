from flask import Blueprint, current_app, send_from_directory, jsonify, render_template
import os

bp = Blueprint('debug', __name__)

@bp.route('/debug/static-test')
def static_test():
    """Debug route to test static file serving"""
    static_folder = current_app.static_folder
    static_url_path = current_app.static_url_path
    
    # Check if the image file exists
    image_path = os.path.join(static_folder, 'images', 'blog', 'electric_bike_alps_man_riding.jpg')
    file_exists = os.path.exists(image_path)
    
    # Get file permissions
    file_permissions = None
    if file_exists:
        try:
            file_permissions = oct(os.stat(image_path).st_mode)[-3:]
        except:
            pass
    
    return jsonify({
        'static_folder': static_folder,
        'static_url_path': static_url_path,
        'image_path': image_path,
        'file_exists': file_exists,
        'file_size': os.path.getsize(image_path) if file_exists else None,
        'file_permissions': file_permissions,
        'expected_url': f'{static_url_path}/images/blog/electric_bike_alps_man_riding.jpg',
        'flask_env': os.getenv('FLASK_ENV', 'not_set'),
        'flask_debug': os.getenv('FLASK_DEBUG', 'not_set')
    })

@bp.route('/debug/static/<path:filename>')
def serve_static_debug(filename):
    """Debug route to serve static files directly"""
    return send_from_directory(current_app.static_folder, filename)

@bp.route('/debug/page')
def debug_page():
    """Debug page to test static files"""
    return render_template('debug.html')
