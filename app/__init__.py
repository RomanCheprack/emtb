from flask import Flask
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os

# Import extensions
from .extensions import cache, csrf

def create_app(config_name=None):
    """Application factory function"""
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Create Flask app
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Configure app
    app.config.from_object('app.config.Config')
    
    # Initialize extensions
    cache.init_app(app)
    csrf.init_app(app)
    
    # Register blueprints
    from .routes import main, bikes, blog, compare, api
    
    app.register_blueprint(main.bp)
    app.register_blueprint(bikes.bp)
    app.register_blueprint(blog.bp)
    app.register_blueprint(compare.bp)
    app.register_blueprint(api.bp)
    
    # Register Jinja2 filters
    from .utils.helpers import format_number_with_commas
    app.jinja_env.filters['format_number'] = format_number_with_commas
    
    # Initialize database
    from .models.bike import init_db
    init_db()
    
    # Register error handlers
    from .utils.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    return app
