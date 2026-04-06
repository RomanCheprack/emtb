#!/usr/bin/env python3
"""
Drop all bike-related data from the database while preserving user data.

This script drops:
- purchase_clicks (purchase analytics; references bikes)
- bikes
- bike_listings
- bike_prices
- bike_specs_raw
- bike_specs_std
- bike_images

This script preserves:
- users
- comparisons
- brands
- sources
- compare_counts

Uses transactions for safe rollback on failure.
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db
from app.models import (
    User, Brand, Source, Bike, BikeListing, BikePrice,
    BikeSpecRaw, BikeSpecStd, BikeImage, CompareCount, Comparison, PurchaseClick,
)
from sqlalchemy import text, inspect


def _purchase_clicks_table_exists():
    return "purchase_clicks" in inspect(db.engine).get_table_names()


def get_table_counts(app):
    """Get current counts for all tables"""
    with app.app_context():
        counts = {
            'users': User.query.count(),
            'comparisons': Comparison.query.count(),
            'brands': Brand.query.count(),
            'sources': Source.query.count(),
            'bikes': Bike.query.count(),
            'bike_listings': BikeListing.query.count(),
            'bike_prices': BikePrice.query.count(),
            'bike_specs_raw': BikeSpecRaw.query.count(),
            'bike_specs_std': BikeSpecStd.query.count(),
            'bike_images': BikeImage.query.count(),
            'compare_counts': CompareCount.query.count(),
            'purchase_clicks': PurchaseClick.query.count() if _purchase_clicks_table_exists() else 0,
        }
        return counts


def drop_bike_data(app, dry_run=False):
    """
    Drop all bike-related data from database.
    
    Deletion order (respecting foreign key constraints):
    1. bike_images (references bikes, sources)
    2. bike_specs_std (references bikes)
    3. bike_specs_raw (references bike_listings)
    4. bike_prices (references bike_listings)
    5. bike_listings (references bikes, sources)
    6. bikes (references brands)
    
    Note: compare_counts references bikes but is preserved.
    After migration, compare_counts will need to be updated to reference new bike IDs.
    
    Preserves: users, comparisons, brands, sources, compare_counts
    """
    print("\n" + "=" * 80)
    print("🗑️  DROPPING BIKE DATA")
    print("=" * 80)
    
    with app.app_context():
        # Show current counts
        print("\n📊 Current database counts:")
        counts_before = get_table_counts(app)
        print(f"   Users: {counts_before['users']}")
        print(f"   Comparisons: {counts_before['comparisons']}")
        print(f"   Brands: {counts_before['brands']}")
        print(f"   Sources: {counts_before['sources']}")
        print(f"   Bikes: {counts_before['bikes']}")
        print(f"   Bike Listings: {counts_before['bike_listings']}")
        print(f"   Bike Prices: {counts_before['bike_prices']}")
        print(f"   Bike Specs (Raw): {counts_before['bike_specs_raw']}")
        print(f"   Bike Specs (Std): {counts_before['bike_specs_std']}")
        print(f"   Bike Images: {counts_before['bike_images']}")
        print(f"   Compare Counts: {counts_before['compare_counts']} (preserved)")
        print(f"   Purchase clicks: {counts_before['purchase_clicks']}")
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - No data will be deleted")
            print("\nWould delete:")
            print(f"   - {counts_before['bike_images']} bike images")
            print(f"   - {counts_before['bike_specs_std']} standardized specs")
            print(f"   - {counts_before['bike_specs_raw']} raw specs")
            print(f"   - {counts_before['bike_prices']} prices")
            print(f"   - {counts_before['bike_listings']} listings")
            print(f"   - {counts_before['purchase_clicks']} purchase clicks")
            print(f"   (Compare counts will be preserved)")
            print(f"   - {counts_before['bikes']} bikes")
            return True
        
        # Start transaction
        print("\n🗑️  Starting deletion (in transaction)...")
        
        try:
            # Disable foreign key checks temporarily (MySQL specific)
            # This allows us to delete in any order
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            deleted_counts = {}
            
            # 1. Delete purchase_clicks (references bikes)
            print("   1. Deleting purchase clicks...")
            if _purchase_clicks_table_exists():
                deleted = PurchaseClick.query.delete()
                deleted_counts['purchase_clicks'] = deleted
                print(f"      ✅ Deleted {deleted} purchase click rows")
            else:
                deleted_counts['purchase_clicks'] = 0
                print("      ⏭️  Table purchase_clicks does not exist (skipped)")
            db.session.flush()
            
            # 2. Delete bike_images
            print("   2. Deleting bike images...")
            deleted = BikeImage.query.delete()
            deleted_counts['bike_images'] = deleted
            print(f"      ✅ Deleted {deleted} bike images")
            db.session.flush()
            
            # 3. Delete bike_specs_std
            print("   3. Deleting standardized specs...")
            deleted = BikeSpecStd.query.delete()
            deleted_counts['bike_specs_std'] = deleted
            print(f"      ✅ Deleted {deleted} standardized specs")
            db.session.flush()
            
            # 4. Delete bike_specs_raw
            print("   4. Deleting raw specs...")
            deleted = BikeSpecRaw.query.delete()
            deleted_counts['bike_specs_raw'] = deleted
            print(f"      ✅ Deleted {deleted} raw specs")
            db.session.flush()
            
            # 5. Delete bike_prices
            print("   5. Deleting bike prices...")
            deleted = BikePrice.query.delete()
            deleted_counts['bike_prices'] = deleted
            print(f"      ✅ Deleted {deleted} prices")
            db.session.flush()
            
            # 6. Delete bike_listings (compare_counts preserved - will be orphaned but kept)
            print("   6. Deleting bike listings...")
            deleted = BikeListing.query.delete()
            deleted_counts['bike_listings'] = deleted
            print(f"      ✅ Deleted {deleted} listings")
            db.session.flush()
            
            # 7. Delete bikes (compare_counts has FK with CASCADE, but we preserve it by disabling FK checks)
            print("   7. Deleting bikes...")
            print("      ⚠️  Note: compare_counts will be orphaned (FK references will be invalid)")
            print("      ⚠️  After migration, compare_counts will need to be updated to match new bike IDs")
            deleted = Bike.query.delete()
            deleted_counts['bikes'] = deleted
            print(f"      ✅ Deleted {deleted} bikes")
            db.session.flush()
            
            # Re-enable foreign key checks
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            
            # Commit transaction
            db.session.commit()
            print("\n✅ All bike data deleted successfully!")
            
            # Show final counts
            print("\n📊 Final database counts:")
            counts_after = get_table_counts(app)
            print(f"   Users: {counts_after['users']} (preserved)")
            print(f"   Comparisons: {counts_after['comparisons']} (preserved)")
            print(f"   Brands: {counts_after['brands']} (preserved)")
            print(f"   Sources: {counts_after['sources']} (preserved)")
            print(f"   Bikes: {counts_after['bikes']} (deleted)")
            print(f"   Bike Listings: {counts_after['bike_listings']} (deleted)")
            print(f"   Bike Prices: {counts_after['bike_prices']} (deleted)")
            print(f"   Bike Specs (Raw): {counts_after['bike_specs_raw']} (deleted)")
            print(f"   Bike Specs (Std): {counts_after['bike_specs_std']} (deleted)")
            print(f"   Bike Images: {counts_after['bike_images']} (deleted)")
            print(f"   Compare Counts: {counts_after['compare_counts']} (preserved)")
            print(f"   Purchase clicks: {counts_after['purchase_clicks']} (deleted)")
            
            return True
            
        except Exception as e:
            # Rollback on error
            db.session.rollback()
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))  # Re-enable even on error
            print(f"\n❌ Error during deletion: {e}")
            print("   Transaction rolled back - no data was deleted")
            import traceback
            traceback.print_exc()
            return False


def recreate_bike_prices_table(app, force=False):
    """Drop and recreate bike_prices table with updated schema"""
    print("\n" + "=" * 80)
    print("🔧 RECREATING BIKE_PRICES TABLE")
    print("=" * 80)
    
    with app.app_context():
        if not force:
            print("\n⚠️  WARNING: This will drop and recreate the bike_prices table!")
            print("   All price data will be lost!")
            response = input("Do you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Aborted.")
                return False
        
        try:
            # Drop the table
            print("\n🗑️  Dropping bike_prices table...")
            db.session.execute(text("DROP TABLE IF EXISTS bike_prices"))
            db.session.commit()
            print("   ✅ Table dropped")
            
            # Recreate the table using SQLAlchemy (will use current model definition)
            print("✨ Creating bike_prices table with new schema...")
            from app.models import BikePrice
            BikePrice.__table__.create(db.engine)
            print("   ✅ Table created with columns: original_price, disc_price")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error recreating table: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Drop all bike-related data from database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--recreate-prices-table', action='store_true', 
                       help='Drop and recreate bike_prices table with updated schema')
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("🗑️  DROP BIKE DATA SCRIPT")
        print("=" * 80)
        print(f"\n📊 Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        
        # Check if database has tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if not tables:
            print("\n❌ No tables found in database!")
            return
        
        print(f"\n✅ Found {len(tables)} tables in database")
        
        # Handle recreate prices table option
        if args.recreate_prices_table:
            success = recreate_bike_prices_table(app, force=args.force)
            if success:
                print("\n✅ bike_prices table recreated with new schema!")
                print("   Columns: original_price, disc_price (replaced price_ils)")
            else:
                print("\n❌ Failed to recreate bike_prices table!")
                sys.exit(1)
            return
        
        # Confirmation (unless --force or --dry-run)
        if not args.force and not args.dry_run:
            print("\n⚠️  WARNING: This will DELETE ALL bike-related data!")
            print("   Preserved: users, comparisons, brands, sources, compare_counts")
            print("   Deleted: purchase_clicks, bikes, listings, prices, specs, images")
            response = input("\nDo you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Aborted.")
                return
        
        # Drop bike data
        success = drop_bike_data(app, dry_run=args.dry_run)
        
        if success:
            if args.dry_run:
                print("\n💡 To actually delete data, run without --dry-run flag")
            else:
                print("\n✅ Bike data deletion complete!")
        else:
            print("\n❌ Bike data deletion failed!")
            sys.exit(1)


if __name__ == "__main__":
    main()

