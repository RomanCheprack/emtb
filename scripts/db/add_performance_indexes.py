"""
Add database indexes for performance optimization

This script adds indexes to improve query performance for common operations:
- Filtering by category
- Filtering by year
- Filtering by sub_category
- Joins with brand, listings, specs, and images
"""

import sys
import os

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app import create_app
from app.extensions import db

def add_indexes():
    """Add performance indexes to the database"""
    app = create_app()
    
    with app.app_context():
        print("🔍 Adding performance indexes to database...")
        
        try:
            # Check if we're using MySQL or SQLite
            engine = db.engine
            dialect = engine.dialect.name
            
            print(f"📊 Database dialect: {dialect}")
            
            # Indexes to create
            indexes = [
                # Basic filtering indexes
                ("idx_bikes_category", "bikes", "category"),
                ("idx_bikes_year", "bikes", "year"),
                ("idx_bikes_sub_category", "bikes", "sub_category"),
                ("idx_bikes_brand_id", "bikes", "brand_id"),
                ("idx_bikes_uuid", "bikes", "uuid"),  # For bike lookups by UUID
                
                # Foreign key indexes for joins
                ("idx_bike_listings_bike_id", "bike_listings", "bike_id"),
                ("idx_bike_listings_source_id", "bike_listings", "source_id"),
                ("idx_bike_specs_std_bike_id", "bike_specs_std", "bike_id"),
                ("idx_bike_specs_std_spec_name", "bike_specs_std", "spec_name"),  # For spec filtering
                ("idx_bike_images_bike_id", "bike_images", "bike_id"),
                ("idx_bike_prices_listing_id", "bike_prices", "listing_id"),
                
                # Brand name for filtering
                ("idx_brands_name", "brands", "name"),
            ]
            
            # Composite indexes for common query patterns
            composite_indexes = [
                ("idx_bikes_category_year", "bikes", ["category", "year"]),
                ("idx_bike_specs_bike_spec", "bike_specs_std", ["bike_id", "spec_name"]),  # For spec lookups
            ]
            
            # Create single-column indexes
            for index_name, table_name, column_name in indexes:
                try:
                    # Check if index exists
                    check_query = f"""
                    SELECT COUNT(*) 
                    FROM information_schema.statistics 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{table_name}' 
                    AND index_name = '{index_name}'
                    """ if dialect == 'mysql' else f"""
                    SELECT COUNT(*) 
                    FROM sqlite_master 
                    WHERE type='index' 
                    AND name='{index_name}'
                    """
                    
                    result = db.session.execute(db.text(check_query))
                    exists = result.scalar() > 0
                    
                    if exists:
                        print(f"  ⏭️  Index {index_name} already exists, skipping...")
                        continue
                    
                    # Create index
                    create_query = f"CREATE INDEX {index_name} ON {table_name}({column_name})"
                    db.session.execute(db.text(create_query))
                    print(f"  ✅ Created index: {index_name} on {table_name}({column_name})")
                    
                except Exception as e:
                    print(f"  ⚠️  Warning: Could not create index {index_name}: {e}")
                    continue
            
            # Create composite indexes
            for index_name, table_name, columns in composite_indexes:
                try:
                    # Check if index exists
                    check_query = f"""
                    SELECT COUNT(*) 
                    FROM information_schema.statistics 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{table_name}' 
                    AND index_name = '{index_name}'
                    """ if dialect == 'mysql' else f"""
                    SELECT COUNT(*) 
                    FROM sqlite_master 
                    WHERE type='index' 
                    AND name='{index_name}'
                    """
                    
                    result = db.session.execute(db.text(check_query))
                    exists = result.scalar() > 0
                    
                    if exists:
                        print(f"  ⏭️  Index {index_name} already exists, skipping...")
                        continue
                    
                    # Create composite index
                    columns_str = ", ".join(columns)
                    create_query = f"CREATE INDEX {index_name} ON {table_name}({columns_str})"
                    db.session.execute(db.text(create_query))
                    print(f"  ✅ Created composite index: {index_name} on {table_name}({columns_str})")
                    
                except Exception as e:
                    print(f"  ⚠️  Warning: Could not create index {index_name}: {e}")
                    continue
            
            # Commit all changes
            db.session.commit()
            print("\n✅ Successfully added all possible indexes!")
            print("💡 Note: Some indexes may have been skipped if they already existed or couldn't be created")
            
        except Exception as e:
            print(f"\n❌ Error adding indexes: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == "__main__":
    print("=" * 60)
    print("Database Performance Optimization")
    print("Adding indexes for improved query performance")
    print("=" * 60)
    print()
    
    success = add_indexes()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Index optimization complete!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Index optimization failed!")
        print("=" * 60)
        sys.exit(1)

