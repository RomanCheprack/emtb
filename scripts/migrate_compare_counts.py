import json
import os
from models import init_db, get_session, CompareCount

def migrate_compare_counts():
    """Migrate compare counts from JSON file to database"""
    print("Starting migration of compare counts to database...")
    
    # Initialize database
    init_db()
    session = get_session()
    
    try:
        # Load compare counts from JSON file
        json_file = "data/compare_counts.json"
        if not os.path.exists(json_file):
            print(f"Compare counts file not found: {json_file}")
            return
        
        with open(json_file, 'r', encoding='utf-8') as f:
            compare_counts = json.load(f)
        
        print(f"Found {len(compare_counts)} compare count entries to migrate")
        
        # Migrate each compare count
        migrated_count = 0
        updated_count = 0
        
        for bike_id, count in compare_counts.items():
            # Check if compare count already exists
            existing_count = session.query(CompareCount).filter_by(bike_id=bike_id).first()
            
            if existing_count:
                # Update existing record
                existing_count.count = count
                updated_count += 1
                print(f"Updated compare count for bike {bike_id}: {count}")
            else:
                # Create new record
                compare_count = CompareCount(
                    bike_id=bike_id,
                    count=count
                )
                session.add(compare_count)
                migrated_count += 1
                print(f"Added compare count for bike {bike_id}: {count}")
        
        # Commit all changes
        session.commit()
        print(f"Successfully migrated {migrated_count} new compare counts")
        print(f"Updated {updated_count} existing compare counts")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def get_top_compared_bikes(limit=10):
    """Get top compared bikes from database"""
    session = get_session()
    try:
        top_bikes = session.query(CompareCount).order_by(CompareCount.count.desc()).limit(limit).all()
        return [(cc.bike_id, cc.count) for cc in top_bikes]
    finally:
        session.close()

def update_compare_count(bike_id):
    """Increment compare count for a bike"""
    session = get_session()
    try:
        compare_count = session.query(CompareCount).filter_by(bike_id=bike_id).first()
        
        if compare_count:
            compare_count.count += 1
        else:
            compare_count = CompareCount(bike_id=bike_id, count=1)
            session.add(compare_count)
        
        session.commit()
        return compare_count.count
    except Exception as e:
        print(f"Error updating compare count: {e}")
        session.rollback()
        return 0
    finally:
        session.close()

if __name__ == "__main__":
    print("Starting compare counts migration...")
    migrate_compare_counts()
    print("Compare counts migration completed!")
    
    # Show top compared bikes
    print("\nTop 10 most compared bikes:")
    top_bikes = get_top_compared_bikes(10)
    for i, (bike_id, count) in enumerate(top_bikes, 1):
        print(f"{i}. {bike_id}: {count} comparisons")
  