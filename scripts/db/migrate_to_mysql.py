#!/usr/bin/env python3
"""
Migration script to import data from standardized JSON files in data/standardized_data/
to the new MySQL database with normalized schema.
"""

import sys
import os
import json
import re
from datetime import datetime, timezone
from decimal import Decimal

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db
from app.models import (
    User, Brand, Source, Bike, BikeListing, BikePrice,
    BikeSpecRaw, BikeSpecStd, BikeImage, CompareCount, Comparison
)


def add_performance_indexes(app):
    """Add performance indexes after data migration"""
    with app.app_context():
        # Indexes to create
        indexes = [
            # Basic filtering indexes
            ("idx_bikes_category", "bikes", "category"),
            ("idx_bikes_year", "bikes", "year"),
            ("idx_bikes_sub_category", "bikes", "sub_category"),
            ("idx_bikes_brand_id", "bikes", "brand_id"),
            ("idx_bikes_uuid", "bikes", "uuid"),
            
            # Foreign key indexes for joins
            ("idx_bike_listings_bike_id", "bike_listings", "bike_id"),
            ("idx_bike_listings_source_id", "bike_listings", "source_id"),
            ("idx_bike_specs_std_bike_id", "bike_specs_std", "bike_id"),
            ("idx_bike_specs_std_spec_name", "bike_specs_std", "spec_name"),
            ("idx_bike_images_bike_id", "bike_images", "bike_id"),
            ("idx_bike_prices_listing_id", "bike_prices", "listing_id"),
            
            # Brand name for filtering
            ("idx_brands_name", "brands", "name"),
        ]
        
        # Composite indexes
        composite_indexes = [
            ("idx_bikes_category_year", "bikes", ["category", "year"]),
            ("idx_bike_specs_bike_spec", "bike_specs_std", ["bike_id", "spec_name"]),
        ]
        
        created_count = 0
        skipped_count = 0
        
        # Create single-column indexes
        for index_name, table_name, column_name in indexes:
            try:
                create_query = f"CREATE INDEX {index_name} ON {table_name}({column_name})"
                db.session.execute(db.text(create_query))
                print(f"   ✅ {index_name}")
                created_count += 1
            except Exception as e:
                print(f"   ⏭️  {index_name} (already exists or skipped)")
                skipped_count += 1
        
        # Create composite indexes
        for index_name, table_name, columns in composite_indexes:
            try:
                columns_str = ", ".join(columns)
                create_query = f"CREATE INDEX {index_name} ON {table_name}({columns_str})"
                db.session.execute(db.text(create_query))
                print(f"   ✅ {index_name} (composite)")
                created_count += 1
            except Exception as e:
                print(f"   ⏭️  {index_name} (already exists or skipped)")
                skipped_count += 1
        
        db.session.commit()
        print(f"\n📊 Created {created_count} indexes, skipped {skipped_count}")


def get_or_create_brand(brand_name, brand_cache):
    """Get or create a brand, using cache to avoid duplicates"""
    if not brand_name:
        return None
    
    brand_name = brand_name.strip()
    
    if brand_name in brand_cache:
        return brand_cache[brand_name]
    
    # Check if brand exists in database
    brand = Brand.query.filter_by(name=brand_name).first()
    if not brand:
        brand = Brand(name=brand_name)
        db.session.add(brand)
        db.session.flush()  # Get the ID
        db.session.commit()  # Commit immediately to persist even if bike fails
    
    brand_cache[brand_name] = brand
    return brand


def get_or_create_source(source_name, domain, source_cache):
    """Get or create a source, using cache to avoid duplicates"""
    cache_key = f"{source_name}_{domain}"
    
    if cache_key in source_cache:
        return source_cache[cache_key]
    
    # Check if source exists in database
    source = Source.query.filter_by(domain=domain).first()
    if not source:
        source = Source(importer=source_name, domain=domain)
        db.session.add(source)
        db.session.flush()  # Get the ID
    
    source_cache[cache_key] = source
    return source


