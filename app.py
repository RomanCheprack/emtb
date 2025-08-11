from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, abort, Response
from flask_caching import Cache
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, timedelta
from email.message import EmailMessage
import json
import os
import smtplib
from scripts.db.models import init_db, get_session, Bike, Comparison, CompareCount
from sqlalchemy import or_ # Added for OR queries in filter_bikes

# --- NEW IMPORTS FOR WEBHOOK ---
import subprocess # To run shell commands like 'git pull'
import hmac # For cryptographic signing and verification (webhook secret)
import hashlib # For hashing (part of cryptographic signing)
# --- END NEW IMPORTS ---

def format_number_with_commas(value):
    """Format a number with commas for better readability"""
    if value is None:
        return ""
    
    # Handle edge cases
    if isinstance(value, (dict, list)):
        return str(value)
    
    # Convert to string first to check if it's a text value
    value_str = str(value).strip()
    
    # If it's the Hebrew text "צור קשר", return it as-is
    if value_str == "צור קשר":
        return value_str
    
    try:
        # Convert to integer and format with commas
        return "{:,}".format(int(float(value)))
    except (ValueError, TypeError):
        # If conversion fails, return the original value
        return value_str

app = Flask(__name__)
load_dotenv(override=True)  # Load .env variables

# Register Jinja2 filter for number formatting
app.jinja_env.filters['format_number'] = format_number_with_commas

# Enable debug mode for better error messages
app.debug = True

