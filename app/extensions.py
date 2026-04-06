from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize Flask extensions
cache = Cache()
csrf = CSRFProtect()
db = SQLAlchemy()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
