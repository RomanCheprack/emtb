#!/usr/bin/env python3
"""
Script to check for duplicate bikes in the database
"""

import sys
import os
from collections import defaultdict

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db
from app.models import Bike, Brand, BikeListing

def check_duplicates():
    """Check for duplicate bikes in various ways"""
    print("=" * 80)
    print("🔍 CHECKING FOR DUPLICATES IN DATABASE")
    print("=" * 80)
    
    load_dotenv(override=True)
    app = create_app()
    
    with app.app_context():
        all_bikes = Bike.query.all()
        print(f"\n📊 Total bikes in database: {len(all_bikes)}")
        
        # Check 1: Duplicates by (brand, model, year)
        print("\n" + "=" * 80)
        print("CHECK 1: Duplicates by (Brand, Model, Year)")
        print("=" * 80)
        
        brand_model_year_map = defaultdict(list)
        for bike in all_bikes:
            brand_name = bike.brand.name if bike.brand else "NO_BRAND"
            key = (brand_name, bike.model, bike.year)
            brand_model_year_map[key].append(bike)
        
        duplicates_found_1 = []
        for key, bikes in brand_model_year_map.items():
            if len(bikes) > 1:
                duplicates_found_1.append((key, bikes))
        
        if duplicates_found_1:
            print(f"\n⚠️  Found {len(duplicates_found_1)} groups of duplicates:")
            for key, bikes in duplicates_found_1:
                brand, model, year = key
                print(f"\n  🔴 {brand} {model} ({year})")
                for bike in bikes:
                    print(f"     - ID: {bike.id}, UUID: {bike.uuid}, Slug: {bike.slug}")
                    print(f"       Created: {bike.created_at}")
                    print(f"       Listings: {len(bike.listings)}")
        else:
            print("✅ No duplicates found by (Brand, Model, Year)")
        
        # Check 2: Duplicates by slug
        print("\n" + "=" * 80)
        print("CHECK 2: Duplicates by Slug")
        print("=" * 80)
        
        slug_map = defaultdict(list)
        for bike in all_bikes:
            if bike.slug:
                slug_map[bike.slug].append(bike)
        
        duplicates_found_2 = []
        for slug, bikes in slug_map.items():
            if len(bikes) > 1:
                duplicates_found_2.append((slug, bikes))
        
        if duplicates_found_2:
            print(f"\n⚠️  Found {len(duplicates_found_2)} duplicate slugs:")
            for slug, bikes in duplicates_found_2:
                print(f"\n  🔴 Slug: {slug}")
                for bike in bikes:
                    brand_name = bike.brand.name if bike.brand else "NO_BRAND"
                    print(f"     - ID: {bike.id}, {brand_name} {bike.model} ({bike.year})")
        else:
            print("✅ No duplicate slugs found")
        
        # Check 3: Bikes with duplicate product URLs across listings
        print("\n" + "=" * 80)
        print("CHECK 3: Duplicate Product URLs")
        print("=" * 80)
        
        all_listings = BikeListing.query.all()
        url_to_bikes = defaultdict(set)
        for listing in all_listings:
            if listing.product_url:
                url_to_bikes[listing.product_url].add(listing.bike_id)
        
        duplicates_found_3 = []
        for url, bike_ids in url_to_bikes.items():
            if len(bike_ids) > 1:
                duplicates_found_3.append((url, bike_ids))
        
        if duplicates_found_3:
            print(f"\n⚠️  Found {len(duplicates_found_3)} product URLs linked to multiple bikes:")
            for url, bike_ids in duplicates_found_3[:10]:  # Show first 10
                print(f"\n  🔴 URL: {url[:80]}...")
                for bike_id in bike_ids:
                    bike = Bike.query.get(bike_id)
                    brand_name = bike.brand.name if bike.brand else "NO_BRAND"
                    print(f"     - Bike ID: {bike_id}, {brand_name} {bike.model} ({bike.year})")
            if len(duplicates_found_3) > 10:
                print(f"\n  ... and {len(duplicates_found_3) - 10} more")
        else:
            print("✅ No duplicate product URLs found")
        
        # Check 4: Very similar models (same brand, similar model name)
        print("\n" + "=" * 80)
        print("CHECK 4: Potentially Similar Bikes (Same Brand, Very Similar Model)")
        print("=" * 80)
        
        brand_bikes = defaultdict(list)
        for bike in all_bikes:
            brand_name = bike.brand.name if bike.brand else "NO_BRAND"
            brand_bikes[brand_name].append(bike)
        
        similar_count = 0
        for brand_name, bikes in brand_bikes.items():
            # Group by normalized model name
            normalized_models = defaultdict(list)
            for bike in bikes:
                if bike.model:
                    # Normalize: lowercase, remove special chars, collapse spaces
                    normalized = bike.model.lower().replace('-', '').replace(' ', '').strip()
                    normalized_models[normalized].append(bike)
            
            for normalized, bike_list in normalized_models.items():
                if len(bike_list) > 1:
                    # Check if they're actually different (different years are OK)
                    years = set(b.year for b in bike_list)
                    if len(bike_list) > len(years):  # More bikes than unique years
                        similar_count += 1
                        print(f"\n  🟡 {brand_name} - Normalized: '{normalized}'")
                        for bike in bike_list:
                            print(f"     - ID: {bike.id}, Model: '{bike.model}', Year: {bike.year}")
        
        if similar_count == 0:
            print("✅ No suspicious similar bikes found")
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"Total bikes: {len(all_bikes)}")
        print(f"Duplicates by (Brand, Model, Year): {len(duplicates_found_1)} groups")
        print(f"Duplicates by Slug: {len(duplicates_found_2)} groups")
        print(f"Duplicate Product URLs: {len(duplicates_found_3)}")
        print(f"Potentially similar bikes: {similar_count}")
        
        if duplicates_found_1 or duplicates_found_2 or duplicates_found_3:
            print("\n⚠️  DUPLICATES DETECTED - Review above for details")
        else:
            print("\n✅ No duplicates detected!")

if __name__ == "__main__":
    check_duplicates()



