#!/usr/bin/env python3
"""
Diagnostic script to understand differences in migration results between environments.

This script helps identify:
1. Number of files being processed
2. Number of bikes in each file
3. Potential errors or data quality issues
4. Database state before migration
"""

import sys
import os
import json
from collections import defaultdict

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db
from app.models import (
    Brand, Source, Bike, BikeListing, BikePrice,
    BikeSpecStd, BikeImage, Comparison
)


def analyze_json_files():
    """Analyze JSON files in standardized_data directory"""
    print("\n" + "="*60)
    print("📄 ANALYZING STANDARDIZED JSON FILES")
    print("="*60)
    
    json_dir = os.path.join(project_root, 'data', 'standardized_data')
    
    if not os.path.exists(json_dir):
        print(f"❌ JSON directory not found at {json_dir}")
        return
    
    json_files = [f for f in os.listdir(json_dir) 
                  if f.startswith('standardized_') and f.endswith('.json')
                  and f != 'all_bikes_standardized.json']
    
    print(f"\nFound {len(json_files)} JSON files to process\n")
    
    total_bikes = 0
    file_stats = []
    
    for json_file in sorted(json_files):
        json_path = os.path.join(json_dir, json_file)
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                bikes_data = json.load(f)
            
            bike_count = len(bikes_data) if isinstance(bikes_data, list) else 1
            total_bikes += bike_count
            
            # Count bikes with missing required fields
            missing_model = 0
            missing_brand = 0
            invalid_model_length = 0
            invalid_year = 0
            
            for bike_data in (bikes_data if isinstance(bikes_data, list) else [bikes_data]):
                model = bike_data.get('model', '').strip() if bike_data.get('model') else None
                if not model or len(model) == 0:
                    missing_model += 1
                elif len(model) > 255:
                    invalid_model_length += 1
                
                if not bike_data.get('firm'):
                    missing_brand += 1
                
                year = bike_data.get('year')
                if year:
                    try:
                        year_int = int(year) if isinstance(year, str) else year
                        if not (1900 <= year_int <= 2100):
                            invalid_year += 1
                    except:
                        invalid_year += 1
            
            file_stats.append({
                'file': json_file,
                'bikes': bike_count,
                'missing_model': missing_model,
                'missing_brand': missing_brand,
                'invalid_model_length': invalid_model_length,
                'invalid_year': invalid_year
            })
            
            print(f"  {json_file}:")
            print(f"    Bikes: {bike_count}")
            if missing_model > 0:
                print(f"    ⚠️  Missing model: {missing_model}")
            if missing_brand > 0:
                print(f"    ⚠️  Missing brand: {missing_brand}")
            if invalid_model_length > 0:
                print(f"    ⚠️  Model too long (>255 chars): {invalid_model_length}")
            if invalid_year > 0:
                print(f"    ⚠️  Invalid year: {invalid_year}")
        
        except Exception as e:
            print(f"  ❌ Error reading {json_file}: {e}")
            file_stats.append({
                'file': json_file,
                'bikes': 0,
                'error': str(e)
            })
    
    print(f"\n📊 Total bikes in JSON files: {total_bikes}")
    
    return file_stats, total_bikes


def analyze_database_state(app):
    """Analyze current database state"""
    print("\n" + "="*60)
    print("🗄️  ANALYZING DATABASE STATE")
    print("="*60)
    
    with app.app_context():
        brands_count = Brand.query.count()
        sources_count = Source.query.count()
        bikes_count = Bike.query.count()
        listings_count = BikeListing.query.count()
        prices_count = BikePrice.query.count()
        specs_count = BikeSpecStd.query.count()
        images_count = BikeImage.query.count()
        comparisons_count = Comparison.query.count()
        
        print(f"\n📊 Current Database Statistics:")
        print(f"   Brands: {brands_count}")
        print(f"   Sources: {sources_count}")
        print(f"   Bikes: {bikes_count}")
        print(f"   Listings: {listings_count}")
        print(f"   Prices: {prices_count}")
        print(f"   Specs: {specs_count}")
        print(f"   Images: {images_count}")
        print(f"   Comparisons: {comparisons_count}")
        
        if bikes_count > 0:
            print(f"\n⚠️  WARNING: Database already contains {bikes_count} bikes!")
            print(f"   Running migration will skip these as duplicates.")
            print(f"   If you want a fresh migration, drop the database first.")
        
        # Count bikes by source
        if sources_count > 0:
            print(f"\n📋 Bikes by source:")
            sources = Source.query.all()
            for source in sources:
                listings = BikeListing.query.filter_by(source_id=source.id).count()
                print(f"   {source.importer} ({source.domain}): {listings} listings")
        
        # Count bikes by brand
        if brands_count > 0:
            print(f"\n📋 Top 10 brands by bike count:")
            from sqlalchemy import func
            brand_counts = db.session.query(
                Brand.name,
                func.count(Bike.id).label('count')
            ).join(Bike, Brand.id == Bike.brand_id).group_by(Brand.name).order_by(func.count(Bike.id).desc()).limit(10).all()
            
            for brand_name, count in brand_counts:
                print(f"   {brand_name}: {count} bikes")
    
    return {
        'brands': brands_count,
        'sources': sources_count,
        'bikes': bikes_count,
        'listings': listings_count,
        'prices': prices_count,
        'specs': specs_count,
        'images': images_count,
        'comparisons': comparisons_count
    }