# Configure caching
cache = Cache(config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutes
})
cache.init_app(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app.secret_key = 'app_secret_key'  # Set a secure secret key!

# Initialize database
init_db()

# Global error handler for JSON routes
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

GITHUB_WEBHOOK_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET')

if not GITHUB_WEBHOOK_SECRET:
    print("WARNING: GITHUB_WEBHOOK_SECRET is not set! Webhook will be insecure in production.")

MOTOR_BRANDS = [
    'shimano', 'bosch', 'tq', 'specialized', 'giant', 'fazua', 'dji', 'yamaha'
]

@app.route('/sitemap.xml', methods=['GET'])
def sitemap():
    pages = []
    now = datetime.now()
    ten_days_ago = (datetime.now() - timedelta(days=10)).date().isoformat()

    # Static pages
    pages.append({
        'loc': url_for('home', _external=True),
        'lastmod': ten_days_ago,
        'priority': '1.0'
    })
    pages.append({
        'loc': url_for('bikes', _external=True),
        'lastmod': ten_days_ago,
        'priority': '0.8'
    })
    pages.append({
        'loc': url_for('blog_list', _external=True),
        'lastmod': ten_days_ago,
        'priority': '0.8'
    })

    # Blog posts
    blog_posts = load_posts()
    for post in blog_posts:
        pages.append({
            'loc': url_for('blog_post', slug=post['slug'], _external=True),
            'lastmod': post['date'],
            'priority': '0.6'
        })

    # Individual bike pages
    bikes = load_all_bikes()
    for bike in bikes:
        pages.append({
            'loc': url_for('bikes', bike_id=bike['id'], _external=True),
            'lastmod': ten_days_ago,
            'priority': '0.5'
        })

    # Add persistent comparison pages
    session = get_session()
    try:
        # Comparison is already imported at the top of the file
        comparisons = session.query(Comparison).all()
        for comparison in comparisons:
            if comparison.slug:
                pages.append({
                    'loc': url_for('view_comparison', slug=comparison.slug, _external=True),
                    'lastmod': comparison.created_at.date().isoformat() if comparison.created_at else ten_days_ago,
                    'priority': '0.7'
                })
    finally:
        session.close()

    # Create XML string
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    return Response(sitemap_xml, mimetype='application/xml')

@app.route("/contact", methods=["POST"])
def contact():
    name = request.form["Name"]
    email = request.form["Email"]
    message = request.form["Message"]

    # Construct the email
    msg = EmailMessage()
    msg["Subject"] = f"New Contact from {name}"
    msg["From"] = email
    msg["To"] = "rideal.bikes@gmail.com"
    msg.set_content(f"Name: {name}\nEmail: {email}\nMessage:\n{message}")

    # Send the email (adjust SMTP settings)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            print("EMAIL_USER from os.getenv:", os.getenv("EMAIL_USER"))
            print("EMAIL_PASS from os.getenv:", os.getenv("EMAIL_PASS"))
            print("About to login to SMTP")
            smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
            print("Logged in to SMTP")
            smtp.send_message(msg)
        return render_template("contact_success.html")
    except Exception as e:
        print("Email failed:", e)
        return "אירעה שגיאה בשליחת ההודעה", 500

def load_posts():
    with open("templates/posts/posts.json", encoding="utf-8-sig") as f:
        return json.load(f)

@app.route("/blog")
def blog_list():
    posts = load_posts()
    return render_template("blog_list.html", posts=posts)

@app.route("/blog/<slug>")
def blog_post(slug):
    posts = load_posts()
    post = next((p for p in posts if p["slug"] == slug), None)
    if not post:
        abort(404)

    post["date"] = datetime.strptime(post["date"], "%Y-%m-%d")

    # מיקום הקובץ עם התוכן של הפוסט
    content_path = os.path.join("templates", "posts", f"{slug}.html")
    if not os.path.exists(content_path):
        abort(404)

    # קורא את התוכן של קובץ ה-HTML לפוסט
    with open(content_path, encoding="utf-8") as f:
        post_content = f.read()

    # מוסיף את התוכן שנקרא למשתנה post['content']
    post["content"] = post_content

    return render_template("blog_post.html", post=post)

@cache.memoize(timeout=300)  # Cache for 5 minutes
def load_all_bikes():
    """Load all bikes from the database with optimized querying"""
    db_session = get_session()
    try:
        # Use more efficient query with specific columns
        bikes = db_session.query(Bike).all()
        
        # Convert to dictionaries more efficiently
        bikes_data = []
        for bike in bikes:
            # Convert all values to strings to avoid any complex object issues
            bike_dict = {
                'id': str(bike.id) if bike.id else None,
                'firm': str(bike.firm) if bike.firm else None,
                'model': str(bike.model) if bike.model else None,
                'year': str(bike.year) if bike.year else None,
                'price': str(bike.price) if bike.price else None,
                'disc_price': str(bike.disc_price) if bike.disc_price else None,
                'frame': str(bike.frame) if bike.frame else None,
                'motor': str(bike.motor) if bike.motor else None,
                'battery': str(bike.battery) if bike.battery else None,
                'fork': str(bike.fork) if bike.fork else None,
                'rear_shock': str(bike.rear_shock) if bike.rear_shock else None,
                'image_url': str(bike.image_url) if bike.image_url else None,
                'product_url': str(bike.product_url) if bike.product_url else None,
                'stem': str(bike.stem) if bike.stem else None,
                'handelbar': str(bike.handelbar) if bike.handelbar else None,
                'front_brake': str(bike.front_brake) if bike.front_brake else None,
                'rear_brake': str(bike.rear_brake) if bike.rear_brake else None,
                'shifter': str(bike.shifter) if bike.shifter else None,
                'rear_der': str(bike.rear_der) if bike.rear_der else None,
                'cassette': str(bike.cassette) if bike.cassette else None,
                'chain': str(bike.chain) if bike.chain else None,
                'crank_set': str(bike.crank_set) if bike.crank_set else None,
                'front_wheel': str(bike.front_wheel) if bike.front_wheel else None,
                'rear_wheel': str(bike.rear_wheel) if bike.rear_wheel else None,
                'rims': str(bike.rims) if bike.rims else None,
                'front_axle': str(bike.front_axle) if bike.front_axle else None,
                'rear_axle': str(bike.rear_axle) if bike.rear_axle else None,
                'spokes': str(bike.spokes) if bike.spokes else None,
                'tubes': str(bike.tubes) if bike.tubes else None,
                'front_tire': str(bike.front_tire) if bike.front_tire else None,
                'rear_tire': str(bike.rear_tire) if bike.rear_tire else None,
                'saddle': str(bike.saddle) if bike.saddle else None,
                'seat_post': str(bike.seat_post) if bike.seat_post else None,
                'clamp': str(bike.clamp) if bike.clamp else None,
                'charger': str(bike.charger) if bike.charger else None,
                'wheel_size': str(bike.wheel_size) if bike.wheel_size else None,
                'headset': str(bike.headset) if bike.headset else None,
                'brake_lever': str(bike.brake_lever) if bike.brake_lever else None,
                'screen': str(bike.screen) if bike.screen else None,
                'extras': str(bike.extras) if bike.extras else None,
                'pedals': str(bike.pedals) if bike.pedals else None,
                'bb': str(bike.bb) if bike.bb else None,
                'weight': str(bike.weight) if bike.weight else None,
                'size': str(bike.size) if bike.size else None,
                'hub': str(bike.hub) if bike.hub else None,
                'brakes': str(bike.brakes) if bike.brakes else None,
                'tires': str(bike.tires) if bike.tires else None,
                'wh': str(bike.wh) if bike.wh else None,
                'gallery_images_urls': str(bike.gallery_images_urls) if bike.gallery_images_urls else None,
                'fork_length': str(bike.fork_length) if bike.fork_length else None,
                'sub_category': str(bike.sub_category) if bike.sub_category else None,
                'rear_wheel_maxtravel': str(bike.rear_wheel_maxtravel) if bike.rear_wheel_maxtravel else None,
                'battery_capacity': str(bike.battery_capacity) if bike.battery_capacity else None,
                'front_wheel_size': str(bike.front_wheel_size) if bike.front_wheel_size else None,
                'rear_wheel_size': str(bike.rear_wheel_size) if bike.rear_wheel_size else None,
                'battery_watts_per_hour': str(bike.battery_watts_per_hour) if bike.battery_watts_per_hour else None,
            }
            # Clean the bike data to ensure it's safe for JSON serialization
            cleaned_bike_dict = clean_bike_data_for_json(bike_dict)
            bikes_data.append(cleaned_bike_dict)
        return bikes_data
    finally:
        db_session.close()

@cache.memoize(timeout=600)  # Cache for 10 minutes
def get_all_firms():
    """Get all unique firms from database"""
    db_session = get_session()
    try:
        firms = db_session.query(Bike.firm).distinct().all()
        return sorted([firm[0] for firm in firms if firm[0]])
    finally:
        db_session.close()

@cache.memoize(timeout=600)  # Cache for 10 minutes
def get_all_sub_categories():
    """Get all unique sub-categories from database"""
    db_session = get_session()
    try:
        sub_categories = db_session.query(Bike.sub_category).distinct().all()
        return sorted([cat[0] for cat in sub_categories if cat[0]])
    finally:
        db_session.close()

def load_bikes_for_display(limit=None, offset=0):
    """Load bikes with pagination for better performance"""
    db_session = get_session()
    try:
        query = db_session.query(Bike)
        if limit:
            query = query.limit(limit).offset(offset)
        bikes = query.all()
        
        bikes_data = []
        for bike in bikes:
            # Convert all values to strings to avoid any complex object issues
            bike_dict = {
                'id': str(bike.id) if bike.id else None,
                'Firm': str(bike.firm) if bike.firm else None,
                'Model': str(bike.model) if bike.model else None,
                'Year': str(bike.year) if bike.year else None,
                'Price': str(bike.price) if bike.price else None,
                'Disc_price': str(bike.disc_price) if bike.disc_price else None,
                'Frame': str(bike.frame) if bike.frame else None,
                'Motor': str(bike.motor) if bike.motor else None,
                'Battery': str(bike.battery) if bike.battery else None,
                'Fork': str(bike.fork) if bike.fork else None,
                'Rear Shock': str(bike.rear_shock) if bike.rear_shock else None,
                'Image URL': str(bike.image_url) if bike.image_url else None,
                'Product URL': str(bike.product_url) if bike.product_url else None,
                'wh': str(bike.wh) if bike.wh else None,
                'fork_length': str(bike.fork_length) if bike.fork_length else None,
                'sub_category': str(bike.sub_category) if bike.sub_category else None,
            }
            # Clean the bike data to ensure it's safe for JSON serialization
            cleaned_bike_dict = clean_bike_data_for_json(bike_dict)
            bikes_data.append(cleaned_bike_dict)
        return bikes_data
    finally:
        db_session.close()

def parse_price(price_str):
    if not price_str:
        return None
    digits_only = ''.join(filter(str.isdigit, str(price_str)))
    return int(digits_only) if digits_only else None

def clean_bike_data_for_json(bike_dict):
    """Clean bike data to ensure it's safe for JSON serialization"""
    import re
    cleaned_dict = {}
    for key, value in bike_dict.items():
        if value is not None:
            # Convert to string and clean any problematic characters
            cleaned_value = str(value)
            
            # Remove all control characters except basic whitespace
            cleaned_value = ''.join(char for char in cleaned_value if ord(char) >= 32 or char in ' \t\n\r')
            
            # Replace problematic characters that could break JSON
            cleaned_value = cleaned_value.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            cleaned_value = cleaned_value.replace('"', "'")   # Replace double quotes with single quotes
            cleaned_value = cleaned_value.replace('\\', '/')  # Replace backslashes with forward slashes
            cleaned_value = cleaned_value.replace(';', ', ')  # Replace semicolons with commas
            
            # Remove any remaining control characters
            cleaned_value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned_value)
            
            # Remove duplicate spaces
            cleaned_value = re.sub(r'\s+', ' ', cleaned_value)
            
            # Trim whitespace
            cleaned_value = cleaned_value.strip()
            
            if cleaned_value:  # Only add non-empty values
                cleaned_dict[key] = cleaned_value
        else:
            cleaned_dict[key] = None
    return cleaned_dict


