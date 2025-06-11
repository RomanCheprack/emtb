from flask import Flask, render_template, request, jsonify
import json

app = Flask(__name__)

def load_all_bikes():
    with open("data/mazman.json", "r", encoding="utf-8") as f:
        bikes1 = json.load(f)
    with open("data/recycles.json", "r", encoding="utf-8") as f:
        bikes2 = json.load(f)
    with open("data/ctc.json", "r", encoding="utf-8") as f:
        bikes3 = json.load(f)
    return bikes1 + bikes2 + bikes3

def parse_price(price_str):
    if not price_str:
        return None
    return int(''.join(filter(str.isdigit, str(price_str))))


@app.route("/")
def home():
    all_bikes = load_all_bikes()
    return render_template("home.html", bikes=all_bikes)
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

        filtered_bikes.append(bike)
    return jsonify(filtered_bikes)


@app.route("/brands")
def brands():
    with open("data/mazman.json", "r", encoding="utf-8") as f:
        bikes = json.load(f)
    brands = sorted(set(bike["Firm"] for bike in bikes))
    return render_template("brands.html", brands=brands)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/api/bikes")
def api_bikes():
    with open("data/mazmanjson", "r", encoding="utf-8") as f:
        bikes = json.load(f)
    return jsonify(bikes)

if __name__ == "__main__":
    app.run(debug=True)