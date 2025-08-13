#!/usr/bin/env python3
"""
Clean up orphaned CompareCount entries that reference non-existent bikes
"""

from scripts.db.models import init_db, get_session, Bike, CompareCount

def cleanup_orphaned_counts():
    """Remove CompareCount entries for bikes that don't exist"""
    
    print("=== CLEANING UP ORPHANED COMPARE COUNTS ===\n")
    
    init_db()
    db_session = get_session()
    
    try:
        # Get all CompareCount entries
        all_compare_counts = db_session.query(CompareCount).all()
        total_counts = len(all_compare_counts)
        
        print(f"Total CompareCount entries: {total_counts}")
        
        # Find orphaned entries
        orphaned_entries = []
        for cc in all_compare_counts:
            bike = db_session.query(Bike).filter_by(id=cc.bike_id).first()
            if not bike:
                orphaned_entries.append(cc)
                print(f"Orphaned: {cc.bike_id} (count: {cc.count})")
        
        print(f"\nFound {len(orphaned_entries)} orphaned entries")
        
        if orphaned_entries:
            # Ask for confirmation
            response = input("\nDo you want to delete these orphaned entries? (y/N): ")
            if response.lower() == 'y':
                for cc in orphaned_entries:
                    db_session.delete(cc)
                db_session.commit()
                print(f"Deleted {len(orphaned_entries)} orphaned entries")
            else:
                print("No changes made")
        else:
            print("No orphaned entries found!")
            
        # Show remaining valid entries
        print(f"\nRemaining valid CompareCount entries:")
        valid_counts = db_session.query(CompareCount).join(Bike).order_by(CompareCount.count.desc()).limit(10).all()
        for i, cc in enumerate(valid_counts, 1):
            bike = cc.bike
            print(f"{i}. {bike.firm} {bike.model} ({bike.year}) - Count: {cc.count}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    cleanup_orphaned_counts()
