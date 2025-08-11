import sqlite3
import os
from models import get_session, Bike

def migrate_database_schema():
    """Safely migrate the database schema by adding new columns without dropping data"""
    print("Starting database schema migration...")
    
    # Get the database file path
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'emtb.db')
    
    if not os.path.exists(db_path):
        print("Database file not found. Creating new database...")
        from models import init_db
        init_db()
        return
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get current table schema
        cursor.execute("PRAGMA table_info(bikes)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        print(f"Existing columns: {existing_columns}")
        
        # Define new columns to add
        new_columns = [
            ('wh', 'INTEGER'),
            ('gallery_images_urls', 'TEXT'),
            ('fork_length', 'INTEGER'),
            ('sub_category', 'VARCHAR(255)'),
            ('rear_wheel_maxtravel', 'VARCHAR(255)'),
            ('battery_capacity', 'VARCHAR(255)'),
            ('front_wheel_size', 'VARCHAR(255)'),
            ('rear_wheel_size', 'VARCHAR(255)'),
            ('battery_watts_per_hour', 'VARCHAR(255)')
        ]
        
        # Add each new column if it doesn't exist
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                print(f"Adding column: {column_name} ({column_type})")
                try:
                    cursor.execute(f"ALTER TABLE bikes ADD COLUMN {column_name} {column_type}")
                    print(f"  ✓ Successfully added {column_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"  - Column {column_name} already exists")
                    else:
                        print(f"  ✗ Error adding {column_name}: {e}")
            else:
                print(f"  - Column {column_name} already exists")
        
        # Commit the changes
        conn.commit()
        print("\nDatabase schema migration completed successfully!")
        
        # Verify the migration by checking the updated schema
        cursor.execute("PRAGMA table_info(bikes)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        print(f"\nUpdated columns: {updated_columns}")
        
        # Count existing records
        cursor.execute("SELECT COUNT(*) FROM bikes")
        bike_count = cursor.fetchone()[0]
        print(f"Total bikes in database: {bike_count}")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database_schema() 