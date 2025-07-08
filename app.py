from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, abort, Response
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, timedelta
from email.message import EmailMessage
import json
import os
import smtplib
from scripts.models import init_db, get_session, Bike, Comparison, CompareCount

# --- NEW IMPORTS FOR WEBHOOK ---
import subprocess # To run shell commands like 'git pull'
import hmac # For cryptographic signing and verification (webhook secret)
import hashlib # For hashing (part of cryptographic signing)
# --- END NEW IMPORTS ---

app = Flask(__name__)
load_dotenv(override=True)  # Load .env variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app.secret_key = 'app_secret_key'  # Set a secure secret key!

# Initialize database
init_db()

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
        from scripts.models import Comparison
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

def load_all_bikes():
    """Load all bikes from the database"""
    session = get_session()
    try:
        bikes = session.query(Bike).all()
        # Convert SQLAlchemy objects to dictionaries
        bikes_data = []
        for bike in bikes:
            bike_dict = {
                'id': bike.id,
                'Firm': bike.firm,
                'Model': bike.model,
                'Year': bike.year,
                'Price': bike.price,
                'Disc_price': bike.disc_price,
                'Frame': bike.frame,
                'Motor': bike.motor,
                'Battery': bike.battery,
                'Fork': bike.fork,
                'Rear Shox': bike.rear_shox,
                'Image URL': bike.image_url,
                'Product URL': bike.product_url,

                # Additional fields
                'Stem': bike.stem,
                'Handelbar': bike.handelbar,
                'Front Brake': bike.front_brake,
                'Rear Brake': bike.rear_brake,
                'Shifter': bike.shifter,
                'Rear Der': bike.rear_der,
                'Cassette': bike.cassette,
                'Chain': bike.chain,
                'Crank Set': bike.crank_set,
                'Front Wheel': bike.front_wheel,
                'Rear Wheel': bike.rear_wheel,
                'Rims': bike.rims,
                'Front Axle': bike.front_axle,
                'Rear Axle': bike.rear_axle,
                'Spokes': bike.spokes,
                'Tubes': bike.tubes,
                'Front Tire': bike.front_tire,
                'Rear Tire': bike.rear_tire,
                'Saddle': bike.saddle,
                'Seat Post': bike.seat_post,
                'Clamp': bike.clamp,
                'Charger': bike.charger,
                'Wheel Size': bike.wheel_size,
                'Headset': bike.headset,
                'Brake Lever': bike.brake_lever,
                'Screen': bike.screen,
                'Extras': bike.extras,
                'Pedals': bike.pedals,
                'B.B': bike.bb,
                'מספר הילוכים:': bike.gear_count,
                'Weight': bike.weight,
                'Size': bike.size,
                'Hub': bike.hub,
                'Brakes': bike.brakes,
                'Tires': bike.tires,
            }
            bikes_data.append(bike_dict)
        return bikes_data
    finally:
        session.close()

def parse_price(price_str):
    if not price_str:
        return None
    digits_only = ''.join(filter(str.isdigit, str(price_str)))
    return int(digits_only) if digits_only else None


@app.route("/")
def home():
    all_bikes = load_all_bikes()
    firms = sorted({bike.get("Firm", "") for bike in all_bikes if bike.get("Firm")})

    # ✅ Load compare counts from database
    session = get_session()
    try:
        top_compare_counts = session.query(CompareCount).order_by(CompareCount.count.desc()).limit(3).all()
        top_ids = [cc.bike_id for cc in top_compare_counts]
        top_bikes = [bike for bike in all_bikes if bike.get("id") in top_ids]
    except Exception as e:
        print(f"Error loading compare counts: {e}")
        top_bikes = []
    finally:
        session.close()

    return render_template("home.html", bikes=all_bikes, firms=firms, top_bikes=top_bikes)


@app.route("/bikes")
def bikes():
    all_bikes = load_all_bikes()
    firms = sorted({bike.get("Firm", "") for bike in all_bikes if bike.get("Firm")})
    return render_template("bikes.html", bikes=all_bikes, firms=firms)
def parse_battery(battery_str):
    if not battery_str:
        return None
    # Extract digits from the string (e.g., "625Wh" -> 625)
    digits = ''.join(filter(str.isdigit, battery_str))
    return int(digits) if digits else None

def get_frame_material(bike):
    frame_val = bike.get('Frame', '')
    model_val = bike.get('Model', '')
    combined = f"{frame_val} {model_val}".lower()
    if 'carbon' in combined:
        return 'carbon'
    return 'aluminium'

def get_motor_brand(bike):
    motor_val = bike.get('Motor', '')
    for brand in MOTOR_BRANDS:
        if brand.lower() in motor_val.lower():
            return brand.lower()
    return 'other'

