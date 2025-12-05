"""
New bike service that works with the normalized MySQL database schema.
Provides backward compatibility with the old flat structure.
"""

from app.extensions import cache, db
from app.models import Bike, Brand, BikeListing, BikePrice, BikeSpecStd, BikeImage
from app.utils.helpers import clean_bike_data_for_json
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
def get_all_firms():
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


def get_firms_by_category(category):
    """Get unique brands that have bikes in a specific category"""
    try:
        if not category:
            return get_all_firms()
        
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
    """Get multiple bikes by their UUIDs"""
    try:
        bikes = Bike.query.options(
            db.joinedload(Bike.brand),
            db.joinedload(Bike.listings).joinedload(BikeListing.prices),
            db.joinedload(Bike.standardized_specs),
            db.joinedload(Bike.images)
        ).filter(Bike.uuid.in_(uuids)).all()
        return [bike.to_dict() for bike in bikes]
    except Exception as e:
        print(f"Error loading bikes: {e}")
        return []

