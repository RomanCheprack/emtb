#!/usr/bin/env python3
"""
Simple script to create only the new lead tables (AvailabilityLead and ContactLead).
This script will NOT drop existing tables - it only creates the new ones if they don't exist.

Usage:
    python scripts/db/create_lead_tables.py
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db

def create_lead_tables():
    """Create only the lead tables"""
    print("=" * 60)
    print("🔧 Creating Lead Tables")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Import the new models to ensure they're registered
        from app.models import AvailabilityLead, ContactLead
        
        print(f"\n📊 Database URI: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        
        # Check if tables already exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        tables_to_create = []
        if 'availability_leads' not in existing_tables:
            tables_to_create.append('availability_leads')
        else:
            print("\n✅ Table 'availability_leads' already exists")
        
        if 'contact_leads' not in existing_tables:
            tables_to_create.append('contact_leads')
        else:
            print("\n✅ Table 'contact_leads' already exists")
        
        if not tables_to_create:
            print("\n✅ All lead tables already exist. Nothing to do!")
            return
        
        print(f"\n✨ Creating {len(tables_to_create)} new table(s)...")
        
        # Create only the new tables
        # SQLAlchemy will only create tables that don't exist
        db.create_all()
        
        print("\n✅ Lead tables created successfully!")
        print("\n📋 Created tables:")
        for table in tables_to_create:
            print(f"   - {table}")
        
        print("\n" + "=" * 60)
        print("✅ Done!")
        print("=" * 60)

if __name__ == "__main__":
    create_lead_tables()
