from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.extensions import csrf, db
from app.utils.security import sanitize_html_content
import json
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from app.models import Bike, Comparison, CompareCount, BikeListing, Source, AvailabilityLead, ContactLead, StoreRequestLead
from app.services.bike_service import get_all_firms

bp = Blueprint('main', __name__)

@bp.route("/")
def home():
    # Get only necessary data - don't load all bikes!
    firms = get_all_firms()
    
    # Calculate number of unique bike brands
    brand_count = len(firms)
    
    # Get total bike count efficiently without loading all bikes
    total_bikes_count = db.session.query(Bike).count()
    
    # Get total number of sources (stores/importers)
    sources_count = db.session.query(Source).count()

    # Load compare counts from database
    try:
        # Get total number of comparisons
        total_comparisons = db.session.query(Comparison).count()
        
        # Get top 10 most compared bikes that actually exist in the bikes table
        top_compare_counts = db.session.query(CompareCount).join(Bike).options(
            db.joinedload(CompareCount.bike).joinedload(Bike.brand),
            db.joinedload(CompareCount.bike).joinedload(Bike.listings).joinedload(BikeListing.prices),
            db.joinedload(CompareCount.bike).joinedload(Bike.standardized_specs),
            db.joinedload(CompareCount.bike).joinedload(Bike.images)
        ).order_by(CompareCount.count.desc()).limit(10).all()
        
        # Convert to template-compatible format
        top_bikes = []
        for cc in top_compare_counts:
            bike = cc.bike
            bike_dict = bike.to_dict()
            top_bikes.append(bike_dict)

        # Add fallback bikes if we don't have enough - load only what's needed
        if len(top_bikes) < 10:
            remaining_needed = 10 - len(top_bikes)
            fallback_bikes_query = Bike.query.options(
                db.joinedload(Bike.brand),
                db.joinedload(Bike.listings).joinedload(BikeListing.prices),
                db.joinedload(Bike.standardized_specs),
                db.joinedload(Bike.images)
            ).limit(remaining_needed).all()
            
            for bike in fallback_bikes_query:
                top_bikes.append(bike.to_dict())

    except Exception as e:
        print(f"Error loading compare counts: {e}")
        import traceback
        traceback.print_exc()
        # Load only 10 bikes for fallback instead of all bikes
        fallback_bikes_query = Bike.query.options(
            db.joinedload(Bike.brand),
            db.joinedload(Bike.listings).joinedload(BikeListing.prices),
            db.joinedload(Bike.standardized_specs),
            db.joinedload(Bike.images)
        ).limit(10).all()
        
        top_bikes = [bike.to_dict() for bike in fallback_bikes_query]
        total_comparisons = 0

    return render_template("home.html", bikes_count=total_bikes_count, firms=firms, top_bikes=top_bikes, total_comparisons=total_comparisons, brand_count=brand_count, sources_count=sources_count)

@bp.route("/contact", methods=["POST"])
def contact():
    name = request.form["Name"]
    form_type = request.form.get("form_type", "contact")
    
    # Save lead to database
    try:
        if form_type == "test_ride":
            phone = request.form.get("Phone", "")
            model = request.form.get("Model", "")
            lead = ContactLead(
                name=name,
                phone=phone,
                form_type="test_ride",
                model=model
            )
        else:
            email = request.form.get("Email", "")
            message = request.form.get("Message", "")
            lead = ContactLead(
                name=name,
                email=email,
                message=message,
                form_type="contact"
            )
        db.session.add(lead)
        db.session.commit()
    except Exception as e:
        print(f"Error saving contact lead: {e}")
        db.session.rollback()
        # Continue even if database save fails
    
    # Construct the email based on form type
    msg = EmailMessage()
    msg["To"] = "rideal.bikes@gmail.com"
    
    if form_type == "test_ride":
        # Test ride form
        phone = request.form["Phone"]
        model = request.form["Model"]
        
        msg["Subject"] = f"בקשה לנסיעת מבחן מ-{name}"
        msg["From"] = "rideal.bikes@gmail.com"
        msg.set_content(f"בקשה לנסיעת מבחן\n\nשם: {name}\nטלפון: {phone}\nדגם מעניין: {model}")
    else:
        # Regular contact form
        email = request.form["Email"]
        message = request.form["Message"]
        
        msg["Subject"] = f"New Contact from {name}"
        msg["From"] = email
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

