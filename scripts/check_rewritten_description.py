#!/usr/bin/env python3
"""
Check if rewritten_description exists in database for a specific bike
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db
from app.models import Bike, BikeListing, BikeSpecRaw

def check_rewritten_description(brand_name, model_name):
    """Check if rewritten_description exists for a bike"""
    load_dotenv(override=True)
    app = create_app()
    
    with app.app_context():
        # Find the bike
        bike = db.session.query(Bike).join(Bike.brand).filter(
            Bike.brand.has(name=brand_name),
            Bike.model == model_name
        ).first()
        
        if not bike:
            print(f"❌ Bike not found: {brand_name} {model_name}")
            return
        
        print(f"✅ Found bike: {brand_name} {model_name}")
        print(f"   UUID: {bike.uuid}")
        print(f"   ID: {bike.id}")
        print(f"   Description field: {bike.description}")
        print()
        
        # Check raw_specs
        if bike.listings:
            print(f"📋 Found {len(bike.listings)} listing(s)")
            for i, listing in enumerate(bike.listings):
                print(f"\n   Listing {i+1}:")
                print(f"   - Listing ID: {listing.id}")
                print(f"   - Product URL: {listing.product_url}")
                
                if listing.raw_specs:
                    print(f"   - Raw specs count: {len(listing.raw_specs)}")
                    
                    # Check for rewritten_description
                    found_rewritten = False
                    for raw_spec in listing.raw_specs:
                        if raw_spec.spec_key_raw.lower().strip() in ['rewritten_description', 'rewritten description']:
                            print(f"   ✅ Found rewritten_description in raw_specs:")
                            print(f"      Key: {raw_spec.spec_key_raw}")
                            print(f"      Value: {raw_spec.spec_value_raw[:200]}..." if len(raw_spec.spec_value_raw) > 200 else f"      Value: {raw_spec.spec_value_raw}")
                            found_rewritten = True
                            break
                    
                    if not found_rewritten:
                        print(f"   ❌ rewritten_description NOT found in raw_specs")
                        print(f"   Available keys (first 10):")
                        for spec in listing.raw_specs[:10]:
                            print(f"      - {spec.spec_key_raw}")
                else:
                    print(f"   ❌ No raw_specs found for this listing")
        else:
            print(f"❌ No listings found for this bike")

if __name__ == "__main__":
    check_rewritten_description("Trek", "Madone SL 5 Gen 8")

