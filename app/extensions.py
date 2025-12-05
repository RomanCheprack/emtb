from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy

# Initialize Flask extensions
cache = Cache()
csrf = CSRFProtect()
db = SQLAlchemy()