@app.route("/")
def home():
    all_bikes = load_all_bikes()
    firms = get_all_firms()

    # ✅ Load compare counts from database
    db_session = get_session()
    try:
        top_compare_counts = db_session.query(CompareCount).order_by(CompareCount.count.desc()).limit(3).all()
        top_ids = [cc.bike_id for cc in top_compare_counts]
        top_bikes = [bike for bike in all_bikes if bike.get("id") in top_ids]
    except Exception as e:
        print(f"Error loading compare counts: {e}")
        top_bikes = []
    finally:
        db_session.close()

    return render_template("home.html", bikes=all_bikes, firms=firms, top_bikes=top_bikes)




@app.route("/bikes")
def bikes():
    all_bikes = load_all_bikes()
    firms = get_all_firms()
    sub_categories = get_all_sub_categories()
    
    return render_template("bikes.html", bikes=all_bikes, firms=firms, sub_categories=sub_categories)
def parse_battery(battery_str):
    if not battery_str:
        return None
    # Extract digits from the string (e.g., "625Wh" -> 625)
    digits = ''.join(filter(str.isdigit, battery_str))
    return int(digits) if digits else None

def get_frame_material(bike):
    frame_val = bike.get('frame', '')
    model_val = bike.get('model', '')
    combined = f"{frame_val} {model_val}".lower()
    if 'carbon' in combined:
        return 'carbon'
    return 'aluminium'

