#!/usr/bin/env python3
"""
Migrate existing blog posts from JSON/HTML files to database.

This script:
1. Reads posts from templates/posts/posts.json
2. Reads HTML content from templates/posts/*.html files
3. Creates BlogPost records in the database
4. Sets is_published=True for all migrated posts

Usage:
    python scripts/db/migrate_blog_posts_from_json.py
"""

import sys
import os
import json
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db
from app.models import BlogPost

def migrate_blog_posts():
    """Migrate blog posts from JSON/HTML to database"""
    print("=" * 60)
    print("📦 Migrating Blog Posts from JSON/HTML to Database")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Ensure table exists
        db.create_all()
        
        # Path to posts.json
        posts_json_path = os.path.join(project_root, "templates", "posts", "posts.json")
        
        if not os.path.exists(posts_json_path):
            print(f"\n❌ Posts file not found: {posts_json_path}")
            print("=" * 60)
            return
        
        print(f"\n📖 Reading posts from: {posts_json_path}")
        
        # Read JSON file
        try:
            with open(posts_json_path, "r", encoding="utf-8-sig") as f:
                posts_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"\n❌ Error parsing JSON: {e}")
            print("=" * 60)
            return
        
        print(f"📝 Found {len(posts_data)} posts in JSON file\n")
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for post_data in posts_data:
            slug = post_data.get("slug")
            title = post_data.get("title")
            author = post_data.get("author", "רומן צ'פרק")
            date_str = post_data.get("date")
            
            print(f"📄 Processing: {title} (slug: {slug})")
            
            # Check if post already exists
            existing = BlogPost.query.filter_by(slug=slug).first()
            if existing:
                print(f"   ⏭️  Skipping - post with slug '{slug}' already exists in database")
                skipped_count += 1
                continue
            
            # Read HTML content
            content_path = post_data.get("content")
            if not content_path:
                # Try default path
                content_path = os.path.join("templates", "posts", f"{slug}.html")
            
            # Handle different path formats
            if not os.path.isabs(content_path):
                content_path = os.path.join(project_root, content_path)
            
            if not os.path.exists(content_path):
                print(f"   ⚠️  Warning: Content file not found: {content_path}")
                content_html = ""
            else:
                try:
                    with open(content_path, "r", encoding="utf-8") as f:
                        content_html = f.read()
                    print(f"   ✅ Loaded content from: {content_path}")
                except Exception as e:
                    print(f"   ❌ Error reading content file: {e}")
                    content_html = ""
            
            # Parse date
            created_date = None
            if date_str:
                try:
                    created_date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    print(f"   ⚠️  Warning: Could not parse date '{date_str}', using current date")
                    created_date = datetime.utcnow()
            else:
                created_date = datetime.utcnow()
            
            # Create BlogPost
            try:
                blog_post = BlogPost(
                    title=title,
                    slug=slug,
                    author=author,
                    content=content_html,
                    is_published=True,  # Migrate all as published
                    created_at=created_date,
                    updated_at=created_date
                )
                
                db.session.add(blog_post)
                db.session.commit()
                
                print(f"   ✅ Successfully migrated to database (ID: {blog_post.id})")
                migrated_count += 1
                
            except Exception as e:
                db.session.rollback()
                print(f"   ❌ Error creating post: {e}")
                error_count += 1
        
        print("\n" + "=" * 60)
        print("📊 Migration Summary:")
        print(f"   ✅ Migrated: {migrated_count}")
        print(f"   ⏭️  Skipped: {skipped_count}")
        print(f"   ❌ Errors: {error_count}")
        print("=" * 60)
        print("✅ Done!")
        print("=" * 60)

if __name__ == "__main__":
    migrate_blog_posts()