def extract_price(price_value):
    """Extract numeric price from string or number"""
    # Handle None
    if price_value is None:
        return None
    
    # Handle numeric types directly (int, float, Decimal)
    if isinstance(price_value, (int, float, Decimal)):
        # Skip 0 as it's not a valid price
        if price_value == 0:
            return None
        try:
            return Decimal(str(price_value))
        except:
            return None
    
    # Handle string values - extract numeric part
    if isinstance(price_value, str):
        price_str = price_value.replace(',', '').replace('₪', '').strip()
        
        # Skip if it's empty or a non-numeric string like "צור קשר" or "N/A"
        if not price_str or price_str.lower() in ['n/a', 'na', '', 'none', 'null']:
            return None
        
        # Extract numeric value using regex
        match = re.search(r'(\d+(?:\.\d+)?)', price_str)
        if match:
            try:
                return Decimal(match.group(1))
            except:
                return None
    
    # For any other type, try to convert to string and extract
    price_str = str(price_value).replace(',', '').replace('₪', '').strip()
    match = re.search(r'(\d+(?:\.\d+)?)', price_str)
    if match:
        try:
            return Decimal(match.group(1))
        except:
            return None
    
    return None


def extract_year(year_value):
    """Extract valid year as integer from various formats"""
    if not year_value:
        return None
    
    # If already an integer, return it
    if isinstance(year_value, int):
        return year_value if 1900 <= year_value <= 2100 else None
    
    # Try to convert string to integer
    try:
        year_str = str(year_value).strip()
        year_int = int(year_str)
        # Validate reasonable year range
        return year_int if 1900 <= year_int <= 2100 else None
    except (ValueError, TypeError):
        # Not a valid integer (e.g., "לא מוגדר", "N/A", etc.)
        return None


def generate_slug(brand_name, model, year, used_slugs=None):
    """Generate SEO-friendly slug
    
    Args:
        brand_name: Brand name
        model: Model name
        year: Year
        used_slugs: Set of slugs already used in current batch (to avoid duplicates within batch)
    """
    parts = []
    if brand_name:
        parts.append(re.sub(r'[^\w\s-]', '', brand_name).strip().lower().replace(' ', '-'))
    if model:
        parts.append(re.sub(r'[^\w\s-]', '', model).strip().lower().replace(' ', '-'))
    if year:
        parts.append(str(year))
    
    slug = '-'.join(parts) if parts else None
    
    if not slug:
        return None
    
    # Ensure uniqueness against both database and current batch
    original_slug = slug
    counter = 1
    
    while True:
        # Check database
        if Bike.query.filter_by(slug=slug).first():
            slug = f"{original_slug}-{counter}"
            counter += 1
            continue
        
        # Check current batch (if provided)
        if used_slugs is not None and slug in used_slugs:
            slug = f"{original_slug}-{counter}"
            counter += 1
            continue
        
        # Slug is unique
        break
    
    return slug


def extract_source_from_url(product_url):
    """Extract domain from product URL"""
    if not product_url:
        return "unknown", "unknown.com"
    
    match = re.search(r'https?://(?:www\.)?([^/]+)', product_url)
    if match:
        domain = match.group(1)
        # Extract importer name from domain
        importer = domain.split('.')[0]
        return importer, domain
    return "unknown", "unknown.com"


