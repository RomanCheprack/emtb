import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ..db.models import get_session, Bike
import urllib.parse
import re

def clean_bike_id(bike_id):
    """Clean bike ID by removing URL-encoded characters and replacing with clean text"""
    if not bike_id:
        return bike_id
    
    # Try to decode URL-encoded characters
    try:
        decoded = urllib.parse.unquote(bike_id)
        # Replace Hebrew characters with English equivalents or remove them
        cleaned = re.sub(r'[א-ת]', '', decoded)  # Remove Hebrew characters
        cleaned = re.sub(r'[^\w\-_.]', '_', cleaned)  # Replace special chars with underscore
        cleaned = re.sub(r'_+', '_', cleaned)  # Replace multiple underscores with single
        cleaned = cleaned.strip('_')  # Remove leading/trailing underscores
        return cleaned
    except:
        return bike_id

def fix_bike_ids():
    """Fix bike IDs that contain URL-encoded characters"""
    print("Starting bike ID cleanup...")
    
    session = get_session()
    try:
        # Get all bikes
        bikes = session.query(Bike).all()
        print(f"Found {len(bikes)} bikes to process")
        
        updated_count = 0
        
        for bike in bikes:
            original_id = bike.id
            cleaned_id = clean_bike_id(original_id)
            
            if original_id != cleaned_id:
                print(f"Updating bike ID: {original_id} -> {cleaned_id}")
                
                # Check if the new ID already exists
                existing_bike = session.query(Bike).filter_by(id=cleaned_id).first()
                if existing_bike:
                    print(f"  WARNING: ID {cleaned_id} already exists, skipping...")
                    continue
                
                # Update the bike ID
                bike.id = cleaned_id
                updated_count += 1
        
        # Commit all changes
        session.commit()
        print(f"Successfully updated {updated_count} bike IDs")
        
    except Exception as e:
        print(f"Error during bike ID cleanup: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    fix_bike_ids()
