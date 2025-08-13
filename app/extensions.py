from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect

# Initialize Flask extensions
cache = Cache()
csrf = CSRFProtect()
