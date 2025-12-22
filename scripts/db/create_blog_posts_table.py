#!/usr/bin/env python3
"""
Simple script to create the blog_posts table.
This script will NOT drop existing tables - it only creates the new one if it doesn't exist.

Usage:
    python scripts/db/create_blog_posts_table.py
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db

def create_blog_posts_table():
    """Create the blog_posts table"""
    print("=" * 60)
    print("🔧 Creating Blog Posts Table")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Import the model to ensure it's registered
        from app.models import BlogPost
        
        print(f"\n📊 Database URI: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        
        # Check if table already exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        if 'blog_posts' in existing_tables:
            print("\n✅ Table 'blog_posts' already exists")
            print("=" * 60)
            return
        
        print("\n✨ Creating new table 'blog_posts'...")
        
        # Create only the new table
        # SQLAlchemy will only create tables that don't exist
        db.create_all()
        
        print("\n✅ Table created successfully!")
        print("\n📋 Created table:")
        print("   - blog_posts")
        print("\n📝 Table structure:")
        print("   - id (BigInteger, Primary Key)")
        print("   - title (String 255, Required)")
        print("   - slug (String 255, Unique, Required, Indexed)")
        print("   - author (String 255)")
        print("   - hero_image (String 500)")
        print("   - content (Text/LONGTEXT)")
        print("   - seo_title (String 255)")
        print("   - seo_description (Text)")
        print("   - tags (String 500, Comma-separated)")
        print("   - is_published (Boolean, Default: False)")
        print("   - created_at (DateTime)")
        print("   - updated_at (DateTime)")
        
        print("\n" + "=" * 60)
        print("✅ Done!")
        print("=" * 60)

if __name__ == "__main__":
    create_blog_posts_table()