@bp.route("/check-availability", methods=["POST"])
def check_availability():
    """Handle availability check form submission"""
    try:
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        city = request.form.get("city", "").strip()
        bike_model = request.form.get("bike_model", "").strip()
        bike_id = request.form.get("bike_id", "").strip()
        preferred_size = request.form.get("preferred_size", "").strip()
        
        # Validate required fields
        if not name or not phone or not city:
            return "שדות חובה חסרים", 400
        
        # Get importer information from bike
        importer_info = ""
        if bike_id:
            try:
                from app.models import Bike, BikeListing, Source
                bike = db.session.query(Bike).filter(Bike.uuid == bike_id).first()
                if bike and bike.listings:
                    # Get all unique importers from the bike's listings
                    importers = set()
                    for listing in bike.listings:
                        if listing.source and listing.source.importer:
                            importers.add(listing.source.importer)
                    if importers:
                        importer_info = ", ".join(sorted(importers))
            except Exception as e:
                print(f"Error fetching importer info: {e}")
                # Continue without importer info if there's an error
        
        # Save lead to database
        try:
            lead = AvailabilityLead(
                name=name,
                phone=phone,
                city=city,
                bike_model=bike_model,
                bike_id=bike_id,
                importer=importer_info,
                preferred_size=preferred_size if preferred_size else None
            )
            db.session.add(lead)
            db.session.commit()
        except Exception as e:
            print(f"Error saving availability lead: {e}")
            db.session.rollback()
            # Continue even if database save fails
        
        # Construct the email
        msg = EmailMessage()
        msg["To"] = "rideal.bikes@gmail.com"
        msg["Subject"] = f"בקשה לבדיקת זמינות מ-{name}"
        msg["From"] = os.getenv("EMAIL_USER") or "rideal.bikes@gmail.com"
        
        # Build email body
        body = f"בקשה לבדיקת זמינות\n\n"
        body += f"שם: {name}\n"
        body += f"טלפון: {phone}\n"
        body += f"עיר: {city}\n"
        body += f"דגם אופניים: {bike_model}\n"
        if importer_info:
            body += f"יבואן: {importer_info}\n"
        if preferred_size:
            body += f"גובה מועדף: {preferred_size} ס\"מ\n"
        body += f"\nתאריך: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        msg.set_content(body)
        
        # Send the email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
            smtp.send_message(msg)
        
        return "הבקשה נשלחה בהצלחה", 200
        
    except Exception as e:
        print(f"Error sending availability check email: {e}")
        import traceback
        traceback.print_exc()
        return "אירעה שגיאה בשליחת הבקשה", 500

@bp.route("/find-store", methods=["POST"])
def find_store():
    """Handle find store form submission"""
    try:
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        city = request.form.get("city", "").strip()
        bike_model = request.form.get("bike_model", "").strip()
        bike_id = request.form.get("bike_id", "").strip()
        remarks = request.form.get("remarks", "").strip()
        
        # Validate required fields
        if not name or not phone or not city:
            return "שדות חובה חסרים", 400
        
        # Save lead to database
        try:
            lead = StoreRequestLead(
                name=name,
                phone=phone,
                city=city,
                bike_model=bike_model,
                bike_id=bike_id,
                remarks=remarks if remarks else None
            )
            db.session.add(lead)
            db.session.commit()
        except Exception as e:
            print(f"Error saving store request lead: {e}")
            db.session.rollback()
            # Continue even if database save fails
        
        # Construct the email
        msg = EmailMessage()
        msg["To"] = "rideal.bikes@gmail.com"
        msg["Subject"] = f"בקשה למציאת חנות מ-{name}"
        msg["From"] = os.getenv("EMAIL_USER") or "rideal.bikes@gmail.com"
        
        # Build email body
        body = f"בקשה למציאת חנות\n\n"
        body += f"שם: {name}\n"
        body += f"טלפון: {phone}\n"
        body += f"עיר: {city}\n"
        body += f"דגם אופניים: {bike_model}\n"
        if remarks:
            body += f"הערות/שאלות: {remarks}\n"
        body += f"\nתאריך: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        msg.set_content(body)
        
        # Send the email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
            smtp.send_message(msg)
        
        return "הבקשה נשלחה בהצלחה", 200
        
    except Exception as e:
        print(f"Error sending find store email: {e}")
        import traceback
        traceback.print_exc()
        return "אירעה שגיאה בשליחת הבקשה", 500

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

    # Individual bike pages - load only UUIDs, not all bike data
    bike_uuids = db.session.query(Bike.uuid).all()
    for (bike_uuid,) in bike_uuids:
        pages.append({
            'loc': url_for('bikes.bikes', bike_id=bike_uuid, _external=True),
            'lastmod': ten_days_ago,
            'priority': '0.5'
        })

    # Add persistent comparison pages
    try:
        comparisons = db.session.query(Comparison).all()
        for comparison in comparisons:
            if comparison.slug:
                pages.append({
                    'loc': url_for('compare.view_comparison', slug=comparison.slug, _external=True),
                    'lastmod': comparison.created_at.date().isoformat() if comparison.created_at else ten_days_ago,
                    'priority': '0.7'
                })
    except:
        pass

    # Create XML string
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    return Response(sitemap_xml, mimetype='application/xml')

@bp.route('/privacy-policy')
def privacy_policy():
    return render_template("privacy_policy.html")


@bp.route('/terms-of-use')
def terms_of_use():
    return render_template("terms_of_use.html")


@bp.route('/cookie-preferences')
def cookie_preferences():
    return render_template("cookie_preferences.html")


