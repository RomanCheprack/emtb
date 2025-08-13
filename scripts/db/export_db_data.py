#!/usr/bin/env python3
"""
Export database data to JSON files for deployment
This creates JSON files that can be safely committed to Git
"""

import os
import json
from datetime import datetime
from scripts.db.models import init_db, get_session, Bike, CompareCount

def export_database_data():
    """Export database data to JSON files"""
    
    print("=== EXPORTING DATABASE DATA ===\n")
    
    init_db()
    db_session = get_session()
    
    try:
        # Export bikes data
        print("Exporting bikes data...")
        bikes = db_session.query(Bike).all()
        bikes_data = []
        
        for bike in bikes:
            bike_dict = {
                'id': bike.id,
                'firm': bike.firm,
                'model': bike.model,
                'year': bike.year,
                'price': bike.price,
                'disc_price': bike.disc_price,
                'frame': bike.frame,
                'motor': bike.motor,
                'battery': bike.battery,
                'fork': bike.fork,
                'rear_shock': bike.rear_shock,
                'image_url': bike.image_url,
                'product_url': bike.product_url,
                'stem': bike.stem,
                'handelbar': bike.handelbar,
                'front_brake': bike.front_brake,
                'rear_brake': bike.rear_brake,
                'shifter': bike.shifter,
                'rear_der': bike.rear_der,
                'cassette': bike.cassette,
                'chain': bike.chain,
                'crank_set': bike.crank_set,
                'front_wheel': bike.front_wheel,
                'rear_wheel': bike.rear_wheel,
                'rims': bike.rims,
                'front_axle': bike.front_axle,
                'rear_axle': bike.rear_axle,
                'spokes': bike.spokes,
                'tubes': bike.tubes,
                'front_tire': bike.front_tire,
                'rear_tire': bike.rear_tire,
                'saddle': bike.saddle,
                'seat_post': bike.seat_post,
                'clamp': bike.clamp,
                'charger': bike.charger,
                'wheel_size': bike.wheel_size,
                'headset': bike.headset,
                'brake_lever': bike.brake_lever,
                'screen': bike.screen,
                'extras': bike.extras,
                'pedals': bike.pedals,
                'bb': bike.bb,
                'weight': bike.weight,
                'size': bike.size,
                'hub': bike.hub,
                'brakes': bike.brakes,
                'tires': bike.tires,
                'wh': bike.wh,
                'gallery_images_urls': bike.gallery_images_urls,
                'fork_length': bike.fork_length,
                'sub_category': bike.sub_category,
                'rear_wheel_maxtravel': bike.rear_wheel_maxtravel,
                'battery_capacity': bike.battery_capacity,
                'front_wheel_size': bike.front_wheel_size,
                'rear_wheel_size': bike.rear_wheel_size,
                'battery_watts_per_hour': bike.battery_watts_per_hour,
            }
            bikes_data.append(bike_dict)
        
        # Export compare counts data
        print("Exporting compare counts data...")
        compare_counts = db_session.query(CompareCount).all()
        compare_counts_data = []
        
        for cc in compare_counts:
            cc_dict = {
                'bike_id': cc.bike_id,
                'count': cc.count,
                'last_updated': cc.last_updated.isoformat() if cc.last_updated else None
            }
            compare_counts_data.append(cc_dict)
        
        # Create export directory
        export_dir = "data/export"
        os.makedirs(export_dir, exist_ok=True)
        
        # Save bikes data
        bikes_file = os.path.join(export_dir, "bikes_export.json")
        with open(bikes_file, 'w', encoding='utf-8') as f:
            json.dump(bikes_data, f, ensure_ascii=False, indent=2)
        
        # Save compare counts data
        compare_counts_file = os.path.join(export_dir, "compare_counts_export.json")
        with open(compare_counts_file, 'w', encoding='utf-8') as f:
            json.dump(compare_counts_data, f, ensure_ascii=False, indent=2)
        
        # Create metadata file
        metadata = {
            'export_date': datetime.now().isoformat(),
            'total_bikes': len(bikes_data),
            'total_compare_counts': len(compare_counts_data),
            'files': {
                'bikes': bikes_file,
                'compare_counts': compare_counts_file
            }
        }
        
        metadata_file = os.path.join(export_dir, "export_metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Export completed successfully!")
        print(f"Total bikes exported: {len(bikes_data)}")
        print(f"Total compare counts exported: {len(compare_counts_data)}")
        print(f"Files saved to: {export_dir}")
        
        # Show top bikes that will be in carousel
        print(f"\nTop bikes that will appear in carousel:")
        top_bikes = db_session.query(CompareCount).join(Bike).order_by(CompareCount.count.desc()).limit(10).all()
        for i, cc in enumerate(top_bikes, 1):
            bike = cc.bike
            print(f"{i}. {bike.firm} {bike.model} ({bike.year}) - Count: {cc.count}")
            
    except Exception as e:
        print(f"Error exporting data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    export_database_data()

