#!/usr/bin/env python3
"""
Initialize production database with data from JSON files
This script can be run on PythonAnywhere to recreate the database
"""

import os
import sys
import json
from scripts.db.models import init_db, get_session, Bike, CompareCount
from scripts.db.migrate_to_db import load_json_data_to_db

def init_production_database():
    """Initialize the production database with data from JSON files"""
    
    print("=== INITIALIZING PRODUCTION DATABASE ===\n")
    
    # Initialize database
    init_db()
    db_session = get_session()
    
    try:
        # Check if database already has data
        existing_bikes = db_session.query(Bike).count()
        if existing_bikes > 0:
            print(f"Database already has {existing_bikes} bikes.")
            response = input("Do you want to recreate the database? This will delete all existing data. (y/N): ")
            if response.lower() != 'y':
                print("Aborted.")
                return
        
        # Clear existing data
        print("Clearing existing data...")
        db_session.query(CompareCount).delete()
        db_session.query(Bike).delete()
        db_session.commit()
        
        # Load data from JSON files
        print("Loading data from JSON files...")
        json_files = [
            "data/standardized_data/standardized_cobra.json",
            "data/standardized_data/standardized_ctc.json", 
            "data/standardized_data/standardized_cube.json",
            "data/standardized_data/standardized_giant.json",
            "data/standardized_data/standardized_mazman.json",
            "data/standardized_data/standardized_motofan.json",
            "data/standardized_data/standardized_motosport.json",
            "data/standardized_data/standardized_ofanaim.json",
            "data/standardized_data/standardized_pedalim.json",
            "data/standardized_data/standardized_recycles.json",
            "data/standardized_data/standardized_rosen.json"
        ]
        
        total_bikes = 0
        for json_file in json_files:
            if os.path.exists(json_file):
                print(f"Loading {json_file}...")
                bikes_loaded = load_json_data_to_db(json_file, db_session)
                total_bikes += bikes_loaded
                print(f"Loaded {bikes_loaded} bikes from {json_file}")
            else:
                print(f"Warning: {json_file} not found")
        
        # Initialize some sample compare counts for popular bikes
        print("Initializing sample compare counts...")
        sample_bikes = db_session.query(Bike).limit(20).all()
        for i, bike in enumerate(sample_bikes):
            compare_count = CompareCount(
                bike_id=bike.id,
                count=max(1, 50 - i * 2)  # Decreasing counts for variety
            )
            db_session.add(compare_count)
        
        db_session.commit()
        
        print(f"\n✅ Database initialized successfully!")
        print(f"Total bikes: {total_bikes}")
        print(f"Sample compare counts created for {len(sample_bikes)} bikes")
        
        # Show top bikes that will appear in carousel
        print(f"\nTop bikes that will appear in carousel:")
        top_bikes = db_session.query(CompareCount).join(Bike).order_by(CompareCount.count.desc()).limit(10).all()
        for i, cc in enumerate(top_bikes, 1):
            bike = cc.bike
            print(f"{i}. {bike.firm} {bike.model} ({bike.year}) - Count: {cc.count}")
            
    except Exception as e:
        print(f"Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    init_production_database()

