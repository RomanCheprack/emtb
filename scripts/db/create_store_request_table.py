#!/usr/bin/env python3
"""
Simple script to create the store_request_leads table.
This script will NOT drop existing tables - it only creates the new one if it doesn't exist.

Usage:
    python scripts/db/create_store_request_table.py
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db

def create_store_request_table():
    """Create the store_request_leads table"""
    print("=" * 60)
    print("🔧 Creating Store Request Table")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Import the model to ensure it's registered
        from app.models import StoreRequestLead
        
        print(f"\n📊 Database URI: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        
        # Check if table already exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        if 'store_request_leads' in existing_tables:
            print("\n✅ Table 'store_request_leads' already exists")
            print("=" * 60)
            return
        
        print("\n✨ Creating new table 'store_request_leads'...")
        
        # Create only the new table
        # SQLAlchemy will only create tables that don't exist
        db.create_all()
        
        print("\n✅ Table created successfully!")
        print("\n📋 Created table:")
        print("   - store_request_leads")
        print("\n📝 Table structure:")
        print("   - id (BigInteger, Primary Key)")
        print("   - name (String 255, Required)")
        print("   - phone (String 50, Required)")
        print("   - city (String 255, Required)")
        print("   - bike_model (String 500)")
        print("   - bike_id (String 36)")
        print("   - remarks (Text)")
        print("   - created_at (DateTime)")
        
        print("\n" + "=" * 60)
        print("✅ Done!")
        print("=" * 60)

if __name__ == "__main__":
    create_store_request_table()