def migrate_json_data(app):
    """Migrate data from standardized JSON files"""
    print("\n📄 Migrating data from JSON files...")
    
    json_dir = os.path.join(project_root, 'data', 'standardized_data')
    
    if not os.path.exists(json_dir):
        print(f"⚠️  JSON directory not found at {json_dir}")
        return
    
    with app.app_context():
        brand_cache = {}
        source_cache = {}
        
        # Get all standardized JSON files
        json_files = [f for f in os.listdir(json_dir) 
                      if f.startswith('standardized_') and f.endswith('.json')
                      and f != 'all_bikes_standardized.json']
        
        print(f"Found {len(json_files)} JSON files to process")
        
        total_added = 0
        total_skipped = 0
        
        for json_file in json_files:
            json_path = os.path.join(json_dir, json_file)
            source_name = json_file.replace('standardized_', '').replace('_data.json', '').replace('.json', '')
            
            print(f"\n📂 Processing {json_file}...")
            
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    bikes_data = json.load(f)
                
                print(f"   Found {len(bikes_data)} bikes")
                
                # Create source BEFORE processing bikes to ensure it exists even if all bikes fail
                source = None
                if bikes_data:
                    first_bike = bikes_data[0]
                    source_data = first_bike.get('source', {})
                    importer = source_data.get('importer', source_name)
                    domain = source_data.get('domain', '')
                    
                    # Fallback if domain not found
                    if not domain or domain == 'unknown.com':
                        domain = f"{source_name}.co.il"
                        importer = source_name
                    
                    source = get_or_create_source(importer, domain, source_cache)
                    # Commit source immediately to ensure it persists even if bikes fail
                    db.session.commit()
                    print(f"   ✅ Source: {importer} ({domain})")
                
                # Track slugs used in this file to avoid duplicates within the same file
                used_slugs_in_file = set()
                # Track bikes added in this file to avoid duplicates within the same batch
                bikes_added_in_file = set()
                
                for bike_data in bikes_data:
                    try:
                        # Validate required fields before processing
                        model = bike_data.get('model', '').strip() if bike_data.get('model') else None
                        if not model or len(model) == 0:
                            print(f"   ⚠️  Skipping bike with missing model: {bike_data.get('source', {}).get('product_url', 'N/A')[:50]}...")
                            total_skipped += 1
                            continue
                        
                        # Validate model length (max 255 chars)
                        if len(model) > 255:
                            print(f"   ⚠️  Skipping bike with model too long ({len(model)} chars): {model[:50]}...")
                            total_skipped += 1
                            continue
                        
                        # Get or create brand
                        brand = get_or_create_brand(bike_data.get('firm'), brand_cache)
                        
                        # Use the source created above
                        # (Still extract product_url from individual bike data)
                        source_data = bike_data.get('source', {})
                        product_url = source_data.get('product_url', '')
                        # Generate slug with uniqueness check against both DB and current file
                        slug = generate_slug(bike_data.get('firm'), model, bike_data.get('year'), used_slugs_in_file)
                        
                        if not slug:
                            print(f"   ⚠️  Skipping bike with empty slug: {brand.name if brand else 'Unknown'} {model}")
                            total_skipped += 1
                            continue
                        
                        # Validate slug length (max 255 chars)
                        if len(slug) > 255:
                            print(f"   ⚠️  Skipping bike with slug too long ({len(slug)} chars): {brand.name if brand else 'Unknown'} {model}")
                            total_skipped += 1
                            continue
                        
                        # Track this slug as used
                        used_slugs_in_file.add(slug)
                        
                        # Extract year for duplicate checking
                        year = extract_year(bike_data.get('year'))
                        
                        # Create bike key for duplicate checking
                        bike_key = (brand.id if brand else None, model, year)
                        
                        # Check if bike already exists (by slug or brand+model+year)
                        # First check against bikes added in current file batch (before commit)
                        if bike_key in bikes_added_in_file:
                            # This bike was already added in this file batch - skip it
                            print(f"   ⚠️  Skipping duplicate bike in file: {brand.name if brand else 'Unknown'} {model} ({year})")
                            total_skipped += 1
                            continue
                        
                        existing_bike = None
                        # Check database for existing bike by slug
                        if slug:
                            existing_bike = Bike.query.filter_by(slug=slug).first()
                        
                        # Also check by unique constraint (brand_id, model, year) in database
                        # This check works for both bikes with year and without year (None)
                        if not existing_bike:
                            if brand and model:
                                existing_bike = Bike.query.filter_by(
                                    brand_id=brand.id,
                                    model=model,
                                    year=year  # year can be None, which is valid
                                ).first()
                        
                        if existing_bike:
                            # Bike exists - check if it needs a price added
                            # Find the listing for this bike from the same source
                            existing_listing = BikeListing.query.filter_by(
                                bike_id=existing_bike.id,
                                source_id=source.id if source else None,
                                product_url=product_url
                            ).first()
                            
                            # If listing exists but has no price, add it
                            if existing_listing:
                                existing_price = BikePrice.query.filter_by(listing_id=existing_listing.id).first()
                                if not existing_price:
                                    # Extract both prices separately
                                    original_price = extract_price(bike_data.get('original_price'))
                                    disc_price = extract_price(bike_data.get('disc_price'))
                                    
                                    # Create price record if at least one price exists
                                    if original_price is not None or disc_price is not None:
                                        bike_price = BikePrice(
                                            listing_id=existing_listing.id,
                                            original_price=original_price,
                                            disc_price=disc_price,
                                            currency='ILS',
                                            scraped_at=datetime.now(timezone.utc)
                                        )
                                        db.session.add(bike_price)
                                        db.session.flush()
                                        print(f"   ✅ Added missing price to existing bike: {model}")
                                    else:
                                        print(f"   ⚠️  No price found for existing bike {model}: original_price={bike_data.get('original_price')}, disc_price={bike_data.get('disc_price')}")
                            
                            total_skipped += 1
                            continue
                        
                        # Extract image data (nested under 'images' key in standardized format)
                        images_data = bike_data.get('images', {})
                        main_image_url = images_data.get('image_url', '')
                        gallery_urls = images_data.get('gallery_images_urls', [])
                        
                        # Get rewritten_description for bike.description field
                        rewritten_description = bike_data.get('rewritten_description', '').strip() if bike_data.get('rewritten_description') else None
                        
                        # Create bike
                        bike = Bike(
                            brand_id=brand.id if brand else None,
                            model=model,
                            year=year,
                            category=bike_data.get('category'),
                            sub_category=bike_data.get('sub_category') or bike_data.get('sub-category'),
                            style=bike_data.get('style'),
                            fork_length=bike_data.get('fork length'),
                            description=rewritten_description,  # Store rewritten_description in description field
                            slug=slug,
                            main_image_url=main_image_url,
                            created_at=datetime.now(timezone.utc)
                        )
                        db.session.add(bike)
                        db.session.flush()
                        
                        # Check if listing already exists (to handle duplicate product URLs in source data)
                        existing_listing = BikeListing.query.filter_by(
                            source_id=source.id if source else None,
                            product_url=product_url
                        ).first()
                        
                        if existing_listing:
                            # Listing already exists, use it instead of creating new one
                            listing = existing_listing
                            print(f"   ⚠️  Skipping duplicate listing: {product_url}")
                        else:
                            # Create new listing
                            listing = BikeListing(
                                bike_id=bike.id,
                                source_id=source.id if source else None,
                                product_url=product_url,
                                availability=True,
                                created_at=datetime.now(timezone.utc)
                            )
                            db.session.add(listing)
                            db.session.flush()
                        
                        # Add price - store both original_price and disc_price separately
                        # Only add price if listing doesn't already have one
                        existing_price = BikePrice.query.filter_by(listing_id=listing.id).first()
                        if not existing_price:
                            # Extract both prices separately from JSON
                            original_price = extract_price(bike_data.get('original_price'))
                            disc_price = extract_price(bike_data.get('disc_price'))
                            
                            # Create price record if at least one price exists
                            # original_price should exist in all entries, so this should always create a record
                            if original_price is not None or disc_price is not None:
                                bike_price = BikePrice(
                                    listing_id=listing.id,
                                    original_price=original_price,
                                    disc_price=disc_price,
                                    currency='ILS',
                                    scraped_at=datetime.now(timezone.utc)
                                )
                                db.session.add(bike_price)
                            else:
                                # Log when no price can be extracted (for debugging)
                                print(f"   ⚠️  No price found for bike {model}: original_price={bike_data.get('original_price')}, disc_price={bike_data.get('disc_price')}")
                        
                        # Add specs - both raw (for display) and standardized (for filtering)
                        specs_data = bike_data.get('specs', {})
                        if specs_data:
                            # Specs are nested - iterate over specs dict
                            spec_items = specs_data.items()
                        else:
                            # Specs at root level (old format) - iterate over bike_data
                            spec_items = bike_data.items()
                        
                        for json_key, value in spec_items:
                            # Skip non-spec fields
                            # Note: rewritten_description is now stored in bike.description, but we also store it in raw_specs for completeness
                            if json_key in ['id', 'firm', 'model', 'year', 'price', 'disc_price', 'original_price',
                                           'image_url', 'product_url', 'gallery_images_urls', 'category',
                                           'source', 'images', 'specs', 'wh', 'fork length', 'style',
                                           'sub_category', 'sub-category']:
                                continue
                            
                            if value and str(value).strip():
                                # Add raw spec (linked to listing, preserves original data)
                                raw_spec = BikeSpecRaw(
                                    listing_id=listing.id,
                                    spec_key_raw=json_key,
                                    spec_value_raw=str(value),
                                    scraped_at=datetime.now(timezone.utc)
                                )
                                db.session.add(raw_spec)
                                
                                # Add standardized spec (linked to bike, normalized for filtering)
                                spec_name = json_key.lower().replace(' ', '_').replace('-', '_')
                                spec = BikeSpecStd(
                                    bike_id=bike.id,
                                    spec_name=spec_name,
                                    spec_value=str(value),
                                    updated_at=datetime.now(timezone.utc)
                                )
                                db.session.add(spec)
                        
                        # Add gallery images (already extracted above)
                        # Deduplicate URLs to avoid unique constraint violations
                        if gallery_urls:
                            seen_urls = set()
                            position = 0
                            for url in gallery_urls:
                                if url not in seen_urls:
                                    seen_urls.add(url)
                                    img = BikeImage(
                                        bike_id=bike.id,
                                        source_id=source.id if source else None,
                                        image_url=url,
                                        is_main=(position == 0 and not main_image_url),
                                        position=position
                                    )
                                    db.session.add(img)
                                    position += 1
                        
                        total_added += 1
                        
                        # Track this bike as added in current file batch
                        bikes_added_in_file.add(bike_key)
                        
                    except Exception as e:
                        print(f"   ⚠️  Error processing bike {bike_data.get('model', 'unknown')}: {e}")
                        db.session.rollback()  # Rollback failed bike to keep session clean
                        continue
                
                # Commit after each file
                db.session.commit()
                print(f"   ✅ Processed {json_file}")
                
            except Exception as e:
                db.session.rollback()
                print(f"   ❌ Error processing {json_file}: {e}")
                import traceback
                traceback.print_exc()
        
        # Count prices created
        total_prices = BikePrice.query.count()
        total_listings = BikeListing.query.count()
        
        print(f"\n✅ JSON Migration Complete:")
        print(f"   Bikes added: {total_added}")
        print(f"   Bikes skipped (duplicates): {total_skipped}")
        print(f"   Listings created: {total_listings}")
        print(f"   Prices created: {total_prices}")
        if total_listings > 0:
            print(f"   Price coverage: {(total_prices / total_listings * 100):.1f}% ({total_prices}/{total_listings} listings have prices)")