@bp.route('/electric-subcategories')
def electric_subcategories():
    """Display Electric bike sub-category selection page"""
    from app.extensions import db
    from app.models import Bike
    
    # Electric MTB count
    electric_mtb_count = db.session.query(Bike).filter(
        Bike.category == 'electric',
        Bike.sub_category == 'electric_mtb'
    ).count()
    
    # Electric City count (including the one with space: "electric_ city")
    electric_city_count = db.session.query(Bike).filter(
        Bike.category == 'electric',
        Bike.sub_category.in_(['electric_city', 'electric_ city'])
    ).count()
    
    # Electric Gravel count
    electric_gravel_count = db.session.query(Bike).filter(
        Bike.category == 'electric',
        Bike.sub_category == 'electric_gravel'
    ).count()
    
    subcategories = [
        {
            'slug': 'electric_mtb',
            'name': 'אופני הרים חשמליים',
            'description': 'שילוב מושלם של כוח חשמלי ויכולות שטח',
            'image': 'images/categories/electric_mtb.jpg',
            'count': electric_mtb_count
        },
        {
            'slug': 'electric_city',
            'name': 'אופני עיר חשמליים',
            'description': 'נסיעה נוחה בעיר עם סיוע חשמלי',
            'image': 'images/categories/electric_city_bike.jpg',
            'count': electric_city_count
        }
    ]
    
    # Only add gravel if there are bikes
    if electric_gravel_count > 0:
        subcategories.append({
            'slug': 'electric_gravel',
            'name': 'אופני גרוול חשמליים',
            'description': 'גמישות לכל שטח עם עזרה חשמלית',
            'image': 'images/blog/alps_man_walks_with_bike.jpg',
            'count': electric_gravel_count
        })
    
    return render_template("electric_subcategories.html", subcategories=subcategories)

@bp.route('/mtb-subcategories')
def mtb_subcategories():
    """Display MTB sub-category selection page (Full Suspension vs Hardtail)"""
    from app.extensions import db
    from app.models import Bike
    
    # Full suspension includes: full_suspension (the actual value in DB)
    full_suspension_count = db.session.query(Bike).filter(
        Bike.category == 'mtb',
        Bike.sub_category == 'full_suspension'
    ).count()
    
    # Hardtail - check what value exists in DB
    hardtail_count = db.session.query(Bike).filter(
        Bike.category == 'mtb',
        Bike.sub_category == 'hardtail'
    ).count()
    
    # If no hardtail, check for hardtail_mtb
    if hardtail_count == 0:
        hardtail_count = db.session.query(Bike).filter(
            Bike.category == 'mtb',
            Bike.sub_category.like('%hardtail%')
        ).count()
    
    subcategories = [
        {
            'slug': 'full_suspension',
            'name': 'שיכוך מלא',
            'description': 'בולם קדמי ואחורי למירב נוחות ושליטה בשטח',
            'image': 'images/categories/full_suspension_drawing.png',
            'count': full_suspension_count
        },
        {
            'slug': 'hardtail',
            'name': 'זנב קשיח',
            'description': 'בולם קדמי בלבד, קלים יותר ויעילים בעליות',
            'image': 'images/categories/hardtail_drawing.png',
            'count': hardtail_count
        }
    ]
    
    return render_template("mtb_subcategories.html", subcategories=subcategories)

@bp.route('/categories')
def categories():
    """Display category selection page"""
    from app.extensions import db
    from app.models import Bike
    
    # Get all distinct categories with counts
    category_data = db.session.query(
        Bike.category,
        db.func.count(Bike.id).label('count')
    ).filter(
        Bike.category.isnot(None)
    ).group_by(Bike.category).all()
    
    # Map categories to Hebrew names and images
    category_info = {
        'electric': {
            'name': 'חשמליים',
            'description': 'עזרה למי שצריך',
            'image': 'images/categories/electric.jpg'
        },
        'mtb': {
            'name': 'אופני שטח',
            'description': 'שטח, שבילים, קפיצות',
            'image': 'images/categories/mtb_rider.jpg'
        },
        'kids': {
            'name': 'אופני ילדים',
            'description': 'בטיחות והנאה לקטנים',
            'image': 'images/categories/kids_rider.jpg'
        },
        'city': {
            'name': 'אופני עיר',
            'description': 'נסיעה נוחה בעיר',
            'image': 'images/categories/city_rider.jpg'
        },
        'road': {
            'name': 'אופני כביש',
            'description': 'מהירות על האספלט',
            'image': 'images/categories/road_rider.jpg'
        },
        'gravel': {
            'name': 'אופני גראבל',
            'description': 'אופני "כביש" לשטח',
            'image': 'images/categories/gravel_rider.jpg'
        }
    }
    
    # Build categories list with info and counts
    categories_list = []
    for cat, count in category_data:
        if cat in category_info:
            categories_list.append({
                'slug': cat,
                'name': category_info[cat]['name'],
                'description': category_info[cat]['description'],
                'image': category_info[cat]['image'],
                'count': count
            })
    
    return render_template("categories.html", categories=categories_list)