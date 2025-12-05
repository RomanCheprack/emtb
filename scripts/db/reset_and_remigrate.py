#!/usr/bin/env python3
"""
Script to reset the MySQL database and remigrate all data from scratch.
This will:
1. Drop all existing tables
2. Recreate the schema
3. Import all data from standardized JSON files
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(override=True)

from app import create_app
from app.extensions import db
from app.models import (
    User, Brand, Source, Bike, BikeListing, BikePrice,
    BikeSpecRaw, BikeSpecStd, BikeImage, CompareCount, Comparison
)

def reset_database(app, force=False):
    """Drop all tables and recreate schema"""
    print("\n" + "="*60)
    print("🗑️  RESETTING DATABASE")
    print("="*60)
    
    with app.app_context():
        print("\n⚠️  WARNING: This will DELETE ALL DATA in the database!")
        print(f"   Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        
        if not force:
            response = input("\nAre you sure you want to continue? Type 'YES' to confirm: ")
            if response != 'YES':
                print("❌ Aborted.")
                return False
        else:
            print("\n✅ Force mode enabled, skipping confirmation...")
        
        print("\n🗑️  Dropping all tables...")
        db.drop_all()
        
        print("✨ Creating new tables...")
        db.create_all()
        
        print("\n✅ Database schema reset successfully!")
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
        
        return True


def main():
    """Main function"""
    print("="*60)
    print("🔄 RESET AND REMIGRATE DATABASE")
    print("="*60)
    
    # Check for force flag
    force = '--force' in sys.argv or '-f' in sys.argv
    
    # Create Flask app
    app = create_app()
    
    # Reset database
    if not reset_database(app, force=force):
        return
    
    # Now run the migration
    print("\n" + "="*60)
    print("📦 STARTING MIGRATION")
    print("="*60)
    
    # Import and run the migration
    from migrate_to_mysql import migrate_json_data, main as migrate_main
    
    # Run migration with force flag to skip confirmation
    migrate_main(force=True)


if __name__ == "__main__":
    main()