@app.route("/api/filter_bikes")
def filter_bikes():
    all_bikes = load_all_bikes()
    query = request.args.get("q", "").strip().lower()
    min_price = request.args.get("min_price", type=int)
    max_price = request.args.get("max_price", type=int)
    years = request.args.getlist("year", type=int)
    firms = request.args.getlist("firm")
    min_battery = request.args.get("min_battery", type=int)
    max_battery = request.args.get("max_battery", type=int)
    frame_material = request.args.get("frame_material", type=str)  # 'carbon' or 'aluminium'
    motor_brands = request.args.getlist("motor_brand", type=str)

    filtered_bikes = []

    for bike in all_bikes:
        # 🔎 Keyword search across all fields
        if query:
            if not any(query in str(value).lower() for value in bike.values() if value):
                continue

        # 💰 Price
        price_str = bike.get("Disc_price") or bike.get("Price")
        price = parse_price(price_str)

        if min_price is not None and min_price > 0:
            if price is not None and price < min_price:
                continue
        if max_price is not None and max_price < 100000:
            if price is not None and price > max_price:
                continue

        # 🔋 Battery
        battery = parse_battery(bike.get("Battery"))
        if min_battery is not None and min_battery > 200:
            if battery is not None and battery < min_battery:
                continue
        if max_battery is not None and max_battery < 1000:
            if battery is not None and battery > max_battery:
                continue

        # 📅 Year
        bike_year = bike.get("Year")
        try:
            bike_year = int(bike_year)
        except (ValueError, TypeError):
            bike_year = None
        if years:
            if bike_year is None or bike_year not in years:
                continue

        # 🏷️ Firm
        if firms:
            if bike.get("Firm") not in firms:
                continue

        # 🆕 Frame Material
        if frame_material:
            if get_frame_material(bike) != frame_material.lower():
                continue

        # 🆕 Motor Brand
        if motor_brands:
            if get_motor_brand(bike) not in [brand.lower() for brand in motor_brands]:
                continue

        # ✅ Passed all filters
        filtered_bikes.append(bike)

    return jsonify(filtered_bikes)


@app.route('/api/compare_list')
def api_compare_list():
    return jsonify({'compare_list': session.get('compare_list', [])})

def get_compare_list():
    return session.get('compare_list', [])

def save_compare_list(compare_list):
    session['compare_list'] = compare_list


@app.route('/add_to_compare/<bike_id>', methods=['POST'])
def add_to_compare(bike_id):
    compare_list = get_compare_list()
    if bike_id not in compare_list:
        if len(compare_list) < 4:
            compare_list.append(bike_id)
            save_compare_list(compare_list)

            # ✅ Increment popularity count in database
            try:
                from migrate_compare_counts import update_compare_count
                update_compare_count(bike_id)
                print(f"Updated compare count for bike {bike_id}")
            except Exception as e:
                print("Error updating compare counts:", e)

            return jsonify({'success': True, 'compare_list': compare_list})
        else:
            return jsonify({'success': False, 'error': 'You can compare up to 4 bikes only.'}), 400
    return jsonify({'success': True, 'compare_list': compare_list})


@app.route('/remove_from_compare/<bike_id>', methods=['POST'])
def remove_from_compare(bike_id):
    compare_list = get_compare_list()
    if bike_id in compare_list:
        compare_list.remove(bike_id)
        save_compare_list(compare_list)
    return jsonify({'success': True, 'compare_list': compare_list})

@app.route('/compare_bikes')
def compare_bikes():
    compare_list = get_compare_list()
    all_bikes = load_all_bikes()
    bikes_to_compare = [bike for bike in all_bikes if bike.get('id') in compare_list]

    # Key fields to always show
    always_show = ["Model", "Price", "Year", "Motor", "Battery"]

    # Disc_price: show if at least one bike has it non-empty
    show_disc_price = any(
        bike.get("Disc_price") not in [None, '', 'N/A', '#N/A']
        for bike in bikes_to_compare
    )
    if show_disc_price:
        always_show.append("Disc_price")

    # Get all unique fields from all bikes
    all_fields = set()
    for bike in bikes_to_compare:
        all_fields.update(bike.keys())

    # Remove fields you don't want to show
    exclude_fields = {'id', 'slug', 'Image URL', 'Product URL'}
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
    session = get_session()

    try:
        # Check if slug is a number (old ID format)
        if slug.isdigit():
            comparison = session.query(Comparison).filter_by(id=int(slug)).first()
        else:
            # New slug format
            comparison = session.query(Comparison).filter_by(slug=slug).first()

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
        session.close()

@app.route('/clear_compare', methods=['POST'])
def clear_compare():
    session['compare_list'] = []
    return jsonify({'success': True})


