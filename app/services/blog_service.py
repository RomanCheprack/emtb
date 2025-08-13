import json
import os
from datetime import datetime

def load_posts():
    """Load blog posts from the posts.json file"""
    posts_path = os.path.join("templates", "posts", "posts.json")
    try:
        with open(posts_path, "r", encoding="utf-8-sig") as f:
            posts = json.load(f)
        
        print(f"Loaded {len(posts)} posts from {posts_path}")
        
        # Convert date strings to datetime objects for template rendering
        for post in posts:
            if isinstance(post.get('date'), str):
                try:
                    post['date'] = datetime.strptime(post['date'], "%Y-%m-%d")
                except ValueError:
                    # If date parsing fails, keep as string
                    print(f"Failed to parse date for post {post.get('slug', 'unknown')}: {post.get('date')}")
                    pass
        
        return posts
    except FileNotFoundError:
        print(f"Posts file not found: {posts_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing posts.json: {e}")
        return []
