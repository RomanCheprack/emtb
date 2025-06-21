from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from openai import OpenAI
import json
import os


app = Flask(__name__)
load_dotenv()  # Load .env variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app.secret_key = '123456789'  # Set a secure secret key!

def load_all_bikes():
    with open("data/mazman.json", "r", encoding="utf-8") as f:
        bikes1 = json.load(f)
    with open("data/recycles.json", "r", encoding="utf-8") as f:
        bikes2 = json.load(f)
    with open("data/ctc.json", "r", encoding="utf-8") as f:
        bikes3 = json.load(f)
    
    all_bikes = bikes1 + bikes2 + bikes3

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
    return int(''.join(filter(str.isdigit, str(price_str))))


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
    top_ids = [bike_id for bike_id, _ in top_bike_ids]
    top_bikes = [bike for bike in all_bikes if str(bike.get("slug") or bike.get("Model")) in top_ids]

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
    min_price = request.args.get("min_price", type=int)
    max_price = request.args.get("max_price", type=int)
    years = request.args.getlist("year", type=int)
    firms = request.args.getlist("firm")
    min_battery = request.args.get("min_battery", type=int)
    max_battery = request.args.get("max_battery", type=int)

    filtered_bikes = []
    for bike in all_bikes:
        price = parse_price(bike.get("Price"))
        bike_year = bike.get("Year")
        battery = parse_battery(bike.get("Battery"))

        try:
            bike_year = int(bike_year)
        except (ValueError, TypeError):
            bike_year = None

        if min_price is not None and min_price > 0:
            if price is not None and price < min_price:
                continue
        if max_price is not None and max_price < 100000:
            if price is not None and price > max_price:
                continue
        if years:
            if bike_year is None or bike_year not in years:
                continue
        if min_battery is not None and min_battery > 200:
            if battery is not None and battery < min_battery:
                continue
        if max_battery is not None and max_battery < 1000:
            if battery is not None and battery > max_battery:
                continue
        if firms:
            if bike.get("Firm") not in firms:
                continue

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
    return render_template('compare_bikes.html', bikes=bikes_to_compare)

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
    bikes_to_compare = [bike for bike in all_bikes if str(bike.get('slug') or bike.get('Model')) in compare_list]

    prompt = create_ai_prompt(bikes_to_compare)

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Act as a e-mtb sales agent and professional e-mtb expert located in israel"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
        )
        text = response.choices[0].message.content

        return jsonify({"comparison_text": text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def create_ai_prompt(bikes):
    prompt = (
        "Your task is to compare 2–4 high-end e-MTBs and help the buyer choose the best one with the most added value.\n\n"
        "You are provided with full technical specs for each bike (directly from a trusted internal database).\n"
        "Based on that data — and your deep understanding of current industry knowledge, review trends, and trail feedback — you will:\n\n"
        "1. Analyze their components, suspension, motor/battery systems, geometry, weight, and customizability.\n"
        "2. Use simulated external review knowledge (from YouTube, Pinkbike, BikeRadar, Reddit, forums) to add credibility.\n"
        "3. Write as if you're selling the better option — but explain why clearly, with numbers, confidence, and value.\n"
        "4. Only later, show a structured in a designed beautiful table side-by-side comparison.\n\n"
        "✨ Write in **natural Hebrew**, in the tone of a trusted sales advisor — sharp, funny, clear, and very professional.\n"
        "Avoid heavy jargon. Use confident, rider-focused language (range, weight, real-world feel, fun, power, confidence, tech). This should read like an expert script ready for voiceover.\n\n"
        "Start with an engaging introduction (e.g. 'היי! איזה כיף שאתה פה…'). Present the winner bike like a pro salesperson. Then summarize the facts.\n\n"
        "Here are the bikes:\n\n"
    )

    for i, bike in enumerate(bikes):
        prompt += f"אופניים {i + 1}:\n"
        for key, value in bike.items():
            prompt += f"{key}: {value}\n"
        prompt += "\n"

    prompt += (
        "עכשיו, כתוב השוואה מלאה, מקצועית אך בגובה העיניים, עם המלצה חד משמעית על הדגם שנותן הכי הרבה תמורה לרוכב הישראלי."
    )

    return prompt




if __name__ == "__main__":
    app.run(debug=True)