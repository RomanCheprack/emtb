"""
New bike service that works with the normalized MySQL database schema.
Provides backward compatibility with the old flat structure.
"""

from app.extensions import cache, db
from app.models import Bike, Brand, BikeListing, BikePrice, BikeSpecStd, BikeSpecRaw, BikeImage
from app.utils.helpers import clean_bike_data_for_json
from sqlalchemy import or_
import json


# convert_new_bike_to_old_format() function REMOVED
# Conversion logic moved to Bike.to_dict() method in app/models/models.py
# This is cleaner and keeps the logic with the model where it belongs


def get_bike_serializer():
    """
    Return the bike serializer (using to_dict() method).
    This allows consistent formatting across the application.
    """
    return lambda bike: bike.to_dict()


# serialize_bike() function REMOVED
# Use bike.to_dict() method instead which is defined in the Bike model


@cache.memoize(timeout=1800)  # Cache for 30 minutes (brands change rarely)
def get_all_brands():
    """Get all unique brands from database"""
    try:
        brands = Brand.query.order_by(Brand.name).all()
        return [brand.name for brand in brands]
    except Exception as e:
        print(f"Error loading brands: {e}")
        return []


@cache.memoize(timeout=1800)  # Cache for 30 minutes (sub-categories change rarely)
def get_all_sub_categories():
    """Get all unique sub-categories from database"""
    try:
        sub_categories = db.session.query(Bike.sub_category).distinct().filter(
            Bike.sub_category.isnot(None),
            Bike.sub_category != '',
            Bike.sub_category != 'unknown'
        ).all()
        return sorted([cat[0] for cat in sub_categories if cat[0]])
    except Exception as e:
        print(f"Error loading sub-categories: {e}")
        return []


def get_brands_by_category(category):
    """Get unique brands that have bikes in a specific category"""
    try:
        if not category:
            return get_all_brands()
        
        brands = db.session.query(Brand).join(Bike).filter(
            Bike.category == category
        ).distinct().order_by(Brand.name).all()
        
        return [brand.name for brand in brands]
    except Exception as e:
        print(f"Error loading brands for category {category}: {e}")
        return []


def get_sub_categories_by_category(category):
    """Get unique sub-categories for bikes in a specific category"""
    try:
        if not category:
            return get_all_sub_categories()
        
        sub_categories = db.session.query(Bike.sub_category).filter(
            Bike.category == category,
            Bike.sub_category.isnot(None),
            Bike.sub_category != '',
            Bike.sub_category != 'unknown'
        ).distinct().all()
        
        return sorted([cat[0] for cat in sub_categories if cat[0]])
    except Exception as e:
        print(f"Error loading sub-categories for category {category}: {e}")
        return []


@cache.memoize(timeout=1800)  # Cache for 30 minutes
def get_all_styles():
    """Get all unique styles from database"""
    try:
        styles = db.session.query(Bike.style).distinct().filter(
            Bike.style.isnot(None),
            Bike.style != '',
            Bike.style != 'unknown'
        ).all()
        return sorted([style[0] for style in styles if style[0]])
    except Exception as e:
        print(f"Error loading styles: {e}")
        return []


def get_styles_by_category(category):
    """Get unique styles for bikes in a specific category"""
    try:
        if not category:
            return get_all_styles()
        
        styles = db.session.query(Bike.style).filter(
            Bike.category == category,
            Bike.style.isnot(None),
            Bike.style != '',
            Bike.style != 'unknown'
        ).distinct().all()
        
        return sorted([style[0] for style in styles if style[0]])
    except Exception as e:
        print(f"Error loading styles for category {category}: {e}")
        return []


def get_wheel_sizes_by_category(category):
    """Get unique wheel sizes for bikes in a specific category (kids only).
    Returns empty list for non-kids categories.
    Queries both bike_specs_std and bike_specs_raw - production may have data in
    raw specs only (from listings) while std specs come from bike-level migration."""
    if category != 'kids':
        return []
    try:
        from sqlalchemy import func
        values_set = set()

        # 1. Query BikeSpecStd (bike-level standardized specs)
        std_results = db.session.query(BikeSpecStd.spec_value).join(Bike).filter(
            Bike.category == 'kids',
            BikeSpecStd.spec_name == 'wheel_size',
            BikeSpecStd.spec_value.isnot(None),
            BikeSpecStd.spec_value != ''
        ).distinct().all()

        # 2. Query BikeSpecRaw (listing-level raw specs) - production often has data here
        raw_results = db.session.query(BikeSpecRaw.spec_value_raw).join(
            BikeListing, BikeSpecRaw.listing_id == BikeListing.id
        ).join(Bike, BikeListing.bike_id == Bike.id).filter(
            Bike.category == 'kids',
            func.lower(func.replace(BikeSpecRaw.spec_key_raw, ' ', '_')) == 'wheel_size',
            BikeSpecRaw.spec_value_raw.isnot(None),
            BikeSpecRaw.spec_value_raw != ''
        ).distinct().all()

        def parse_value(val):
            try:
                return int(float(str(val).strip()))
            except (ValueError, TypeError):
                return None

        for (val,) in std_results:
            n = parse_value(val)
            if n is not None:
                values_set.add(n)
        for (val,) in raw_results:
            n = parse_value(val)
            if n is not None:
                values_set.add(n)

        # Ensure standard kids sizes (12-26") are always available in filter
        values_set.update([12, 14, 16, 18, 20, 24, 26])
        return sorted(values_set)
    except Exception as e:
        print(f"Error loading wheel sizes for category {category}: {e}")
        return []


def get_bike_by_uuid(uuid):
    """Get a single bike by UUID"""
    try:
        bike = Bike.query.options(
            db.joinedload(Bike.brand),
            db.joinedload(Bike.listings).joinedload(BikeListing.prices),
            db.joinedload(Bike.standardized_specs),
            db.joinedload(Bike.images)
        ).filter_by(uuid=uuid).first()
        if bike:
            return bike.to_dict()
        return None
    except Exception as e:
        print(f"Error loading bike {uuid}: {e}")
        return None


def get_bikes_by_uuids(uuids):
    """Get multiple bikes by their UUIDs or slugs"""
    try:
        bikes = Bike.query.options(
            db.joinedload(Bike.brand),
            db.joinedload(Bike.listings).joinedload(BikeListing.prices),
            db.joinedload(Bike.standardized_specs),
            db.joinedload(Bike.images)
        ).filter(
            or_(Bike.uuid.in_(uuids), Bike.slug.in_(uuids))
        ).all()
        return [bike.to_dict() for bike in bikes]
    except Exception as e:
        print(f"Error loading bikes: {e}")
        return []