def get_motor_brand(bike):
    motor_val = bike.get('motor', '')
    for brand in MOTOR_BRANDS:
        if brand.lower() in motor_val.lower():
            return brand.lower()
    return 'other'

@app.route("/api/filter_bikes")
def filter_bikes():
    db_session = get_session()
    try:
        query = request.args.get("q", "").strip().lower()
        min_price = request.args.get("min_price", type=int)
        max_price = request.args.get("max_price", type=int)
        years = request.args.getlist("year", type=int)
        firms = request.args.getlist("firm")
        min_battery = request.args.get("min_battery", type=int)
        max_battery = request.args.get("max_battery", type=int)
        frame_material = request.args.get("frame_material", type=str)
        motor_brands = request.args.getlist("motor_brand", type=str)
        sub_categories = request.args.getlist("sub_category", type=str)

        # Start with base query - only select needed columns for better performance
        db_query = db_session.query(
            Bike.id, Bike.firm, Bike.model, Bike.year, Bike.price, Bike.disc_price,
            Bike.frame, Bike.motor, Bike.battery, Bike.fork, Bike.rear_shock,
            Bike.image_url, Bike.product_url, Bike.wh, Bike.fork_length, Bike.sub_category
        )

        # Apply filters using database queries for better performance
        if query:
            # Search across multiple fields using OR conditions
            search_conditions = []
            for field in [Bike.firm, Bike.model, Bike.frame, Bike.motor, Bike.battery]:
                search_conditions.append(field.ilike(f'%{query}%'))
            db_query = db_query.filter(or_(*search_conditions))

        if years:
            db_query = db_query.filter(Bike.year.in_(years))

        if firms:
            db_query = db_query.filter(Bike.firm.in_(firms))

        if min_battery is not None and min_battery > 200:
            db_query = db_query.filter(Bike.wh >= min_battery)

        if max_battery is not None and max_battery < 1000:
            db_query = db_query.filter(Bike.wh <= max_battery)

        if sub_categories:
            db_query = db_query.filter(Bike.sub_category.in_(sub_categories))

        # Execute query and convert to list for faster iteration
        bikes = db_query.all()

        # Apply price filtering (since price is stored as string)
        filtered_bikes = []
        for bike in bikes:
            # Price filtering
            price_str = bike.disc_price or bike.price
            price = parse_price(price_str)
            
            if min_price is not None and min_price > 0:
                if price is not None and price < min_price:
                    continue
            if max_price is not None and max_price < 100000:
                if price is not None and price > max_price:
                    continue

            # Frame material filtering
            if frame_material:
                bike_frame_material = get_frame_material({
                    'frame': bike.frame,
                    'model': bike.model
                })
                if bike_frame_material != frame_material.lower():
                    continue

            # Motor brand filtering
            if motor_brands:
                bike_motor_brand = get_motor_brand({'motor': bike.motor})
                if bike_motor_brand not in [brand.lower() for brand in motor_brands]:
                    continue

            # Convert to dictionary with only needed fields
            bike_dict = {
                'id': str(bike.id) if bike.id else None,
                'firm': str(bike.firm) if bike.firm else None,
                'model': str(bike.model) if bike.model else None,
                'year': str(bike.year) if bike.year else None,
                'price': str(bike.price) if bike.price else None,
                'disc_price': str(bike.disc_price) if bike.disc_price else None,
                'frame': str(bike.frame) if bike.frame else None,
                'motor': str(bike.motor) if bike.motor else None,
                'battery': str(bike.battery) if bike.battery else None,
                'fork': str(bike.fork) if bike.fork else None,
                'rear_shock': str(bike.rear_shock) if bike.rear_shock else None,
                'image_url': str(bike.image_url) if bike.image_url else None,
                'product_url': str(bike.product_url) if bike.product_url else None,
                'wh': str(bike.wh) if bike.wh else None,
                'fork_length': str(bike.fork_length) if bike.fork_length else None,
                'sub_category': str(bike.sub_category) if bike.sub_category else None,
            }
            # Clean the bike data to ensure it's safe for JSON serialization
            cleaned_bike_dict = clean_bike_data_for_json(bike_dict)
            filtered_bikes.append(cleaned_bike_dict)

        return jsonify(filtered_bikes)
    finally:
        db_session.close()


