#!/usr/bin/env python3
"""
Simple script to create the bike_variants table.
This script will NOT drop existing tables - it only creates the new one if it doesn't exist.

Usage:
    python scripts/db/create_bike_variants_table.py
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db


def create_bike_variants_table():
    """Create the bike_variants table"""
    print("=" * 60)
    print("🔧 Creating Bike Variants Table")
    print("=" * 60)

    load_dotenv(override=True)

    app = create_app()

    with app.app_context():
        # Import the model to ensure it's registered
        from app.models import BikeVariant  # noqa: F401

        print(f"\n📊 Database URI: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")

        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        if 'bike_variants' in existing_tables:
            print("\n✅ Table 'bike_variants' already exists")
            print("=" * 60)
            return

        print("\n✨ Creating new table 'bike_variants'...")

        # SQLAlchemy will only create tables that don't exist yet.
        db.create_all()

        print("\n✅ Table created successfully!")
        print("\n📋 Created table:")
        print("   - bike_variants")
        print("\n📝 Table structure:")
        print("   - id (BigInteger, Primary Key)")
        print("   - bike_id (BigInteger, FK -> bikes.id, CASCADE)")
        print("   - listing_id (BigInteger, FK -> bike_listings.id, CASCADE, nullable)")
        print("   - color_id (String 64, nullable)")
        print("   - color_label (String 255, nullable)")
        print("   - size_label (String 64, nullable)")
        print("   - sku (String 128, nullable)")
        print("   - stock (Integer, nullable)")
        print("   - in_stock (Boolean, default False)")
        print("   - is_default_color (Boolean, default False)")
        print("   - image_url (String 500, nullable)")
        print("   - gallery_json (Text, nullable)")
        print("   - position (Integer, default 0)")
        print("   - updated_at (DateTime)")
        print("   - Unique: (bike_id, color_id, size_label)")
        print("   - Index: bike_id; (bike_id, in_stock)")

        print("\n" + "=" * 60)
        print("✅ Done!")
        print("=" * 60)


if __name__ == "__main__":
    create_bike_variants_table()
