from flask import Blueprint, render_template, abort, request
from app.extensions import db
from app.models import BlogPost
import re

bp = Blueprint('blog', __name__)

@bp.route("/blog")
def blog_list():
    """List all published blog posts"""
    posts = db.session.query(BlogPost).filter_by(is_published=True).order_by(BlogPost.created_at.desc()).all()
    
    # Convert to dict format for template compatibility
    posts_data = []
    for post in posts:
        posts_data.append({
            'slug': post.slug,
            'title': post.title,
            'author': post.author or "רומן צ'פרק",
            'date': post.created_at,
            'content': post.content or '',
            'hero_image': post.hero_image,
            'seo_description': post.seo_description
        })
    
    return render_template("blog_list.html", posts=posts_data)

@bp.route("/blog/<slug>")
def blog_post(slug):
    """Display a single blog post"""
    # Validate slug to prevent path traversal attacks
    if not re.match(r'^[a-zA-Z0-9_-]+$', slug):
        abort(404)
    
    # Get post from database (only published posts)
    post = db.session.query(BlogPost).filter_by(slug=slug, is_published=True).first()
    
    if not post:
        abort(404)
    
    # Check if this is a preview (admin only)
    is_preview = request.args.get('preview') == 'true' and request.args.get('admin') == 'true'
    
    # Convert to dict format for template compatibility
    post_data = {
        'slug': post.slug,
        'title': post.title,
        'author': post.author or "רומן צ'פרק",
        'date': post.created_at,
        'content': post.content or '',
        'hero_image': post.hero_image,
        'seo_title': post.seo_title,
        'seo_description': post.seo_description,
        'tags': post.tags
    }
    
    return render_template("blog_post.html", post=post_data, is_preview=is_preview)
