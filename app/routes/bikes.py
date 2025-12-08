from flask import Blueprint, render_template, request, jsonify, abort
from app.extensions import db
from app.models import Bike, Brand, BikeListing, BikePrice
from app.services.bike_service import (
    get_all_firms, get_all_sub_categories, get_firms_by_category, 
    get_sub_categories_by_category, get_all_styles, get_styles_by_category
)
from app.utils.helpers import parse_price, get_frame_material, get_motor_brand
from sqlalchemy import or_

bp = Blueprint('bikes', __name__)

@bp.route("/bikes")
def bikes():
    # Load all bikes for client-side filtering (faster with max 300 bikes)
    
    # Get category filter from URL parameter (for backward compatibility)
    selected_category = request.args.get('category', None)
    
    # Get sub_category filters from URL parameters (for MTB subcategories)
    selected_sub_categories = request.args.getlist('sub_category')
    
    # Get firms, sub-categories, and styles filtered by category if one is selected
    if selected_category:
        firms = get_firms_by_category(selected_category)
        sub_categories = get_sub_categories_by_category(selected_category)
        styles = get_styles_by_category(selected_category)
    else:
        firms = get_all_firms()
        sub_categories = get_all_sub_categories()
        styles = get_all_styles()
    
    # Load ALL bikes (with filters if specified) for client-side filtering
    initial_query = db.session.query(Bike).options(
        db.joinedload(Bike.brand),
        db.joinedload(Bike.listings).joinedload(BikeListing.prices),
        db.joinedload(Bike.listings).joinedload(BikeListing.raw_specs),
        db.joinedload(Bike.images)
    )
    
    # Apply category filter
    if selected_category:
        initial_query = initial_query.filter(Bike.category == selected_category)
    
    # Apply sub_category filter
    if selected_sub_categories:
        # Handle electric_city special case (some have "electric_ city" with space)
        expanded_subcats = []
        for subcat in selected_sub_categories:
            expanded_subcats.append(subcat)
            if subcat == 'electric_city':
                expanded_subcats.append('electric_ city')  # Handle data quality issue
        initial_query = initial_query.filter(Bike.sub_category.in_(expanded_subcats))
    
    # Get ALL bikes (no limit for client-side filtering)
    initial_bikes = initial_query.all()
    
    # Convert to template-compatible format
    bikes_for_template = [bike.to_dict() for bike in initial_bikes]
    bikes_count = len(bikes_for_template)
    
    return render_template("bikes.html", bikes=bikes_for_template, bikes_count=bikes_count, firms=firms, sub_categories=sub_categories, styles=styles, selected_category=selected_category, selected_sub_categories=selected_sub_categories)


@bp.route("/<category>")
def category_bikes(category):
    """Dynamic route for category-specific bike pages"""
    # Valid categories from the database
    valid_categories = ['electric', 'mtb', 'kids', 'city', 'road', 'gravel']
    
    # Check if the category is valid
    if category not in valid_categories:
        abort(404)
    
    # Load ALL bikes for this category for client-side filtering
    # With max 300 bikes per category, this is faster than AJAX calls
    category_bikes_query = db.session.query(Bike).options(
        db.joinedload(Bike.brand),
        db.joinedload(Bike.listings).joinedload(BikeListing.prices),
        db.joinedload(Bike.listings).joinedload(BikeListing.raw_specs),
        db.joinedload(Bike.images)
    ).filter(Bike.category == category).all()  # Load ALL bikes
    
    # Convert to template-compatible format
    bikes_for_template = [bike.to_dict() for bike in category_bikes_query]
    bikes_count = len(bikes_for_template)
    
    # Get firms, sub_categories, and styles filtered by this specific category
    firms = get_firms_by_category(category)
    sub_categories = get_sub_categories_by_category(category)
    styles = get_styles_by_category(category)
    
    # Pass all bikes for client-side filtering (instant response!)
    return render_template("bikes.html", bikes=bikes_for_template, bikes_count=bikes_count, firms=firms, sub_categories=sub_categories, styles=styles, selected_category=category, selected_sub_categories=[])

