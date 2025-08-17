from flask import Blueprint, current_app, send_from_directory, jsonify
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
    
    return jsonify({
        'static_folder': static_folder,
        'static_url_path': static_url_path,
        'image_path': image_path,
        'file_exists': file_exists,
        'file_size': os.path.getsize(image_path) if file_exists else None,
        'expected_url': f'{static_url_path}/images/blog/electric_bike_alps_man_riding.jpg'
    })

@bp.route('/debug/static/<path:filename>')
def serve_static_debug(filename):
    """Debug route to serve static files directly"""
    return send_from_directory(current_app.static_folder, filename)
