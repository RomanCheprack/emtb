#!/usr/bin/env python3
"""
Script to clean up duplicate bikes in the database.
Keeps the oldest bike (by created_at) and deletes newer duplicates.
"""

import sys
import os
from collections import defaultdict

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db
from app.models import Bike, Brand

def cleanup_duplicates(dry_run=True):
    """
    Remove duplicate bikes, keeping the oldest one by created_at.
    
    Args:
        dry_run: If True, only show what would be deleted without actually deleting
    """
    print("=" * 80)
    print("🧹 CLEANING UP DUPLICATE BIKES")
    print("=" * 80)
    
    load_dotenv(override=True)
    app = create_app()
    
    with app.app_context():
        all_bikes = Bike.query.all()
        print(f"\n📊 Total bikes before cleanup: {len(all_bikes)}")
        
        # Group bikes by (brand_id, model, year)
        bike_groups = defaultdict(list)
        for bike in all_bikes:
            brand_name = bike.brand.name if bike.brand else None
            key = (bike.brand_id, bike.model, bike.year)
            bike_groups[key].append(bike)
        
        # Find duplicates
        duplicates_to_delete = []
        bikes_to_keep = []
        
        for key, bikes in bike_groups.items():
            if len(bikes) > 1:
                # Sort by created_at (oldest first)
                bikes_sorted = sorted(bikes, key=lambda b: b.created_at)
                
                # Keep the oldest one
                keep_bike = bikes_sorted[0]
                bikes_to_keep.append(keep_bike)
                
                # Mark the rest for deletion
                to_delete = bikes_sorted[1:]
                duplicates_to_delete.extend(to_delete)
                
                # Print info
                brand_name = keep_bike.brand.name if keep_bike.brand else "NO_BRAND"
                print(f"\n🔍 {brand_name} {keep_bike.model} ({keep_bike.year})")
                print(f"   ✅ KEEPING: ID {keep_bike.id} (UUID: {keep_bike.uuid}, Created: {keep_bike.created_at})")
                for bike in to_delete:
                    print(f"   ❌ DELETING: ID {bike.id} (UUID: {bike.uuid}, Created: {bike.created_at})")
        
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"Total bikes: {len(all_bikes)}")
        print(f"Duplicate groups found: {len(bikes_to_keep)}")
        print(f"Bikes to delete: {len(duplicates_to_delete)}")
        print(f"Bikes after cleanup: {len(all_bikes) - len(duplicates_to_delete)}")
        
        if not duplicates_to_delete:
            print("\n✅ No duplicates found!")
            return
        
        if dry_run:
            print("\n" + "=" * 80)
            print("🔍 DRY RUN MODE - No changes made")
            print("=" * 80)
            print("\nTo actually delete duplicates, run:")
            print("  python scripts/db/cleanup_duplicates.py --execute")
            return
        
        # Actually delete duplicates
        print("\n" + "=" * 80)
        print("⚠️  EXECUTING DELETION")
        print("=" * 80)
        
        deleted_count = 0
        for bike in duplicates_to_delete:
            try:
                # The cascade delete will handle related records (listings, specs, images, etc.)
                db.session.delete(bike)
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting bike ID {bike.id}: {e}")
                db.session.rollback()
                continue
        
        # Commit all deletions
        try:
            db.session.commit()
            print(f"\n✅ Successfully deleted {deleted_count} duplicate bikes!")
            
            # Verify final count
            final_count = Bike.query.count()
            print(f"\n📊 Final bike count: {final_count}")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error committing deletions: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # Check for --execute flag
    execute = '--execute' in sys.argv or '-e' in sys.argv
    dry_run = not execute
    
    if dry_run:
        print("\n⚠️  Running in DRY RUN mode (no changes will be made)")
        print("    Use --execute or -e to actually delete duplicates\n")
    else:
        print("\n⚠️  EXECUTION MODE - This will permanently delete duplicates!")
        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Aborted.")
            sys.exit(0)
    
    cleanup_duplicates(dry_run=dry_run)



