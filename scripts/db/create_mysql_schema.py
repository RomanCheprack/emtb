#!/usr/bin/env python3
"""
Script to create the MySQL database schema for the new normalized structure.

This script will:
1. Connect to MySQL database
2. Create all tables based on the new models
3. Create indexes for performance
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db

def add_performance_indexes():
    """Add performance indexes after schema creation"""
    # Indexes to create
    indexes = [
        # Basic filtering indexes
        ("idx_bikes_category", "bikes", "category"),
        ("idx_bikes_year", "bikes", "year"),
        ("idx_bikes_sub_category", "bikes", "sub_category"),
        ("idx_bikes_brand_id", "bikes", "brand_id"),
        ("idx_bikes_uuid", "bikes", "uuid"),
        
        # Foreign key indexes for joins
        ("idx_bike_listings_bike_id", "bike_listings", "bike_id"),
        ("idx_bike_listings_source_id", "bike_listings", "source_id"),
        ("idx_bike_specs_std_bike_id", "bike_specs_std", "bike_id"),
        ("idx_bike_specs_std_spec_name", "bike_specs_std", "spec_name"),
        ("idx_bike_images_bike_id", "bike_images", "bike_id"),
        ("idx_bike_prices_listing_id", "bike_prices", "listing_id"),
        
        # Brand name for filtering
        ("idx_brands_name", "brands", "name"),
    ]
    
    # Composite indexes
    composite_indexes = [
        ("idx_bikes_category_year", "bikes", ["category", "year"]),
        ("idx_bike_specs_bike_spec", "bike_specs_std", ["bike_id", "spec_name"]),
    ]
    
    # Create single-column indexes
    for index_name, table_name, column_name in indexes:
        try:
            create_query = f"CREATE INDEX {index_name} ON {table_name}({column_name})"
            db.session.execute(db.text(create_query))
            print(f"   ✅ {index_name}")
        except Exception as e:
            # Index might already exist, that's ok
            print(f"   ⏭️  {index_name} (already exists or skipped)")
    
    # Create composite indexes
    for index_name, table_name, columns in composite_indexes:
        try:
            columns_str = ", ".join(columns)
            create_query = f"CREATE INDEX {index_name} ON {table_name}({columns_str})"
            db.session.execute(db.text(create_query))
            print(f"   ✅ {index_name} (composite)")
        except Exception as e:
            print(f"   ⏭️  {index_name} (already exists or skipped)")
    
    db.session.commit()

def create_schema(force=False):
    """Create all database tables"""
    print("🔧 Creating MySQL Database Schema...")
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Import all models to ensure they're registered
        from app.models import (
            User, Brand, Source, Bike, BikeListing, BikePrice,
            BikeSpecRaw, BikeSpecStd, BikeImage, CompareCount, Comparison
        )
        
        print(f"📊 Database URI: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        
        # Drop all tables (WARNING: This will delete all data!)
        if not force:
            print("\n⚠️  WARNING: This will drop all existing tables!")
            response = input("Do you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Aborted.")
                return
        
        print("\n🗑️  Dropping existing tables...")
        db.drop_all()
        
        print("✨ Creating new tables...")
        db.create_all()
        
        print("\n✅ Database schema created successfully!")
        print("\n📋 Created tables:")
        print("   - users")
        print("   - brands")
        print("   - sources")
        print("   - bikes")
        print("   - bike_listings")
        print("   - bike_prices")
        print("   - bike_specs_raw")
        print("   - bike_specs_std")
        print("   - bike_images")
        print("   - compare_counts")
        print("   - comparisons")
        
        # Add performance indexes
        print("\n🚀 Creating performance indexes...")
        add_performance_indexes()
        print("✅ Performance indexes created!")

if __name__ == "__main__":
    force = '--force' in sys.argv or '-f' in sys.argv
    create_schema(force=force)

