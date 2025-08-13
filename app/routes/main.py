from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.extensions import csrf
from app.utils.security import sanitize_html_content
import json
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from app.models.bike import get_session, Bike, Comparison, CompareCount
from app.services.bike_service import load_all_bikes, get_all_firms

bp = Blueprint('main', __name__)

@bp.route("/")
def home():
    all_bikes = load_all_bikes()
    firms = get_all_firms()

    # Load compare counts from database
    db_session = get_session()
    try:
        # Get total number of comparisons
        total_comparisons = db_session.query(Comparison).count()
        
        # Get top 10 most compared bikes that actually exist in the bikes table
        top_compare_counts = db_session.query(CompareCount).join(Bike).order_by(CompareCount.count.desc()).limit(10).all()
        
        # Convert to the same format as all_bikes
        top_bikes = []
        for cc in top_compare_counts:
            bike = cc.bike
            
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
            top_bikes.append(bike_dict)

        # Add fallback bikes if we don't have enough
        if len(top_bikes) < 10:
            remaining_needed = 10 - len(top_bikes)
            fallback_bikes = all_bikes[:remaining_needed]
            top_bikes.extend(fallback_bikes)

    except Exception as e:
        print(f"Error loading compare counts: {e}")
        import traceback
        traceback.print_exc()
        top_bikes = all_bikes[:10]  # Fallback to first 10 bikes
        total_comparisons = 0
    finally:
        db_session.close()

    return render_template("home.html", bikes=all_bikes, firms=firms, top_bikes=top_bikes, total_comparisons=total_comparisons)

@bp.route("/contact", methods=["POST"])
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

@bp.route('/sitemap.xml', methods=['GET'])
def sitemap():
    from flask import Response, url_for
    pages = []
    now = datetime.now()
    ten_days_ago = (datetime.now() - timedelta(days=10)).date().isoformat()

    # Static pages
    pages.append({
        'loc': url_for('main.home', _external=True),
        'lastmod': ten_days_ago,
        'priority': '1.0'
    })
    pages.append({
        'loc': url_for('bikes.bikes', _external=True),
        'lastmod': ten_days_ago,
        'priority': '0.8'
    })
    pages.append({
        'loc': url_for('blog.blog_list', _external=True),
        'lastmod': ten_days_ago,
        'priority': '0.8'
    })

    # Blog posts
    from app.services.blog_service import load_posts
    blog_posts = load_posts()
    for post in blog_posts:
        pages.append({
            'loc': url_for('blog.blog_post', slug=post['slug'], _external=True),
            'lastmod': post['date'],
            'priority': '0.6'
        })

    # Individual bike pages
    bikes = load_all_bikes()
    for bike in bikes:
        pages.append({
            'loc': url_for('bikes.bikes', bike_id=bike['id'], _external=True),
            'lastmod': ten_days_ago,
            'priority': '0.5'
        })

    # Add persistent comparison pages
    session = get_session()
    try:
        comparisons = session.query(Comparison).all()
        for comparison in comparisons:
            if comparison.slug:
                pages.append({
                    'loc': url_for('compare.view_comparison', slug=comparison.slug, _external=True),
                    'lastmod': comparison.created_at.date().isoformat() if comparison.created_at else ten_days_ago,
                    'priority': '0.7'
                })
    finally:
        session.close()

    # Create XML string
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    return Response(sitemap_xml, mimetype='application/xml')
