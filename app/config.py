import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Flask settings
    # IMPORTANT: SECRET_KEY must be stable across restarts, otherwise sessions will be invalidated
    # Set FLASK_SECRET_KEY in your .env file or environment variables
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
    if not SECRET_KEY:
        # Fallback: try to read from a file, or generate and warn
        secret_file = os.path.join(os.path.dirname(__file__), '..', '.secret_key')
        if os.path.exists(secret_file):
            with open(secret_file, 'r') as f:
                SECRET_KEY = f.read().strip()
        else:
            # Generate a new key and save it
            import secrets
            SECRET_KEY = secrets.token_urlsafe(32)
            try:
                with open(secret_file, 'w') as f:
                    f.write(SECRET_KEY)
            except:
                pass  # If we can't write, continue with generated key
    
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)  # Admin session expires after 24 hours
    
    # Session cookie settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_REFRESH_EACH_REQUEST = False  # Don't refresh session on each request (prevents premature expiration)
    
    # Version for cache busting
    VERSION = os.getenv('APP_VERSION', '1.0.0')
    
    # Cache settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # Feature flags
    USE_NEW_BIKE_FORMAT = os.getenv('USE_NEW_BIKE_FORMAT', 'false').lower() == 'true'
    
    # Database settings
    # Support both DATABASE_URL and SQLALCHEMY_DATABASE_URI for compatibility
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL', 'sqlite:///emtb.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 20
    }
    
    # OpenAI settings
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Email settings
    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASS = os.getenv('EMAIL_PASS')
    
    # GitHub webhook settings
    GITHUB_WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET')
    
    # Motor brands for filtering
    MOTOR_BRANDS = [
        'shimano', 'bosch', 'tq', 'specialized', 'giant', 'fazua', 'dji', 'yamaha'
    ]

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    # Production-specific settings
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year cache for static files
    
    # Ensure static files are served correctly
    STATIC_FOLDER = '../static'
    STATIC_URL_PATH = '/static'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
