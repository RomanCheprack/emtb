
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, abort, Response
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, timedelta
from email.message import EmailMessage
import json
import os
import smtplib

app = Flask(__name__)
load_dotenv()  # Load .env variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app.secret_key = 'app_secret_key'  # Set a secure secret key!


@app.route('/sitemap.xml', methods=['GET'])
def sitemap():
    pages = []
    now = datetime.now()
    ten_days_ago = (datetime.now() - timedelta(days=10)).date().isoformat()

    # Static pages
    pages.append({
        'loc': url_for('home', _external=True),
        'lastmod': ten_days_ago
    })
    pages.append({
        'loc': url_for('compare_bikes', _external=True),
        'lastmod': ten_days_ago
    })

    blog_posts = load_posts()

    for post in blog_posts:
        pages.append({
            'loc': url_for('blog_post', slug=post['slug'], _external=True),
            'lastmod': post['date']
        })
    # Dynamic product pages (example if you store bikes in a DB or list)
    bikes = load_all_bikes()  # Replace with real DB call or logic
    for bike in bikes:
        pages.append({
            'loc': url_for('bikes', bike_id=bike['id'], _external=True),
            'lastmod': bike.get('last_updated', ten_days_ago)
        })

    # Create XML string
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    return Response(sitemap_xml, mimetype='application/xml')

@app.route('/google123abc456.html')
def google_verification():
    return send_from_directory(os.path.dirname(__file__), 'google123abc456.html')

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
            smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
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
    with open("data/mazman.json", "r", encoding="utf-8") as f:
        bikes1 = json.load(f)
    with open("data/recycles.json", "r", encoding="utf-8") as f:
        bikes2 = json.load(f)
    with open("data/ctc.json", "r", encoding="utf-8") as f:
        bikes3 = json.load(f)
    with open("data/pedalim.json", "r", encoding="utf-8") as f:
        bikes4 = json.load(f)
    with open("data/whistle.json", "r", encoding="utf-8") as f:
        bikes5 = json.load(f)
    with open("data/ktm.json", "r", encoding="utf-8") as f:
        bikes6 = json.load(f)
    
    all_bikes = bikes1 + bikes2 + bikes3 + bikes4 + bikes5 + bikes6

    for bike in all_bikes:
        if not bike.get('id'):
            # Create a unique ID from firm-model-year-shop (or product URL)
            firm = bike.get('Firm', '').replace(" ", "-")
            model = bike.get('Model', '').replace(" ", "-")
            year = str(bike.get('Year', ''))
            url_part = bike.get('Product URL', '').split('/')[-1].split('.')[0]
            bike['id'] = f"{firm}_{model}_{year}_{url_part}".lower()

    return all_bikes

def parse_price(price_str):
    if not price_str:
        return None
    digits_only = ''.join(filter(str.isdigit, str(price_str)))
    return int(digits_only) if digits_only else None


@app.route("/")
def home():
    all_bikes = load_all_bikes()
    firms = sorted({bike.get("Firm", "") for bike in all_bikes if bike.get("Firm")})

    # ✅ Load compare counts
    try:
        with open("data/compare_counts.json", "r", encoding="utf-8") as f:
            compare_counts = json.load(f)
    except FileNotFoundError:
        compare_counts = {}

    # ✅ Sort by popularity
    top_bike_ids = sorted(compare_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    print(top_bike_ids)
    top_ids = [bike_id for bike_id, _ in top_bike_ids]
    # Ensure you're matching against the 'id' you generate and store in compare_counts.json
    top_bikes = [bike for bike in all_bikes if bike.get("id") in top_ids]
    
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

            # ✅ Increment popularity count
            try:
                with open("data/compare_counts.json", "r+", encoding="utf-8") as f:
                    counts = json.load(f)
                    counts[bike_id] = counts.get(bike_id, 0) + 1
                    f.seek(0)
                    json.dump(counts, f, ensure_ascii=False, indent=2)
                    f.truncate()
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
    spec_fields = [
        ("Price", "מחיר"),
        ("Motor", "מנוע"),
        ("Battery", "סוללה"),
        ("Frame", "שלדה"),
    ]
    return render_template('compare_bikes.html', bikes=bikes_to_compare, specs=spec_fields)

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
                    "content": "Act as a professional e-MTB sales expert located in Israel. Output valid JSON only. No markdown, no free text, no explanation. Keys must be in English. Text in values must be natural Hebrew with no grammar mistakes."
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
            return jsonify(data)
        except json.JSONDecodeError as e:
            print("❌ JSON decode error:", e)
            return jsonify({
                "error": "ה-AI לא החזיר תשובת JSON תקינה.",
                "raw": raw_text
            }), 500

        
    except Exception as e:
        return jsonify({"error": "שגיאה פנימית. נסה שוב מאוחר יותר.", "details": str(e)}), 500


def create_ai_prompt(bikes):
    # Fields to exclude from AI comparison
    excluded_fields = {"id", "slug", "Image URL", "Product URL"}

    # Collect all unique keys across bikes (excluding irrelevant ones)
    all_fields = set()
    for bike in bikes:
        all_fields.update(bike.keys())
    important_fields = sorted(all_fields - excluded_fields)

    # Normalize bikes into a simplified list
    simplified_bike_data = []
    for bike in bikes:
        clean_bike = {"name": bike.get("Model", "דגם לא ידוע")}
        for field in important_fields:
            clean_bike[field] = bike.get(field, "לא ידוע")
        simplified_bike_data.append(clean_bike)
    #print(simplified_bike_data)

    # Build the prompt
    prompt = (
        "🧠 אתה מומחה במכירת והשוואת אופני הרים חשמליים (e-MTB) בישראל.\n"
        "קיבלת טבלת מידע מובנית על מספר דגמים.\n"
        "בנה השוואה ביניהם לפי מבנה JSON הבא בלבד:\n\n"
        "{\n"
        '  "intro": "פתיח ידידותי בעברית",\n'
        '  "recommendation": "הסבר בהרחבה מהו הדגם המומלץ ולמה אתה ממליץ אליו. התייחס למפרטה חלקים של האופניים, למחיר וההנחות במקה וקיימות, לביקורות ברשת ואונליין וכל מידע נוסף שתוכל להוסיף לרוכש",\n'
        '  "bikes": [\n'
        '    {\n'
        '      "name": "שם הדגם",\n'
        '      "pros": ["יתרון 1", "יתרון 2"],\n'
        '      "cons": ["חיסרון 1", "חיסרון 2"],\n'
        '      "best_for": "סוג הרוכב שהדגם מתאים לו"\n'
        '    }, ...\n'
        '  ],\n'
        '  "expert_tip": "טיפ מעניין או מצחיק בעברית"\n'
        "}\n\n"
        "❗ אל תשתמש ב-Markdown או טקסט חופשי. החזר JSON בלבד.\n"
        "השתמש רק במפתחות באנגלית וערכים בטקסט טבעי בעברית.\n\n"
        "📦 להלן נתוני האופניים:\n\n"
    )

    prompt += json.dumps(simplified_bike_data, ensure_ascii=False, indent=2)
    
    prompt += (
        "\n\nבחר את התכונות החשובות להשוואה והשווה ביניהן.\n"
        "המבנה חייב להיות JSON תקני לפי הפורמט שהוגדר למעלה בלבד."
    )

    return prompt


if __name__ == "__main__":
    app.run(debug=True)