def main(force=False):
    """Main migration function"""
    print("=" * 60)
    print("🚀 MySQL Data Import Script")
    print("=" * 60)
    print("\nThis script will import bike data from JSON files")
    print("in data/standardized_data/ to MySQL database")
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        print(f"\n📊 Target Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        
        # Check if database has tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if not tables:
            print("\n❌ No tables found in database!")
            print("   Please run 'python scripts/db/create_mysql_schema.py' first")
            return
        
        print(f"\n✅ Found {len(tables)} tables in database")
        
        # Ask for confirmation
        if not force:
            print("\n⚠️  This will import data to MySQL database")
            print("   Note: Duplicate bikes (same brand+model+year) will be skipped")
            response = input("\nDo you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Aborted.")
                return
        
        # Import JSON data
        migrate_json_data(app)
        
        print("\n" + "=" * 60)
        print("✅ Import Complete!")
        print("=" * 60)
        
        # Show statistics
        print("\n📊 Database Statistics:")
        print(f"   Brands: {Brand.query.count()}")
        print(f"   Sources: {Source.query.count()}")
        print(f"   Bikes: {Bike.query.count()}")
        print(f"   Listings: {BikeListing.query.count()}")
        print(f"   Prices: {BikePrice.query.count()}")
        print(f"   Specs: {BikeSpecStd.query.count()}")
        print(f"   Images: {BikeImage.query.count()}")
        print(f"   Comparisons: {Comparison.query.count()}")
        
        # Add performance indexes
        print("\n" + "=" * 60)
        print("🚀 Adding Performance Indexes...")
        print("=" * 60)
        add_performance_indexes(app)
        print("\n✅ Performance indexes created!")


if __name__ == "__main__":
    force = '--force' in sys.argv or '-f' in sys.argv
    main(force=force)

