from flask import Blueprint, render_template, abort
from app.services.blog_service import load_posts
from app.utils.security import sanitize_html_content
from datetime import datetime
import os
import re

bp = Blueprint('blog', __name__)

@bp.route("/blog")
def blog_list():
    posts = load_posts()
    print(f"Blog route: loaded {len(posts)} posts")
    for post in posts:
        print(f"Post: {post.get('title', 'No title')} - Date: {post.get('date', 'No date')}")
    return render_template("blog_list.html", posts=posts)

@bp.route("/blog/<slug>")
def blog_post(slug):
    # Validate slug to prevent path traversal attacks
    if not re.match(r'^[a-zA-Z0-9_-]+$', slug):
        abort(404)
    
    posts = load_posts()
    post = next((p for p in posts if p["slug"] == slug), None)
    if not post:
        abort(404)

    # Date is already parsed in the service, but ensure it's a datetime object
    if isinstance(post["date"], str):
        post["date"] = datetime.strptime(post["date"], "%Y-%m-%d")

    # מיקום הקובץ עם התוכן של הפוסט - secure path construction
    content_path = os.path.join("templates", "posts", f"{slug}.html")
    
    # Additional security check to ensure the path is within the intended directory
    base_dir = os.path.abspath("templates/posts")
    full_path = os.path.abspath(content_path)
    
    if not full_path.startswith(base_dir):
        abort(404)
    
    if not os.path.exists(content_path):
        abort(404)

    # קורא את התוכן של קובץ ה-HTML לפוסט
    with open(content_path, encoding="utf-8") as f:
        post_content = f.read()

    # מוסיף את התוכן שנקרא למשתנה post['content'] עם סניטציה
    post["content"] = sanitize_html_content(post_content)

    return render_template("blog_post.html", post=post)
