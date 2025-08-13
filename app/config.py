import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY') or os.urandom(24)
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Cache settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # Database settings
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///emtb.db')
    
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
