from flask import Blueprint, render_template, request, jsonify, abort, redirect, url_for
from app.extensions import db
from app.models import Bike, Brand, BikeListing, BikePrice, BikeSpecRaw
from app.services.bike_service import (
    get_all_firms, get_all_sub_categories, get_firms_by_category, 
    get_sub_categories_by_category, get_all_styles, get_styles_by_category
)
from app.utils.helpers import parse_price, get_frame_material, get_motor_brand, translate_spec_key_to_hebrew
from sqlalchemy import or_

bp = Blueprint('bikes', __name__)

@bp.route("/bikes")
def bikes():
    # Load all bikes for client-side filtering (faster with max 300 bikes)
    
    # Get category filter from URL parameter (for backward compatibility)
    selected_category = request.args.get('category', None)
    
    # Get sub_category filters from URL parameters (for MTB subcategories)
    selected_sub_categories = request.args.getlist('sub_category')
    
    # Load ALL bikes (with filters if specified) for client-side filtering
    # Optimized: Skip images loading for list view (not needed for initial render)
    initial_query = db.session.query(Bike).options(
        db.joinedload(Bike.brand),
        db.joinedload(Bike.listings).joinedload(BikeListing.prices),
        db.joinedload(Bike.listings).joinedload(BikeListing.raw_specs)
        # Note: Images not loaded here - not needed for list view, reduces query time
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
    
    # Get firms, sub-categories, and styles based on filtered bikes
    # If sub_category is selected, extract firms from the actual filtered bikes
    # This ensures firms list only shows brands present in the filtered results
    if selected_sub_categories:
        # Extract unique firms from the filtered bikes
        firms_set = set()
        for bike in initial_bikes:
            if bike.brand and bike.brand.name:
                firms_set.add(bike.brand.name)
        firms = sorted(list(firms_set))
        
        # Extract unique sub_categories from filtered bikes
        sub_categories_set = set()
        for bike in initial_bikes:
            if bike.sub_category and bike.sub_category not in ['', 'unknown']:
                sub_categories_set.add(bike.sub_category)
        sub_categories = sorted(list(sub_categories_set))
        
        # Extract unique styles from filtered bikes
        styles_set = set()
        for bike in initial_bikes:
            if bike.style and bike.style not in ['', 'unknown']:
                styles_set.add(bike.style)
        styles = sorted(list(styles_set))
    elif selected_category:
        # Use category-based filtering when only category is selected
        firms = get_firms_by_category(selected_category)
        sub_categories = get_sub_categories_by_category(selected_category)
        styles = get_styles_by_category(selected_category)
    else:
        # No filters - show all
        firms = get_all_firms()
        sub_categories = get_all_sub_categories()
        styles = get_all_styles()
    
    # Convert to template-compatible format using lightweight list_view mode
    # This only includes essential specs (wh, frame_material, motor_brand) for filtering
    # and skips gallery images, significantly reducing payload size
    bikes_for_template = [bike.to_dict(list_view=True, include_images=False) for bike in initial_bikes]
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
    # Optimized: Skip images loading for list view (not needed for initial render)
    category_bikes_query = db.session.query(Bike).options(
        db.joinedload(Bike.brand),
        db.joinedload(Bike.listings).joinedload(BikeListing.prices),
        db.joinedload(Bike.listings).joinedload(BikeListing.raw_specs)
        # Note: Images not loaded here - not needed for list view, reduces query time
    ).filter(Bike.category == category).all()  # Load ALL bikes
    
    # Convert to template-compatible format using lightweight list_view mode
    # This only includes essential specs (wh, frame_material, motor_brand) for filtering
    # and skips gallery images, significantly reducing payload size
    bikes_for_template = [bike.to_dict(list_view=True, include_images=False) for bike in category_bikes_query]
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
            # Include bikes matching selected years OR bikes with null year
            db_query = db_query.filter(or_(Bike.year.in_(years), Bike.year.is_(None)))

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
                # Include bikes with null/unknown frame material OR bikes matching selected material
                if bike_frame_material is not None and bike_frame_material != frame_material:
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

@bp.route("/bike/<bike_id>")
def bike_detail(bike_id):
    """Bike detail page - similar to recycles.co.il design"""
    try:
        # Try to find bike by slug first (SEO-friendly), then by UUID (backward compatibility)
        bike = db.session.query(Bike).options(
            db.joinedload(Bike.brand),
            db.joinedload(Bike.listings).joinedload(BikeListing.raw_specs),
            db.joinedload(Bike.listings).joinedload(BikeListing.prices),
            db.joinedload(Bike.images)
        ).filter(
            (Bike.slug == bike_id) | (Bike.uuid == bike_id)
        ).first()
        
        if not bike:
            abort(404)
        
        # If accessed via UUID but slug exists, redirect to slug for SEO
        if bike.slug and bike.uuid == bike_id:
            return redirect(url_for('bikes.bike_detail', bike_id=bike.slug), code=301)
        
        # Convert to template-compatible format with all data
        bike_dict = bike.to_dict(include_specs=True, include_prices=True, include_images=True, flat_format=True, list_view=False)
        
        # Get rewritten_description from multiple sources
        rewritten_description = None
        
        # First, try to get from raw_specs (check all listings)
        if bike.listings:
            for listing in bike.listings:
                if listing.raw_specs:
                    for raw_spec in listing.raw_specs:
                        # Check case-insensitively and also check for variations
                        spec_key_lower = raw_spec.spec_key_raw.lower().strip()
                        if spec_key_lower == 'rewritten_description' or spec_key_lower == 'rewritten description':
                            rewritten_description = raw_spec.spec_value_raw
                            break
                if rewritten_description:
                    break
        
        # If not found in raw_specs, try from bike.description
        if not rewritten_description or not rewritten_description.strip():
            rewritten_description = bike.description
        
        # If still not found, try from bike_dict (in case it's stored there)
        if (not rewritten_description or not rewritten_description.strip()) and bike_dict:
            rewritten_description = bike_dict.get('rewritten_description') or bike_dict.get('description')
        
        # Get gallery images
        gallery_images = []
        if bike.images:
            # Sort images: main image first, then by position
            sorted_images = sorted(bike.images, key=lambda x: (not x.is_main, x.position))
            gallery_images = [img.image_url for img in sorted_images]
        
        # Get raw specs for display and translate keys to Hebrew
        raw_specs = {}
        if bike.listings and bike.listings[0].raw_specs:
            for raw_spec in bike.listings[0].raw_specs:
                # Skip rewritten_description as it's displayed separately
                if raw_spec.spec_key_raw != 'rewritten_description':
                    # Translate the key to Hebrew for display
                    hebrew_key = translate_spec_key_to_hebrew(raw_spec.spec_key_raw)
                    raw_specs[hebrew_key] = raw_spec.spec_value_raw
        
        # Get product URL from latest listing
        product_url = None
        if bike.listings:
            product_url = bike.listings[0].product_url
        
        # Get prices from bike_dict (to_dict returns 'price' as original_price and 'disc_price' as disc_price)
        original_price = bike_dict.get('price')
        disc_price = bike_dict.get('disc_price')
        
        # Parse prices for structured data (numeric values)
        parsed_price = None
        if disc_price and disc_price != 'None' and disc_price != '' and disc_price != 'צור קשר':
            parsed_price = parse_price(disc_price)
        elif original_price and original_price != 'None' and original_price != '' and original_price != 'צור קשר':
            parsed_price = parse_price(original_price)
        
        # If disc_price exists, original_price is the original, otherwise price is the current price
        # The to_dict method already handles this correctly
        
        # Category and sub_category Hebrew translations
        category_translations = {
            'electric': 'חשמליים',
            'mtb': 'אופני הרים',
            'kids': 'אופני ילדים',
            'city': 'אופני עיר',
            'road': 'אופני כביש',
            'gravel': 'אופני גראבל'
        }
        
        sub_category_translations = {
            'electric_mtb': 'אופני הרים חשמליים',
            'electric_city': 'אופני עיר חשמליים',
            'hardtail': 'הארדטייל',
            'full_suspension': 'שיכוך מלא',
            'city': 'אופני עיר',
            'folding_city': 'אופני עיר מתקפלים',
            'gravel': 'אופני גראבל',
            'road': 'אופני כביש',
            'time_trial': 'נגד השעון',
            'kids': 'אופני ילדים',
            'kids_mtb': 'אופני הרים לילדים',
            'pushbike': 'אופני איזון'
        }
        
        category_hebrew = category_translations.get(bike.category, bike.category) if bike.category else None
        sub_category_hebrew = sub_category_translations.get(bike.sub_category, bike.sub_category) if bike.sub_category else None
        
        # Get canonical bike_id (prefer slug, fallback to uuid)
        canonical_bike_id = bike.slug if bike.slug else bike.uuid
        
        return render_template(
            "bike_detail.html",
            bike=bike_dict,
            brand=bike.brand.name if bike.brand else None,
            model=bike.model,
            year=bike.year,
            category=bike.category,
            category_hebrew=category_hebrew,
            sub_category=bike.sub_category,
            sub_category_hebrew=sub_category_hebrew,
            original_price=original_price,
            disc_price=disc_price,
            main_image=bike_dict.get('image_url'),
            gallery_images=gallery_images,
            product_url=product_url,
            rewritten_description=rewritten_description,
            raw_specs=raw_specs,
            bike_id=canonical_bike_id,
            parsed_price=parsed_price
        )
    except Exception as e:
        print(f"Error in bike_detail: {e}")
        import traceback
        traceback.print_exc()
        abort(500)

@bp.route("/similar_bikes/<bike_id>")
def similar_bikes(bike_id):
    """Get similar bikes based on category and price range"""
    try:
        # Find the current bike
        bike = db.session.query(Bike).options(
            db.joinedload(Bike.brand),
            db.joinedload(Bike.listings).joinedload(BikeListing.prices)
        ).filter(
            (Bike.slug == bike_id) | (Bike.uuid == bike_id)
        ).first()
        
        if not bike:
            return jsonify({'error': 'Bike not found'}), 404
        
        # Get current bike's price (prefer disc_price, fallback to original_price)
        bike_dict = bike.to_dict(include_specs=False, include_prices=True, include_images=False, flat_format=True)
        price_str = bike_dict.get('disc_price') or bike_dict.get('price')
        current_price = parse_price(price_str)
        
        # Build query for similar bikes
        similar_query = db.session.query(Bike).options(
            db.joinedload(Bike.brand),
            db.joinedload(Bike.listings).joinedload(BikeListing.prices),
            db.joinedload(Bike.listings).joinedload(BikeListing.raw_specs)
        ).filter(
            Bike.id != bike.id  # Exclude current bike
        )
        
        # Filter by same category if available
        if bike.category:
            similar_query = similar_query.filter(Bike.category == bike.category)
        
        # Get all potential similar bikes
        similar_bikes_list = similar_query.all()
        
        # Calculate price similarity and filter by price range (±50% of current price)
        similar_bikes_with_scores = []
        for similar_bike in similar_bikes_list:
            similar_bike_dict = similar_bike.to_dict(include_specs=False, include_prices=True, include_images=False, flat_format=True)
            similar_price_str = similar_bike_dict.get('disc_price') or similar_bike_dict.get('price')
            similar_price = parse_price(similar_price_str)
            
            # Skip bikes without valid prices (if current bike has a price)
            if current_price and (not similar_price or similar_price == 0):
                continue
            
            # Filter by price range (±50% of current price)
            if current_price:
                min_price = current_price * 0.5
                max_price = current_price * 1.5
                if similar_price < min_price or similar_price > max_price:
                    continue
                
                # Calculate price similarity score (lower is better)
                price_diff = abs(similar_price - current_price)
                price_similarity = price_diff / current_price if current_price > 0 else float('inf')
            else:
                # If current bike has no price, accept all bikes
                price_similarity = 0
            
            # Also consider sub_category if available
            sub_category_match = 1 if (bike.sub_category and similar_bike.sub_category == bike.sub_category) else 0
            
            # Calculate total similarity score (lower is better)
            # Weight price similarity more heavily
            similarity_score = price_similarity * 0.7 + (1 - sub_category_match) * 0.3
            
            similar_bikes_with_scores.append((similarity_score, similar_bike_dict))
        
        # Sort by similarity score and take top 15
        similar_bikes_with_scores.sort(key=lambda x: x[0])
        top_similar = [bike_dict for _, bike_dict in similar_bikes_with_scores[:15]]
        
        # Clean bike data for JSON
        from app.utils.helpers import clean_bike_data_for_json
        cleaned_similar = [clean_bike_data_for_json(b) for b in top_similar]
        
        return jsonify({'similar_bikes': cleaned_similar})
        
    except Exception as e:
        print(f"Error in similar_bikes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500