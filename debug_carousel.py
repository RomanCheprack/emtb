#!/usr/bin/env python3
"""
Debug script to check carousel data between development and production
"""

import os
import sys
from scripts.db.models import init_db, get_session, Bike, CompareCount
from sqlalchemy import text

def debug_carousel_data():
    """Debug the carousel data to see what's happening"""
    
    print("=== CAROUSEL DEBUG SCRIPT ===\n")
    
    # Initialize database
    init_db()
    db_session = get_session()
    
    try:
        # 1. Check total bikes in database
        total_bikes = db_session.query(Bike).count()
        print(f"1. Total bikes in database: {total_bikes}")
        
        # 2. Check total compare counts
        total_compare_counts = db_session.query(CompareCount).count()
        print(f"2. Total compare counts: {total_compare_counts}")
        
        # 3. Check top 10 most compared bikes
        print("\n3. Top 10 most compared bikes:")
        top_compare_counts = db_session.query(CompareCount).order_by(CompareCount.count.desc()).limit(10).all()
        
        for i, cc in enumerate(top_compare_counts, 1):
            print(f"   {i}. Bike ID: {cc.bike_id}, Count: {cc.count}")
            
            # Check if this bike exists in the bikes table
            bike = db_session.query(Bike).filter_by(id=cc.bike_id).first()
            if bike:
                print(f"      ✓ Found: {bike.firm} {bike.model} ({bike.year})")
            else:
                print(f"      ✗ NOT FOUND in bikes table!")
        
        # 4. Check bikes that exist in both tables (what the carousel should show)
        print("\n4. Bikes that exist in both tables (carousel data):")
        top_bikes_with_data = db_session.query(CompareCount).join(Bike).order_by(CompareCount.count.desc()).limit(10).all()
        
        for i, cc in enumerate(top_bikes_with_data, 1):
            bike = cc.bike
            print(f"   {i}. {bike.firm} {bike.model} ({bike.year}) - Count: {cc.count}")
        
        # 5. Check database file location
        print(f"\n5. Database file location:")
        print(f"   Current working directory: {os.getcwd()}")
        
        # Try to find the database file
        possible_db_paths = [
            "emtb.db",
            "data/emtb.db", 
            "scripts/db/emtb.db",
            "../emtb.db"
        ]
        
        for path in possible_db_paths:
            if os.path.exists(path):
                print(f"   ✓ Found database at: {path}")
                file_size = os.path.getsize(path)
                print(f"     File size: {file_size:,} bytes")
            else:
                print(f"   ✗ Not found: {path}")
        
        # 6. Check environment variables
        print(f"\n6. Environment variables:")
        db_url = os.getenv('DATABASE_URL', 'Not set')
        print(f"   DATABASE_URL: {db_url}")
        
        # 7. Check if we can query the database directly
        print(f"\n7. Database connection test:")
        try:
            result = db_session.execute(text("SELECT COUNT(*) FROM bikes"))
            count = result.scalar()
            print(f"   ✓ Database connection successful: {count} bikes found")
        except Exception as e:
            print(f"   ✗ Database connection failed: {e}")
            
    except Exception as e:
        print(f"Error during debugging: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    debug_carousel_data()
