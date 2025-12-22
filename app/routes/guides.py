from flask import Blueprint, render_template, abort, url_for
from app.extensions import db
from app.models import Guide
import re

bp = Blueprint('guides', __name__)


@bp.route('/guides')
def guides_list():
    """List all published guides"""
    guides = db.session.query(Guide).filter_by(is_published=True).order_by(
        Guide.created_at.desc()
    ).all()
    
    return render_template('guides/index.html', guides=guides)


@bp.route('/guides/<slug>')
def guide_detail(slug):
    """Display guide by slug"""
    # Validate slug to prevent path traversal attacks
    if not re.match(r'^[a-zA-Z0-9-]+$', slug):
        abort(404)
    
    guide = db.session.query(Guide).filter_by(slug=slug, is_published=True).first()
    
    if not guide:
        abort(404)
    
    return render_template('guides/detail.html', guide=guide, is_preview=False)

