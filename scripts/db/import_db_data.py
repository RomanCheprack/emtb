#!/usr/bin/env python3
"""
Import database data from JSON files
This script can be run on PythonAnywhere to recreate the database
"""

import os
import json
from scripts.db.models import init_db, get_session, Bike, CompareCount
from datetime import datetime

def import_database_data():
    """Import database data from JSON files"""
    
    print("=== IMPORTING DATABASE DATA ===\n")
    
    init_db()
    db_session = get_session()
    
    try:
        # Check if export files exist
        bikes_file = "data/export/bikes_export.json"
        compare_counts_file = "data/export/compare_counts_export.json"
        
        if not os.path.exists(bikes_file):
            print(f"Error: {bikes_file} not found!")
            print("Please run export_db_data.py first to create the export files.")
            return
        
        if not os.path.exists(compare_counts_file):
            print(f"Error: {compare_counts_file} not found!")
            print("Please run export_db_data.py first to create the export files.")
            return
        
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
        
        # Import bikes data
        print("Importing bikes data...")
        with open(bikes_file, 'r', encoding='utf-8') as f:
            bikes_data = json.load(f)
        
        for bike_dict in bikes_data:
            bike = Bike(
                id=bike_dict['id'],
                firm=bike_dict['firm'],
                model=bike_dict['model'],
                year=bike_dict['year'],
                price=bike_dict['price'],
                disc_price=bike_dict['disc_price'],
                frame=bike_dict['frame'],
                motor=bike_dict['motor'],
                battery=bike_dict['battery'],
                fork=bike_dict['fork'],
                rear_shock=bike_dict['rear_shock'],
                image_url=bike_dict['image_url'],
                product_url=bike_dict['product_url'],
                stem=bike_dict['stem'],
                handelbar=bike_dict['handelbar'],
                front_brake=bike_dict['front_brake'],
                rear_brake=bike_dict['rear_brake'],
                shifter=bike_dict['shifter'],
                rear_der=bike_dict['rear_der'],
                cassette=bike_dict['cassette'],
                chain=bike_dict['chain'],
                crank_set=bike_dict['crank_set'],
                front_wheel=bike_dict['front_wheel'],
                rear_wheel=bike_dict['rear_wheel'],
                rims=bike_dict['rims'],
                front_axle=bike_dict['front_axle'],
                rear_axle=bike_dict['rear_axle'],
                spokes=bike_dict['spokes'],
                tubes=bike_dict['tubes'],
                front_tire=bike_dict['front_tire'],
                rear_tire=bike_dict['rear_tire'],
                saddle=bike_dict['saddle'],
                seat_post=bike_dict['seat_post'],
                clamp=bike_dict['clamp'],
                charger=bike_dict['charger'],
                wheel_size=bike_dict['wheel_size'],
                headset=bike_dict['headset'],
                brake_lever=bike_dict['brake_lever'],
                screen=bike_dict['screen'],
                extras=bike_dict['extras'],
                pedals=bike_dict['pedals'],
                bb=bike_dict['bb'],
                weight=bike_dict['weight'],
                size=bike_dict['size'],
                hub=bike_dict['hub'],
                brakes=bike_dict['brakes'],
                tires=bike_dict['tires'],
                wh=bike_dict['wh'],
                gallery_images_urls=bike_dict['gallery_images_urls'],
                fork_length=bike_dict['fork_length'],
                sub_category=bike_dict['sub_category'],
                rear_wheel_maxtravel=bike_dict['rear_wheel_maxtravel'],
                battery_capacity=bike_dict['battery_capacity'],
                front_wheel_size=bike_dict['front_wheel_size'],
                rear_wheel_size=bike_dict['rear_wheel_size'],
                battery_watts_per_hour=bike_dict['battery_watts_per_hour'],
            )
            db_session.add(bike)
        
        db_session.commit()
        print(f"Imported {len(bikes_data)} bikes")
        
        # Import compare counts data
        print("Importing compare counts data...")
        with open(compare_counts_file, 'r', encoding='utf-8') as f:
            compare_counts_data = json.load(f)
        
        for cc_dict in compare_counts_data:
            # Parse the last_updated date if it exists
            last_updated = None
            if cc_dict.get('last_updated'):
                try:
                    last_updated = datetime.fromisoformat(cc_dict['last_updated'])
                except:
                    last_updated = datetime.now()
            
            compare_count = CompareCount(
                bike_id=cc_dict['bike_id'],
                count=cc_dict['count'],
                last_updated=last_updated
            )
            db_session.add(compare_count)
        
        db_session.commit()
        print(f"Imported {len(compare_counts_data)} compare counts")
        
        print(f"\n✅ Database import completed successfully!")
        
        # Show top bikes that will appear in carousel
        print(f"\nTop bikes that will appear in carousel:")
        top_bikes = db_session.query(CompareCount).join(Bike).order_by(CompareCount.count.desc()).limit(10).all()
        for i, cc in enumerate(top_bikes, 1):
            bike = cc.bike
            print(f"{i}. {bike.firm} {bike.model} ({bike.year}) - Count: {cc.count}")
            
    except Exception as e:
        print(f"Error importing data: {e}")
        import traceback
        traceback.print_exc()
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    import_database_data()