@app.route('/api/bike/<path:bike_id>')
def get_bike_details(bike_id):
    """Get bike details by ID for AJAX requests"""
    try:
        db_session = get_session()
        
        # Find the bike with the exact ID
        bike = db_session.query(Bike).filter_by(id=bike_id).first()
        
        if not bike:
            return jsonify({'error': 'Bike not found'}), 404
        
        # Convert bike to dictionary with only needed fields
        bike_dict = {
            'id': str(bike.id) if bike.id else None,
            'firm': str(bike.firm) if bike.firm else None,
            'model': str(bike.model) if bike.model else None,
            'year': str(bike.year) if bike.year else None,
            'price': str(bike.price) if bike.price else None,
            'disc_price': str(bike.disc_price) if bike.disc_price else None,
            'frame': str(bike.frame) if bike.frame else None,
            'motor': str(bike.motor) if bike.motor else None,
            'battery': str(bike.battery) if bike.battery else None,
            'fork': str(bike.fork) if bike.fork else None,
            'rear_shock': str(bike.rear_shock) if bike.rear_shock else None,
            'image_url': str(bike.image_url) if bike.image_url else None,
            'product_url': str(bike.product_url) if bike.product_url else None,
            'wh': str(bike.wh) if bike.wh else None,
            'fork_length': str(bike.fork_length) if bike.fork_length else None,
            'sub_category': str(bike.sub_category) if bike.sub_category else None,
        }
        
        # Clean the bike data to ensure it's safe for JSON serialization
        cleaned_bike_dict = clean_bike_data_for_json(bike_dict)
        
        return jsonify(cleaned_bike_dict)
        
    except Exception as e:
        print(f"Error getting bike details: {e}")
        return jsonify({'error': 'Server error'}), 500
    finally:
        db_session.close()


@app.route('/api/compare_list')
def api_compare_list():
    return jsonify({'compare_list': session.get('compare_list', [])})

def get_compare_list():
    try:
        return session.get('compare_list', [])
    except Exception as e:
        print(f"Error getting compare list from session: {e}")
        return []

def save_compare_list(compare_list):
    try:
        session['compare_list'] = compare_list
        session.modified = True  # Ensure session is marked as modified
    except Exception as e:
        print(f"Error saving compare list to session: {e}")


