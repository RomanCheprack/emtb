#!/usr/bin/env python3
"""
Update existing bikes with rewritten_description from JSON files
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db
from app.models import Bike, Brand, BikeListing, BikeSpecRaw

def update_rewritten_descriptions():
    """Update bikes with rewritten_description from JSON files"""
    load_dotenv(override=True)
    app = create_app()
    
    # Find all standardized JSON files
    json_dir = Path(project_root) / "data" / "standardized_data"
    json_files = list(json_dir.glob("standardized_*.json"))
    
    if not json_files:
        print("❌ No standardized JSON files found")
        return
    
    print(f"📂 Found {len(json_files)} JSON file(s)")
    
    with app.app_context():
        updated_count = 0
        not_found_count = 0
        
        for json_file in json_files:
            print(f"\n📄 Processing {json_file.name}...")
            
            with open(json_file, 'r', encoding='utf-8') as f:
                bikes_data = json.load(f)
            
            for bike_data in bikes_data:
                firm = bike_data.get('firm')
                model = bike_data.get('model')
                rewritten_desc_raw = bike_data.get('rewritten_description')
                rewritten_desc = rewritten_desc_raw.strip() if rewritten_desc_raw and isinstance(rewritten_desc_raw, str) else None
                
                if not firm or not model or not rewritten_desc:
                    continue
                
                # Find the bike in database
                bike = db.session.query(Bike).join(Bike.brand).filter(
                    Bike.brand.has(name=firm),
                    Bike.model == model
                ).first()
                
                if not bike:
                    not_found_count += 1
                    continue
                
                # Update bike.description if it's empty or different
                if not bike.description or bike.description.strip() != rewritten_desc:
                    bike.description = rewritten_desc
                    updated_count += 1
                    print(f"   ✅ Updated: {firm} {model}")
                
                # Also add to raw_specs if not present
                if bike.listings:
                    listing = bike.listings[0]  # Use first listing
                    existing_spec = db.session.query(BikeSpecRaw).filter_by(
                        listing_id=listing.id,
                        spec_key_raw='rewritten_description'
                    ).first()
                    
                    if not existing_spec:
                        raw_spec = BikeSpecRaw(
                            listing_id=listing.id,
                            spec_key_raw='rewritten_description',
                            spec_value_raw=rewritten_desc,
                            scraped_at=db.session.query(BikeSpecRaw).filter_by(
                                listing_id=listing.id
                            ).first().scraped_at if listing.raw_specs else None
                        )
                        db.session.add(raw_spec)
                        print(f"   ✅ Added to raw_specs: {firm} {model}")
        
        # Commit all changes
        if updated_count > 0:
            db.session.commit()
            print(f"\n✅ Updated {updated_count} bike(s) with rewritten_description")
        else:
            print(f"\n⚠️  No bikes needed updating")
        
        if not_found_count > 0:
            print(f"⚠️  {not_found_count} bike(s) from JSON not found in database")

if __name__ == "__main__":
    update_rewritten_descriptions()

