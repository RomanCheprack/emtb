from flask import jsonify, request, flash, redirect, url_for

def register_error_handlers(app):
    """Register error handlers for the application"""
    
    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/') or request.path.startswith('/add_to_compare/') or request.path.startswith('/remove_from_compare/'):
            return jsonify({'success': False, 'error': 'Internal server error'}), 500
        return error

    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/') or request.path.startswith('/add_to_compare/') or request.path.startswith('/remove_from_compare/'):
            return jsonify({'success': False, 'error': 'Route not found'}), 404
        return error

    @app.errorhandler(400)
    def bad_request_error(error):
        if request.path.startswith('/api/') or request.path.startswith('/add_to_compare/') or request.path.startswith('/remove_from_compare/'):
            return jsonify({'success': False, 'error': 'Bad request'}), 400
        return error