@app.route('/add_to_compare', methods=['POST'])
def add_to_compare():
    try:
        # Get bike_id from request data instead of URL path
        bike_id = request.json.get('bike_id') if request.is_json else request.form.get('bike_id')
        
        # Check if bike_id is valid
        if not bike_id or bike_id.strip() == '':
            return jsonify({'success': False, 'error': 'Invalid bike ID'}), 400
        
        # Store the bike_id in its original form (no encoding needed since we're using JSON body)
        normalized_bike_id = bike_id
        
        print(f"Adding bike to compare - Bike ID: {bike_id}")
        
        compare_list = get_compare_list()
        if normalized_bike_id not in compare_list:
            if len(compare_list) < 4:
                compare_list.append(normalized_bike_id)
                save_compare_list(compare_list)

                # ✅ Increment popularity count in database
                try:
                    from scripts.migrate_compare_counts import update_compare_count
                    update_compare_count(normalized_bike_id)
                    print(f"Updated compare count for bike {normalized_bike_id}")
                except Exception as e:
                    print("Error updating compare counts:", e)

                return jsonify({'success': True, 'compare_list': compare_list})
            else:
                return jsonify({'success': False, 'error': 'You can compare up to 4 bikes only.'}), 400
        return jsonify({'success': True, 'compare_list': compare_list})
    except Exception as e:
        print(f"Error in add_to_compare: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500


@app.route('/remove_from_compare', methods=['POST'])
def remove_from_compare():
    try:
        # Get bike_id from request data instead of URL path
        bike_id = request.json.get('bike_id') if request.is_json else request.form.get('bike_id')
        
        # Check if bike_id is valid
        if not bike_id or bike_id.strip() == '':
            return jsonify({'success': False, 'error': 'Invalid bike ID'}), 400
        
        # Store the bike_id in its original form (no encoding needed since we're using JSON body)
        normalized_bike_id = bike_id
        
        print(f"Removing bike from compare - Bike ID: {bike_id}")
        
        compare_list = get_compare_list()
        if normalized_bike_id in compare_list:
            compare_list.remove(normalized_bike_id)
            save_compare_list(compare_list)
        return jsonify({'success': True, 'compare_list': compare_list})
    except Exception as e:
        print(f"Error in remove_from_compare: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/compare_bikes')
def compare_bikes():
    compare_list = get_compare_list()
    all_bikes = load_all_bikes()
    
    # Find bikes that are in the compare list (using original bike IDs)
    bikes_to_compare = []
    for bike in all_bikes:
        bike_id = bike.get('id')
        if bike_id and bike_id in compare_list:
            bikes_to_compare.append(bike)

    # Key fields to always show
    always_show = ["model", "price", "year", "motor", "battery"]

    # Disc_price: show if at least one bike has it non-empty
    show_disc_price = any(
        bike.get("disc_price") not in [None, '', 'N/A', '#N/A']
        for bike in bikes_to_compare
    )
    if show_disc_price:
        always_show.append("disc_price")

    # Get all unique fields from all bikes
    all_fields = set()
    for bike in bikes_to_compare:
        all_fields.update(bike.keys())

    # Remove fields you don't want to show
    exclude_fields = {'id', 'slug', 'image_url', 'product_url'}
    candidate_fields = [f for f in all_fields if f not in exclude_fields and f not in always_show]

    # Only keep fields that are present and non-empty in ALL bikes
    fields_to_show = []
    for field in candidate_fields:
        if all(
            field in bike and bike[field] not in [None, '', 'N/A', '#N/A']
            for bike in bikes_to_compare
        ):
            fields_to_show.append(field)

    # Final order: always_show first, then the rest (sorted)
    fields_to_show = always_show + sorted(fields_to_show)

    return render_template(
        'compare_bikes.html',
        bikes=bikes_to_compare,
        fields_to_show=fields_to_show,
        # ...other context...
    )

@app.route('/comparison/<path:slug>')
def view_comparison(slug):
    """View a specific comparison by slug"""
    db_session = get_session()

    try:
        # Check if slug is a number (old ID format)
        if slug.isdigit():
            comparison = db_session.query(Comparison).filter_by(id=int(slug)).first()
        else:
            # New slug format
            comparison = db_session.query(Comparison).filter_by(slug=slug).first()

        if not comparison:
            abort(404)

        # Get bike IDs and load bike details
        bike_ids = comparison.get_bike_ids()
        all_bikes = load_all_bikes()
        bikes_to_compare = [bike for bike in all_bikes if bike.get('id') in bike_ids]

        # Get comparison data
        comparison_data = comparison.get_comparison_data()

        # Create a shareable URL for this comparison (prefer slug over ID)
        if comparison.slug:
            share_url = request.host_url.rstrip('/') + url_for('view_comparison', slug=comparison.slug)
        else:
            share_url = request.host_url.rstrip('/') + url_for('view_comparison', comparison_id=comparison.id)

        return render_template('shared_comparison.html',
                             comparison=comparison,
                             bikes=bikes_to_compare,
                             comparison_data=comparison_data,
                             share_url=share_url)

    except Exception as e:
        print(f"Error viewing comparison {slug}: {e}")
        abort(500)
    finally:
        db_session.close()

@app.route('/clear_compare', methods=['POST'])
def clear_compare():
    session['compare_list'] = []
    return jsonify({'success': True})


@app.route('/api/compare_ai_from_session', methods=['GET'])
def compare_ai_from_session():
    try:
        # Check if OpenAI API key is set
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return jsonify({"error": "OpenAI API key not configured", "details": "OPENAI_API_KEY environment variable is missing"}), 500
        
        compare_list = get_compare_list()
        
        if len(compare_list) < 2:
            return jsonify({"error": "צריך לבחור לפחות שני דגמים להשוואה."}), 400

        all_bikes = load_all_bikes()
        bikes_to_compare = [bike for bike in all_bikes if bike.get('id') in compare_list]
        
        if len(bikes_to_compare) < 2:
            return jsonify({"error": "לא נמצאו מספיק דגמים להשוואה. נסה לבחור דגמים אחרים."}), 400
        
        prompt = create_ai_prompt(bikes_to_compare)
    except Exception as e:
        return jsonify({"error": "שגיאה בטעינת נתוני האופניים", "details": str(e)}), 500

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Act as a top-tier e-MTB sales and product expert based in Israel who has deep knowledge "
                        "of the local market, parts specs, brands, riding styles, and value-for-money strategies. "
                        "Use your understanding of online reviews (BikeRadar, Pinkbike, Reddit, etc.) to enrich your recommendations. "
                        "Output valid JSON only. No Markdown. No free text. Keys must be in English. Text must be fluent, helpful, and natural in Hebrew."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4,
        )

        raw_text = response.choices[0].message.content.strip()

        # Remove wrapping ```json ... ```
        if raw_text.startswith("```json"):
            raw_text = raw_text[len("```json"):].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[len("```"):].strip()

        if raw_text.endswith("```"):
            raw_text = raw_text[:-3].strip()

        # Parse JSON
        try:
            data = json.loads(raw_text)

            # ✅ Save comparison to database
            db_session = get_session()
            try:
                comparison = Comparison()
                comparison.set_bike_ids(compare_list)
                comparison.set_comparison_data(data)

                # Generate SEO-friendly slug using bike data from database
                slug = comparison.generate_slug(compare_list, db_session)
                comparison.slug = slug

                db_session.add(comparison)
                db_session.commit()

                # Create response data after successful save
                response_data = {
                    "comparison_id": comparison.id,
                    "share_url": request.host_url.rstrip('/') + url_for('view_comparison', slug=comparison.slug),
                    "data": data
                }

            except Exception as e:
                db_session.rollback()
                # Return error response
                return jsonify({"error": "שגיאה בשמירת ההשוואה", "details": str(e)}), 500
            finally:
                db_session.close()

            return jsonify(response_data)
        except json.JSONDecodeError as e:
            return jsonify({
                "error": "ה-AI לא החזיר תשובת JSON תקינה.",
                "raw": raw_text
            }), 500


    except Exception as e:
        return jsonify({"error": "שגיאה פנימית. נסה שוב מאוחר יותר.", "details": str(e)}), 500


def create_ai_prompt(bikes):
    excluded_fields = {"id", "slug", "Image URL", "Product URL"}

    all_fields = set()
    for bike in bikes:
        all_fields.update(bike.keys())
    important_fields = sorted(all_fields - excluded_fields)

    simplified_bike_data = []
    for bike in bikes:
        # Use lowercase field names to match the actual bike data structure
        clean_bike = {"name": bike.get("model", "דגם לא ידוע")}
        for field in important_fields:
            clean_bike[field] = bike.get(field, "לא ידוע")
        simplified_bike_data.append(clean_bike)

    bikes_json = {"bikes": simplified_bike_data}

    prompt = (
        "🧠 אתה מומחה במכירת והשוואת אופני הרים חשמליים (e-MTB) בישראל.\n"
        "קיבלת מידע על מספר דגמים.\n"
        "עליך לבצע השוואה מעמיקה ביניהם, לפי המבנה הבא בלבד:\n\n"
        "{\n"
        '  "intro": "היי! איזה כיף שאתה משווה בין הדגמים – הנה ההתרשמות האישית שלי בתור אחד שחי אופני הרים חשמליים כבר שנים:",\n'
        '  "recommendation": "הסבר איזה דגם הכי משתלם ומדוע. התייחס למפרט, למחיר, לשם המותג, לתחזוקה ולתגובות רוכבים אם אתה מכיר. אם קראת עליו באתרי סקירה או פורומים, ציין זאת והבא טיעונים מחזקים מהמקורות (למשל Pinkbike, BikeRadar, Reddit ועוד).",\n'
        '  "bikes": [\n'
        '    {\n'
        '      "name": "שם הדגם",\n'
        '      "pros": ["תציין יתרונות אמיתיים שקשורים לרכיבה, מחיר, חלקים, משקל, נוחות, אמינות, תמיכה של החנות וכו׳"],\n'
        '      "cons": ["תציין חסרונות אמיתיים – מפרט נחות, מחיר גבוה מדי, משקל, חלקים בסיסיים, מותג פחות ידוע וכו׳"],\n'
        '      "best_for": "מיהו הרוכב שהאופניים האלה הכי מתאימים לו ולמה. לא להשתמש במונחים עמומים כמו "מקצוענים". להעדיף תיאור סגנון רכיבה, שימוש, מיקום בארץ, תקציב או תנאי שטח."\n'
        '    }, ...\n'
        '  ],\n'
        '  "expert_tip": "טיפ של אלופים: אל תבחר רק לפי מספרים. תחשוב גם איפה אתה רוכב, כמה אתה שוקל, וכמה קל יהיה לתחזק את האופניים בעתיד."\n'
        "}\n\n"
        "❗ אל תשתמש ב-Markdown או טקסט חופשי. החזר JSON בלבד.\n"
        "השתמש רק במפתחות באנגלית וערכים בטקסט טבעי בעברית.\n"
        "נסה להתבסס גם על מידע קיים מהאינטרנט שברשותך, כולל אתרי סקירות כמו Pinkbike, emtb-test.com, BikeRadar, Reddit פורומים של רוכבים וכו׳. אם קיימים יתרונות או חסרונות שידועים מהסקירות האלו, כלל אותם בהסברים שלך.\n\n"
        "📦 להלן נתוני האופניים במבנה JSON תחת מפתח 'bikes':\n\n"
    )

    prompt += json.dumps(bikes_json, ensure_ascii=False, indent=2)
    prompt += (
        "\n\nבחר את התכונות החשובות להשוואה והשווה ביניהן.\n"
        "המבנה חייב להיות JSON תקני לפי הפורמט שהוגדר למעלה בלבד."
    )

    return prompt


# --- NEW: WEBHOOK ENDPOINT ---
# This route will be triggered by GitHub pushes to automatically pull and reload
def clear_bike_cache():
    """Clear bike-related cache when data is updated"""
    cache.delete_memoized(load_all_bikes)
    cache.delete_memoized(get_all_firms)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # 1. Verify the request is a JSON payload
    if not request.is_json:
        return jsonify({"error": "Invalid content type"}), 400
    
    # 2. Get the request body
    payload = request.get_json()
    
    # 3. Verify the webhook signature (if secret is set)
    if GITHUB_WEBHOOK_SECRET:
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            return jsonify({"error": "Missing signature"}), 401
        
        # Verify the signature
        expected_signature = 'sha256=' + hmac.new(
            GITHUB_WEBHOOK_SECRET.encode('utf-8'),
            request.get_data(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return jsonify({"error": "Invalid signature"}), 401
    
    # 4. Check if this is a push event to the main branch
    if payload.get('ref') == 'refs/heads/main':
        try:
            # 5. Pull the latest changes
            result = subprocess.run(['git', 'pull'], 
                                  capture_output=True, 
                                  text=True, 
                                  cwd=os.path.dirname(os.path.abspath(__file__)))
            
            if result.returncode == 0:
                # Clear cache after successful update
                clear_bike_cache()
                return jsonify({"message": "Successfully updated", "output": result.stdout}), 200
            else:
                return jsonify({"error": "Failed to pull changes", "output": result.stderr}), 500
                
        except Exception as e:
            return jsonify({"error": f"Error during update: {str(e)}"}), 500
    
    return jsonify({"message": "Webhook received but no action taken"}), 200
# --- END NEW WEBHOOK ENDPOINT ---


if __name__ == "__main__":
    app.run(debug=True)