@bp.route("/api/filter_bikes")
def filter_bikes():
    try:
        query = request.args.get("q", "").strip().lower()
        min_price = request.args.get("min_price", type=int)
        max_price = request.args.get("max_price", type=int)
        years = request.args.getlist("year", type=int)
        firms = request.args.getlist("firm")
        min_battery = request.args.get("min_battery", type=int)
        max_battery = request.args.get("max_battery", type=int)
        min_fork = request.args.get("min_fork", type=int)
        max_fork = request.args.get("max_fork", type=int)
        frame_material = request.args.get("frame_material", type=str)
        motor_brands = request.args.getlist("motor_brand", type=str)
        sub_categories = request.args.getlist("sub_category", type=str)
        styles = request.args.getlist("style", type=str)
        has_discount = request.args.get("has_discount", type=str)
        category = request.args.get("category", type=str)
        
        # Pagination for infinite scroll
        offset = request.args.get("offset", type=int, default=0)
        limit = request.args.get("limit", type=int, default=1000)  # Default: load all

        # Start with base query - use MySQL models
        # Note: MySQL Bike model uses different structure (normalized with relationships)
        # We need to query with proper joins
        db_query = db.session.query(Bike).options(
            db.joinedload(Bike.brand),
            db.joinedload(Bike.listings).joinedload(BikeListing.prices),
            db.joinedload(Bike.listings).joinedload(BikeListing.raw_specs),
            db.joinedload(Bike.images)
        )
        
        # Track if we've already joined Brand table to avoid duplicate joins
        brand_joined = False
        
        # Apply filters using database queries for better performance
        if query:
            # Search across model field and brand name
            # Join brand table for search
            db_query = db_query.join(Brand, Bike.brand_id == Brand.id, isouter=True)
            brand_joined = True
            
            search_conditions = [
                Bike.model.ilike(f'%{query}%'),
                Brand.name.ilike(f'%{query}%')
            ]
            db_query = db_query.filter(or_(*search_conditions))

        if years:
            db_query = db_query.filter(Bike.year.in_(years))

        if firms:
            # Firms = brands in MySQL model
            # Only join if not already joined for search
            if not brand_joined:
                db_query = db_query.join(Brand, Bike.brand_id == Brand.id)
                brand_joined = True
            db_query = db_query.filter(Brand.name.in_(firms))

        # Battery and other specs are in bike_specs_std table
        # For now, we'll filter these in Python after query (less efficient but works)
        # TODO: Optimize with proper joins to bike_specs_std

        if sub_categories:
            # Handle electric_city special case (some have "electric_ city" with space)
            expanded_subcats = []
            for subcat in sub_categories:
                expanded_subcats.append(subcat)
                if subcat == 'electric_city':
                    expanded_subcats.append('electric_ city')
            db_query = db_query.filter(Bike.sub_category.in_(expanded_subcats))
        
        if styles:
            db_query = db_query.filter(Bike.style.in_(styles))
        
        if category:
            db_query = db_query.filter(Bike.category == category)
        
        # Don't apply offset/limit yet - we need to filter in Python first
        # Execute query to get all matching bikes (filtered by SQL conditions)
        bikes = db_query.all()
        
        # Apply Python-side filters and collect matching bikes
        filtered_bikes = []
        import re
        
        for bike in bikes:
            # Convert to template-compatible format
            bike_dict = bike.to_dict()
            
            # Price filtering
            price_str = bike_dict.get('disc_price') or bike_dict.get('price')
            price = parse_price(price_str)
            
            if min_price is not None:
                if price is not None and price < min_price:
                    continue
            if max_price is not None:
                if price is not None and price > max_price:
                    continue

            # Battery filtering (from specs)
            if min_battery is not None or max_battery is not None:
                wh_str = bike_dict.get('wh')
                try:
                    wh = int(wh_str) if wh_str and wh_str.isdigit() else None
                    if wh:
                        if min_battery is not None and wh < min_battery:
                            continue
                        if max_battery is not None and wh > max_battery:
                            continue
                except:
                    pass

            # Fork length filtering (from direct column)
            if min_fork is not None or max_fork is not None:
                fork_str = bike_dict.get('fork_length')
                try:
                    if fork_str:
                        # Try to find first number in the string
                        numbers = re.findall(r'\d+', str(fork_str))
                        fork_length = int(numbers[0]) if numbers else None
                        if fork_length:
                            if min_fork is not None and fork_length < min_fork:
                                continue
                            if max_fork is not None and fork_length > max_fork:
                                continue
                except:
                    pass

            # Frame material filtering
            if frame_material:
                bike_frame_material = get_frame_material(bike_dict)
                if bike_frame_material != frame_material:
                    continue

            # Motor brand filtering
            if motor_brands:
                bike_motor_brand = get_motor_brand(bike_dict)
                if bike_motor_brand not in motor_brands:
                    continue
            
            # Discount filtering
            if has_discount == "true":
                if not bike_dict.get('disc_price'):
                    continue

            filtered_bikes.append(bike_dict)
        
        # Now apply pagination to filtered results
        total_filtered = len(filtered_bikes)
        paginated_bikes = filtered_bikes[offset:offset + limit]
        has_more = (offset + len(paginated_bikes)) < total_filtered

        return jsonify({
            'success': True,
            'bikes': paginated_bikes,
            'count': len(paginated_bikes),
            'total': total_filtered,
            'has_more': has_more
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