def check_duplicate_slugs_in_files():
    """Check for potential duplicate slugs within JSON files"""
    print("\n" + "="*60)
    print("🔍 CHECKING FOR DUPLICATE SLUGS IN FILES")
    print("="*60)
    
    json_dir = os.path.join(project_root, 'data', 'standardized_data')
    json_files = [f for f in os.listdir(json_dir) 
                  if f.startswith('standardized_') and f.endswith('.json')
                  and f != 'all_bikes_standardized.json']
    
    import re
    all_slugs = defaultdict(list)
    
    for json_file in sorted(json_files):
        json_path = os.path.join(json_dir, json_file)
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                bikes_data = json.load(f)
            
            for bike_data in (bikes_data if isinstance(bikes_data, list) else [bikes_data]):
                brand = bike_data.get('firm', '').strip()
                model = bike_data.get('model', '').strip()
                year = bike_data.get('year')
                
                # Generate slug (simplified version of generate_slug)
                parts = []
                if brand:
                    parts.append(re.sub(r'[^\w\s-]', '', brand).strip().lower().replace(' ', '-'))
                if model:
                    parts.append(re.sub(r'[^\w\s-]', '', model).strip().lower().replace(' ', '-'))
                if year:
                    parts.append(str(year))
                
                slug = '-'.join(parts) if parts else None
                
                if slug:
                    all_slugs[slug].append({
                        'file': json_file,
                        'brand': brand,
                        'model': model,
                        'year': year
                    })
        
        except Exception as e:
            print(f"  ❌ Error processing {json_file}: {e}")
    
    duplicates = {slug: bikes for slug, bikes in all_slugs.items() if len(bikes) > 1}
    
    if duplicates:
        print(f"\n⚠️  Found {len(duplicates)} duplicate slugs across files:")
        for slug, bikes in list(duplicates.items())[:10]:  # Show first 10
            print(f"\n   Slug: {slug}")
            for bike in bikes:
                print(f"     - {bike['file']}: {bike['brand']} {bike['model']} ({bike['year']})")
        if len(duplicates) > 10:
            print(f"\n   ... and {len(duplicates) - 10} more")
    else:
        print("\n✅ No duplicate slugs found across files")


def main():
    """Main diagnostic function"""
    print("="*60)
    print("🔍 MIGRATION DIAGNOSTIC TOOL")
    print("="*60)
    print("\nThis script helps diagnose differences in migration results")
    print("between development and production environments.\n")
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Analyze JSON files
    file_stats, total_bikes_in_files = analyze_json_files()
    
    # Check for duplicate slugs
    check_duplicate_slugs_in_files()
    
    # Create Flask app and analyze database
    app = create_app()
    db_stats = analyze_database_state(app)
    
    # Summary and recommendations
    print("\n" + "="*60)
    print("📋 SUMMARY AND RECOMMENDATIONS")
    print("="*60)
    
    print(f"\n📄 JSON Files Analysis:")
    print(f"   Total files: {len(file_stats)}")
    print(f"   Total bikes in files: {total_bikes_in_files}")
    
    print(f"\n🗄️  Database Analysis:")
    print(f"   Current bikes in DB: {db_stats['bikes']}")
    print(f"   Current sources in DB: {db_stats['sources']}")
    
    if db_stats['bikes'] > 0:
        print(f"\n⚠️  IMPORTANT:")
        print(f"   Your database already has {db_stats['bikes']} bikes.")
        print(f"   When you run migrate_to_mysql.py, it will:")
        print(f"   - Skip bikes that already exist (by brand+model+year or slug)")
        print(f"   - Only add new bikes")
        print(f"   - Final count = existing bikes + new bikes added")
        print(f"\n   To get a fresh migration matching production:")
        print(f"   1. Drop database: python scripts/db/drop_bike_data.py")
        print(f"   2. Run migration: python scripts/db/migrate_to_mysql.py --force")
    
    expected_new_bikes = total_bikes_in_files
    if db_stats['bikes'] > 0:
        print(f"\n📊 Expected Result:")
        print(f"   If database is clean: ~{total_bikes_in_files} bikes")
        print(f"   With current DB state: {db_stats['bikes']} existing + up to {total_bikes_in_files} new")
        print(f"   (Some new bikes may be skipped as duplicates)")
    else:
        print(f"\n📊 Expected Result:")
        print(f"   If migration succeeds: ~{total_bikes_in_files} bikes")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
