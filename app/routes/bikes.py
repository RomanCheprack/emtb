from flask import Blueprint, render_template, request, jsonify
from app.models.bike import get_session, Bike
from app.services.bike_service import load_all_bikes, get_all_firms, get_all_sub_categories
from app.utils.helpers import parse_price, get_frame_material, get_motor_brand
from sqlalchemy import or_

bp = Blueprint('bikes', __name__)

@bp.route("/bikes")
def bikes():
    all_bikes = load_all_bikes()
    firms = get_all_firms()
    sub_categories = get_all_sub_categories()
    
    return render_template("bikes.html", bikes=all_bikes, firms=firms, sub_categories=sub_categories)

@bp.route("/api/filter_bikes")
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
        has_discount = request.args.get("has_discount", type=str)

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

        if has_discount == "true":
            db_query = db_query.filter(Bike.disc_price.isnot(None)).filter(Bike.disc_price != '')

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
                if bike_frame_material != frame_material:
                    continue

            # Motor brand filtering
            if motor_brands:
                bike_motor_brand = get_motor_brand({
                    'motor': bike.motor
                })
                if bike_motor_brand not in motor_brands:
                    continue

            # Convert bike to dict for JSON response
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
            filtered_bikes.append(bike_dict)

        return jsonify({
            'success': True,
            'bikes': filtered_bikes,
            'count': len(filtered_bikes)
        })

    except Exception as e:
        print(f"Error in filter_bikes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'bikes': [],
            'count': 0
        }), 500
    finally:
        db_session.close()
