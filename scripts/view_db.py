import sqlite3
from models import get_session, Bike

def view_database():
    """View the contents of the SQLite database"""
    print("=== Database Contents ===")
    
    # Connect to SQLite database
    conn = sqlite3.connect('emtb.db')
    cursor = conn.cursor()
    
    # Show all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables in database: {[table[0] for table in tables]}")
    print()
    
    # Show bikes table structure
    cursor.execute("PRAGMA table_info(bikes);")
    columns = cursor.fetchall()
    print("Bikes table structure:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    print()
    
    # Show count of bikes
    cursor.execute("SELECT COUNT(*) FROM bikes;")
    count = cursor.fetchone()[0]
    print(f"Total bikes in database: {count}")
    print()
    
    # Show first 5 bikes
    cursor.execute("SELECT id, firm, model, year FROM bikes LIMIT 5;")
    bikes = cursor.fetchall()
    print("First 5 bikes:")
    for bike in bikes:
        print(f"  ID: {bike[0]}, Firm: {bike[1]}, Model: {bike[2]}, Year: {bike[3]}")
    print()
    
    # Show comparisons table if it exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='comparisons';")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM comparisons;")
        comp_count = cursor.fetchone()[0]
        print(f"Total comparisons in database: {comp_count}")
    else:
        print("Comparisons table does not exist yet.")
    
    conn.close()

if __name__ == "__main__":
    view_database() 