@app.route('/api/compare_ai_from_session', methods=['GET'])
def compare_ai_from_session():
    compare_list = get_compare_list()
    if len(compare_list) < 2:
        return jsonify({"error": "צריך לבחור לפחות שני דגמים להשוואה."}), 400

    all_bikes = load_all_bikes()
    bikes_to_compare = [bike for bike in all_bikes if bike.get('id') in compare_list]
    prompt = create_ai_prompt(bikes_to_compare)

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
        #print("✅ raw_text before cleaning:")
        #print(raw_text)

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
            print("✅ JSON parsed successfully")

            # ✅ Save comparison to database
            session = get_session()
            try:
                comparison = Comparison()
                comparison.set_bike_ids(compare_list)
                comparison.set_comparison_data(data)

                # Generate SEO-friendly slug using bike data from database
                slug = comparison.generate_slug(compare_list, session)
                comparison.slug = slug

                session.add(comparison)
                session.commit()
                print(f"✅ Saved comparison to database with ID: {comparison.id}, Slug: {slug}")

                # Create response data after successful save
                response_data = {
                    "comparison_id": comparison.id,
                    "share_url": request.host_url.rstrip('/') + url_for('view_comparison', slug=comparison.slug),
                    "data": data
                }

            except Exception as e:
                print(f"❌ Error saving to database: {e}")
                session.rollback()
                # Return error response
                return jsonify({"error": "שגיאה בשמירת ההשוואה", "details": str(e)}), 500
            finally:
                session.close()

            return jsonify(response_data)
        except json.JSONDecodeError as e:
            print("❌ JSON decode error:", e)
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
        clean_bike = {"name": bike.get("Model", "דגם לא ידוע")}
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
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # 1. Verify the request is a JSON payload
    if request.headers.get('Content-Type') != 'application/json':
        abort(400, "Invalid Content Type")

    # 2. Verify the GitHub signature (for security)
    # This checks if the request genuinely came from GitHub and hasn't been tampered with.
    if not GITHUB_WEBHOOK_SECRET:
        # If no secret is configured, this webhook is insecure!
        print("Warning: GITHUB_WEBHOOK_SECRET not configured. Skipping signature check.")
    else:
        # Ensure the X-Hub-Signature header is present
        if 'X-Hub-Signature' not in request.headers:
            print("Webhook: Missing X-Hub-Signature header. Request rejected.")
            abort(403, "Missing X-Hub-Signature")

        # Reconstruct the payload to verify signature
        # request.data contains the raw request body
        payload_body = request.data
        
        # Calculate the expected signature
        signature = 'sha1=' + hmac.new(
            GITHUB_WEBHOOK_SECRET.encode('utf-8'),
            payload_body,
            hashlib.sha1
        ).hexdigest()

        # Compare the calculated signature with the signature from the header
        if not hmac.compare_digest(signature, request.headers['X-Hub-Signature']):
            print("Webhook signature mismatch! Request rejected.")
            abort(403, "Invalid X-Hub-Signature")
        print("Webhook signature verified successfully.")

    data = request.json # Safely parse JSON after verification
    # Log the Git ref that triggered the webhook (e.g., 'refs/heads/main')
    print(f"Received webhook from GitHub for ref: {data.get('ref', 'N/A')}")
    print(f"Commit message: {data.get('head_commit', {}).get('message', 'N/A')}")


    # --- Git Pull Logic ---
    try:
        # Change directory to your project's root first
        # This is crucial so 'git pull' runs in the correct location.
        project_dir = '/home/romanahi8689/emtb' 
        os.chdir(project_dir) 
        
        # Execute 'git pull origin main' to fetch and merge latest changes
        # 'capture_output=True' captures stdout/stderr, 'text=True' decodes to string,
        # 'check=True' raises CalledProcessError on non-zero exit codes.
        result = subprocess.run(['git', 'pull', 'origin', 'main'], capture_output=True, text=True, check=True)
        print(f"Git pull output (stdout):\n{result.stdout}")
        if result.stderr:
            print(f"Git pull output (stderr):\n{result.stderr}")

    except subprocess.CalledProcessError as e:
        print(f"Error during git pull (return code {e.returncode}): {e.stderr}")
        return f"Git pull failed: {e.stderr}", 500
    except Exception as e:
        print(f"Unexpected error during git pull: {e}")
        return "Internal server error during git pull", 500

    # --- Reload the web application on PythonAnywhere ---
    # Touching the WSGI file tells PythonAnywhere to restart your web application.
    try:
        # You MUST replace this with your exact WSGI file path from your PythonAnywhere 'Web' tab.
        # It's usually found under 'WSGI configuration file'.
        # Example: '/var/www/romanahi8689_www_rideal_co_il_wsgi.py'
        wsgi_file_path = '/var/www/www_rideal_co_il_wsgi.py' # <--- REPLACE THIS PATH!
        
        os.system(f'touch {wsgi_file_path}')
        print(f"Touched {wsgi_file_path} to reload web app.")
    except Exception as e:
        print(f"Error reloading web app: {e}")
        # Log the error, but we still return 200 to GitHub as the pull might have succeeded.
    
    return "Webhook processed and app reloaded successfully", 200
# --- END NEW WEBHOOK ENDPOINT ---


if __name__ == "__main__":
    app.run(debug=True)