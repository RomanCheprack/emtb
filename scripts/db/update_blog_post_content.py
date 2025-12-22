#!/usr/bin/env python3
"""
Update blog post content from HTML files.

This script:
1. Finds blog posts in the database
2. Reads HTML content from templates/posts/*.html files
3. Updates the content field in the database

Usage:
    python scripts/db/update_blog_post_content.py
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db
from app.models import BlogPost

def update_blog_post_content():
    """Update blog post content from HTML files"""
    print("=" * 60)
    print("📝 Updating Blog Post Content from HTML Files")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Get all blog posts
        posts = db.session.query(BlogPost).all()
        
        if not posts:
            print("\n❌ No blog posts found in database")
            print("=" * 60)
            return
        
        print(f"\n📖 Found {len(posts)} posts in database\n")
        
        updated_count = 0
        not_found_count = 0
        error_count = 0
        
        posts_dir = os.path.join(project_root, "templates", "posts")
        
        for post in posts:
            print(f"📄 Processing: {post.title} (slug: {post.slug})")
            
            # Try to find HTML file
            # Try different possible filenames
            possible_files = [
                f"{post.slug}.html",
                f"{post.slug.replace('-', '_')}.html",  # If slug has hyphens, try underscores
                f"{post.slug.replace('_', '-')}.html",  # If slug has underscores, try hyphens
            ]
            
            content_html = None
            found_file = None
            
            for filename in possible_files:
                file_path = os.path.join(posts_dir, filename)
                if os.path.exists(file_path):
                    found_file = file_path
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content_html = f.read()
                        print(f"   ✅ Found and loaded: {filename}")
                        break
                    except Exception as e:
                        print(f"   ❌ Error reading {filename}: {e}")
                        error_count += 1
                        continue
            
            if not content_html:
                # Try to find any HTML file that might match
                if os.path.exists(posts_dir):
                    for file in os.listdir(posts_dir):
                        if file.endswith('.html') and post.slug in file:
                            file_path = os.path.join(posts_dir, file)
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content_html = f.read()
                                found_file = file_path
                                print(f"   ✅ Found matching file: {file}")
                                break
                            except Exception as e:
                                print(f"   ❌ Error reading {file}: {e}")
                                continue
                
                if not content_html:
                    print(f"   ⚠️  No HTML file found for slug: {post.slug}")
                    not_found_count += 1
                    continue
            
            # Update post content
            try:
                post.content = content_html
                db.session.commit()
                print(f"   ✅ Updated content in database")
                updated_count += 1
            except Exception as e:
                db.session.rollback()
                print(f"   ❌ Error updating post: {e}")
                error_count += 1
        
        print("\n" + "=" * 60)
        print("📊 Update Summary:")
        print(f"   ✅ Updated: {updated_count}")
        print(f"   ⚠️  Not Found: {not_found_count}")
        print(f"   ❌ Errors: {error_count}")
        print("=" * 60)
        print("✅ Done!")
        print("=" * 60)

if __name__ == "__main__":
    update_blog_post_content()

