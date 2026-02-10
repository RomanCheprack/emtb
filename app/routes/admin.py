from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, current_app
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import AvailabilityLead, ContactLead, StoreRequestLead, Guide, BlogPost
from app.utils.helpers import generate_slug_from_title
from datetime import datetime
import os
import re
from pathlib import Path

bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin credentials from environment variables
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH')  # Should be pre-hashed

# If no hash is set, use a default password (should be changed in production!)
if not ADMIN_PASSWORD_HASH:
    # Default password: "admin123" - CHANGE THIS IN PRODUCTION!
    ADMIN_PASSWORD_HASH = generate_password_hash('admin123')


def login_required(f):
    """Decorator to require login for admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Check credentials
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            session.permanent = True
            # Explicitly set session cookie to persist
            session.modified = True
            flash('התחברת בהצלחה', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('שם משתמש או סיסמה שגויים', 'error')
    
    return render_template('admin/login.html')


@bp.route('/logout')
def logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    flash('התנתקת בהצלחה', 'info')
    return redirect(url_for('admin.login'))


@bp.route('/')
@login_required
def dashboard():
    """Admin dashboard showing all leads"""
    # Get availability leads
    try:
        availability_leads = db.session.query(AvailabilityLead).order_by(
            AvailabilityLead.created_at.desc()
        ).all()
    except Exception as e:
        current_app.logger.error(f"Error loading availability leads: {e}")
        availability_leads = []
    
    # Get contact leads
    try:
        contact_leads = db.session.query(ContactLead).order_by(
            ContactLead.created_at.desc()
        ).all()
    except Exception as e:
        current_app.logger.error(f"Error loading contact leads: {e}")
        contact_leads = []
    
    # Get store request leads
    try:
        store_request_leads = db.session.query(StoreRequestLead).order_by(
            StoreRequestLead.created_at.desc()
        ).all()
    except Exception as e:
        current_app.logger.error(f"Error loading store request leads: {e}")
        store_request_leads = []
    
    return render_template('admin/dashboard.html', 
                         availability_leads=availability_leads,
                         contact_leads=contact_leads,
                         store_request_leads=store_request_leads)


@bp.route('/availability-leads')
@login_required
def availability_leads():
    """View all availability leads"""
    try:
        leads = db.session.query(AvailabilityLead).order_by(
            AvailabilityLead.created_at.desc()
        ).all()
    except Exception as e:
        current_app.logger.error(f"Error loading availability leads: {e}")
        leads = []
        flash(f'שגיאה בטעינת הלידים: {str(e)}', 'error')
    
    return render_template('admin/availability_leads.html', leads=leads)


@bp.route('/contact-leads')
@login_required
def contact_leads():
    """View all contact leads"""
    try:
        leads = db.session.query(ContactLead).order_by(
            ContactLead.created_at.desc()
        ).all()
    except Exception as e:
        current_app.logger.error(f"Error loading contact leads: {e}")
        leads = []
        flash(f'שגיאה בטעינת הלידים: {str(e)}', 'error')
    
    return render_template('admin/contact_leads.html', leads=leads)


@bp.route('/store-request-leads')
@login_required
def store_request_leads():
    """View all store request leads"""
    try:
        leads = db.session.query(StoreRequestLead).order_by(
            StoreRequestLead.created_at.desc()
        ).all()
    except Exception as e:
        current_app.logger.error(f"Error loading store request leads: {e}")
        leads = []
        flash(f'שגיאה בטעינת הלידים: {str(e)}', 'error')
    
    return render_template('admin/store_request_leads.html', leads=leads)


@bp.route('/availability-leads/<int:lead_id>/delete', methods=['POST'])
@login_required
def availability_lead_delete(lead_id):
    """Delete availability lead"""
    lead = db.session.query(AvailabilityLead).filter_by(id=lead_id).first_or_404()
    
    try:
        db.session.delete(lead)
        db.session.commit()
        flash('הליד נמחק בהצלחה', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'שגיאה במחיקת הליד: {str(e)}', 'error')
    
    return redirect(url_for('admin.availability_leads'))


@bp.route('/contact-leads/<int:lead_id>/delete', methods=['POST'])
@login_required
def contact_lead_delete(lead_id):
    """Delete contact lead"""
    lead = db.session.query(ContactLead).filter_by(id=lead_id).first_or_404()
    
    try:
        db.session.delete(lead)
        db.session.commit()
        flash('הליד נמחק בהצלחה', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'שגיאה במחיקת הליד: {str(e)}', 'error')
    
    return redirect(url_for('admin.contact_leads'))


@bp.route('/store-request-leads/<int:lead_id>/delete', methods=['POST'], endpoint='store_request_lead_delete')
@login_required
def store_request_lead_delete(lead_id):
    """Delete store request lead"""
    lead = db.session.query(StoreRequestLead).filter_by(id=lead_id).first_or_404()
    
    try:
        db.session.delete(lead)
        db.session.commit()
        flash('הליד נמחק בהצלחה', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'שגיאה במחיקת הליד: {str(e)}', 'error')
    
    return redirect(url_for('admin.store_request_leads'))


# ---------------------------
# Guides Routes
# ---------------------------
@bp.route('/guides')
@login_required
def guides_list():
    """List all guides"""
    guides = db.session.query(Guide).order_by(Guide.created_at.desc()).all()
    return render_template('admin/guides_list.html', guides=guides)


def allowed_file(filename, file_type='image'):
    """Check if file extension is allowed"""
    if file_type == 'image':
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
    elif file_type == 'document':
        ALLOWED_EXTENSIONS = {'docx', 'doc'}
    else:
        ALLOWED_EXTENSIONS = set()
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_image(file, guide_id=None, subfolder='guides'):
    """Save uploaded image and return URL"""
    if file and file.filename and allowed_file(file.filename):
        # Create guides directory if it doesn't exist
        guides_dir = Path(current_app.static_folder) / 'images' / subfolder
        guides_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        
        # Save file
        file_path = guides_dir / unique_filename
        file.save(str(file_path))
        
        # Return URL path
        return url_for('static', filename=f'images/{subfolder}/{unique_filename}')
    return None


@bp.route('/guides/new', methods=['GET', 'POST'])
@login_required
def guide_new():
    """Create new guide"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        slug = request.form.get('slug', '').strip()
        hero_image_url = request.form.get('hero_image', '').strip()
        hero_image_file = request.files.get('hero_image_file')
        content = request.form.get('content', '')
        seo_title = request.form.get('seo_title', '').strip()
        seo_description = request.form.get('seo_description', '').strip()
        tags = request.form.get('tags', '').strip()
        is_published = request.form.get('is_published') == 'on'
        
        # Validate required fields
        if not title:
            flash('כותרת היא שדה חובה', 'error')
            return render_template('admin/guide_form.html', guide=None)
        
        # Generate slug if not provided
        if not slug:
            slug = generate_slug_from_title(title)
        
        # Ensure slug is unique
        base_slug = slug
        counter = 1
        while db.session.query(Guide).filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Validate slug format (English only, alphanumeric and hyphens)
        if not re.match(r'^[a-zA-Z0-9-]+$', slug):
            flash('שגיאה: ה-slug חייב להכיל רק אותיות באנגלית, מספרים ומקפים', 'error')
            return render_template('admin/guide_form.html', guide=None)
        
        # Handle image upload (file takes priority over URL)
        hero_image = None
        if hero_image_file and hero_image_file.filename:
            uploaded_url = save_uploaded_image(hero_image_file)
            if uploaded_url:
                hero_image = uploaded_url
            else:
                flash('שגיאה בהעלאת התמונה. אנא ודא שהקובץ הוא תמונה תקינה (png, jpg, jpeg, gif, webp, svg)', 'error')
        elif hero_image_url:
            hero_image = hero_image_url
        
        # Sanitize content for security
        from app.utils.security import sanitize_html_content
        sanitized_content = sanitize_html_content(content) if content else ''
        
        # Create guide
        guide = Guide(
            title=title,
            slug=slug,
            hero_image=hero_image,
            content=sanitized_content,
            seo_title=seo_title if seo_title else None,
            seo_description=seo_description if seo_description else None,
            tags=tags if tags else None,
            is_published=is_published
        )
        
        try:
            db.session.add(guide)
            db.session.commit()
            flash('המדריך נוצר בהצלחה', 'success')
            return redirect(url_for('admin.guides_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'שגיאה ביצירת המדריך: {str(e)}', 'error')
            return render_template('admin/guide_form.html', guide=None)
    
    return render_template('admin/guide_form.html', guide=None)


@bp.route('/guides/<int:guide_id>/edit', methods=['GET', 'POST'])
@login_required
def guide_edit(guide_id):
    """Edit existing guide"""
    guide = db.session.query(Guide).filter_by(id=guide_id).first_or_404()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        slug = request.form.get('slug', '').strip()
        hero_image_url = request.form.get('hero_image', '').strip()
        hero_image_file = request.files.get('hero_image_file')
        content = request.form.get('content', '')
        seo_title = request.form.get('seo_title', '').strip()
        seo_description = request.form.get('seo_description', '').strip()
        tags = request.form.get('tags', '').strip()
        is_published = request.form.get('is_published') == 'on'
        
        # Validate required fields
        if not title:
            flash('כותרת היא שדה חובה', 'error')
            return render_template('admin/guide_form.html', guide=guide)
        
        # Generate slug if not provided
        if not slug:
            slug = generate_slug_from_title(title)
        
        # Check if slug changed and ensure uniqueness
        if slug != guide.slug:
            base_slug = slug
            counter = 1
            while db.session.query(Guide).filter_by(slug=slug).filter(Guide.id != guide_id).first():
                slug = f"{base_slug}-{counter}"
                counter += 1
        
        # Validate slug format
        if not re.match(r'^[a-zA-Z0-9-]+$', slug):
            flash('שגיאה: ה-slug חייב להכיל רק אותיות באנגלית, מספרים ומקפים', 'error')
            return render_template('admin/guide_form.html', guide=guide)
        
        # Handle image upload (file takes priority over URL)
        if hero_image_file and hero_image_file.filename:
            uploaded_url = save_uploaded_image(hero_image_file, guide_id)
            if uploaded_url:
                hero_image = uploaded_url
            else:
                flash('שגיאה בהעלאת התמונה. אנא ודא שהקובץ הוא תמונה תקינה (png, jpg, jpeg, gif, webp, svg)', 'error')
                hero_image = guide.hero_image  # Keep existing image
        elif hero_image_url:
            hero_image = hero_image_url
        else:
            hero_image = guide.hero_image  # Keep existing image if nothing provided
        
        # Sanitize content for security
        from app.utils.security import sanitize_html_content
        sanitized_content = sanitize_html_content(content) if content else ''
        
        # Update guide
        guide.title = title
        guide.slug = slug
        guide.hero_image = hero_image
        guide.content = sanitized_content
        guide.seo_title = seo_title if seo_title else None
        guide.seo_description = seo_description if seo_description else None
        guide.tags = tags if tags else None
        guide.is_published = is_published
        guide.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash('המדריך עודכן בהצלחה', 'success')
            return redirect(url_for('admin.guides_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'שגיאה בעדכון המדריך: {str(e)}', 'error')
            return render_template('admin/guide_form.html', guide=guide)
    
    return render_template('admin/guide_form.html', guide=guide)


@bp.route('/guides/<int:guide_id>/delete', methods=['POST'])
@login_required
def guide_delete(guide_id):
    """Delete guide"""
    guide = db.session.query(Guide).filter_by(id=guide_id).first_or_404()
    
    try:
        db.session.delete(guide)
        db.session.commit()
        flash('המדריך נמחק בהצלחה', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'שגיאה במחיקת המדריך: {str(e)}', 'error')
    
    return redirect(url_for('admin.guides_list'))


@bp.route('/guides/<int:guide_id>/duplicate', methods=['POST'])
@login_required
def guide_duplicate(guide_id):
    """Duplicate guide"""
    original = db.session.query(Guide).filter_by(id=guide_id).first_or_404()
    
    # Create new guide with "(Copy)" in title
    new_title = f"{original.title} (Copy)"
    new_slug = generate_slug_from_title(new_title)
    
    # Ensure slug is unique
    base_slug = new_slug
    counter = 1
    while db.session.query(Guide).filter_by(slug=new_slug).first():
        new_slug = f"{base_slug}-{counter}"
        counter += 1
    
    new_guide = Guide(
        title=new_title,
        slug=new_slug,
        hero_image=original.hero_image,
        content=original.content,
        seo_title=original.seo_title,
        seo_description=original.seo_description,
        tags=original.tags,
        is_published=False  # Duplicates start as drafts
    )
    
    try:
        db.session.add(new_guide)
        db.session.commit()
        flash('המדריך שוכפל בהצלחה', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'שגיאה בשכפול המדריך: {str(e)}', 'error')
    
    return redirect(url_for('admin.guides_list'))


@bp.route('/guides/<int:guide_id>/preview')
@login_required
def guide_preview(guide_id):
    """Preview guide (admin only)"""
    guide = db.session.query(Guide).filter_by(id=guide_id).first_or_404()
    return render_template('guides/detail.html', guide=guide, is_preview=True)


@bp.route('/guides/<int:guide_id>/toggle-publish', methods=['POST'])
@login_required
def guide_toggle_publish(guide_id):
    """Toggle publish status of guide"""
    guide = db.session.query(Guide).filter_by(id=guide_id).first_or_404()
    
    try:
        guide.is_published = not guide.is_published
        guide.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = "פורסם" if guide.is_published else "הוסר מפרסום"
        flash(f'המדריך {status} בהצלחה', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'שגיאה בשינוי סטטוס הפרסום: {str(e)}', 'error')
    
    return redirect(url_for('admin.guides_list'))


@bp.route('/guides/upload-image', methods=['POST'])
@login_required
def guide_upload_content_image():
    """Upload image for guide content (used by TinyMCE)"""
    from flask import jsonify
    from app.extensions import csrf
    
    # CSRF token is validated by login_required and session, but we can also check it
    # For AJAX requests, CSRF token should be in form data
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename, 'image'):
        return jsonify({'error': 'Invalid file type. Only images are allowed.'}), 400
    
    # Validate file size (max 5MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 5 * 1024 * 1024:  # 5MB
        return jsonify({'error': 'File too large. Maximum size is 5MB.'}), 400
    
    # Save to content subfolder
    uploaded_url = save_uploaded_image(file, subfolder='guides/content')
    
    if uploaded_url:
        # Return in TinyMCE expected format
        return jsonify({
            'location': uploaded_url
        })
    else:
        return jsonify({'error': 'Failed to upload image'}), 500


@bp.route('/guides/upload-docx', methods=['POST'])
@login_required
def guide_upload_docx():
    """Upload DOCX file and convert to HTML for TinyMCE editor"""
    from flask import jsonify
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename, 'document'):
        return jsonify({'error': 'Invalid file type. Only DOCX and DOC files are allowed.'}), 400
    
    # Validate file size (max 10MB for documents)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 10 * 1024 * 1024:  # 10MB
        return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 400
    
    try:
        import mammoth
        
        # Convert DOCX to HTML
        result = mammoth.convert_to_html(file)
        html_content = result.value
        
        # Get any warnings
        warnings = result.messages
        
        # Sanitize the HTML content
        from app.utils.security import sanitize_html_content
        sanitized_html = sanitize_html_content(html_content)
        
        return jsonify({
            'success': True,
            'html': sanitized_html,
            'warnings': warnings if warnings else []
        })
    except ImportError:
        return jsonify({'error': 'Document conversion library not installed. Please install mammoth: pip install mammoth'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to convert document: {str(e)}'}), 500


# ---------------------------
# Blog Posts Routes
# ---------------------------
@bp.route('/blog')
@login_required
def blog_list():
    """List all blog posts"""
    posts = db.session.query(BlogPost).order_by(BlogPost.created_at.desc()).all()
    return render_template('admin/blog_list.html', posts=posts)


def save_uploaded_blog_image(file, post_id=None, subfolder='blog'):
    """Save uploaded image for blog posts and return URL"""
    if file and file.filename and allowed_file(file.filename):
        # Create blog directory if it doesn't exist
        blog_dir = Path(current_app.static_folder) / 'images' / subfolder
        blog_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        
        # Save file
        file_path = blog_dir / unique_filename
        file.save(str(file_path))
        
        # Return URL path
        return url_for('static', filename=f'images/{subfolder}/{unique_filename}')
    return None


@bp.route('/blog/new', methods=['GET', 'POST'])
@login_required
def blog_new():
    """Create new blog post"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        slug = request.form.get('slug', '').strip()
        author = request.form.get('author', '').strip()
        hero_image_url = request.form.get('hero_image', '').strip()
        hero_image_file = request.files.get('hero_image_file')
        content = request.form.get('content', '')
        seo_title = request.form.get('seo_title', '').strip()
        seo_description = request.form.get('seo_description', '').strip()
        tags = request.form.get('tags', '').strip()
        is_published = request.form.get('is_published') == 'on'
        
        # Validate required fields
        if not title:
            flash('כותרת היא שדה חובה', 'error')
            return render_template('admin/blog_form.html', post=None)
        
        # Generate slug if not provided
        if not slug:
            slug = generate_slug_from_title(title)
        
        # Ensure slug is unique
        base_slug = slug
        counter = 1
        while db.session.query(BlogPost).filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Validate slug format (English only, alphanumeric and hyphens)
        if not re.match(r'^[a-zA-Z0-9-]+$', slug):
            flash('שגיאה: ה-slug חייב להכיל רק אותיות באנגלית, מספרים ומקפים', 'error')
            return render_template('admin/blog_form.html', post=None)
        
        # Handle image upload (file takes priority over URL)
        hero_image = None
        if hero_image_file and hero_image_file.filename:
            uploaded_url = save_uploaded_blog_image(hero_image_file)
            if uploaded_url:
                hero_image = uploaded_url
            else:
                flash('שגיאה בהעלאת התמונה. אנא ודא שהקובץ הוא תמונה תקינה (png, jpg, jpeg, gif, webp, svg)', 'error')
        elif hero_image_url:
            hero_image = hero_image_url
        
        # Sanitize content for security
        from app.utils.security import sanitize_html_content
        sanitized_content = sanitize_html_content(content) if content else ''
        
        # Create blog post
        post = BlogPost(
            title=title,
            slug=slug,
            author=author if author else None,
            hero_image=hero_image,
            content=sanitized_content,
            seo_title=seo_title if seo_title else None,
            seo_description=seo_description if seo_description else None,
            tags=tags if tags else None,
            is_published=is_published
        )
        
        try:
            db.session.add(post)
            db.session.commit()
            flash('הפוסט נוצר בהצלחה', 'success')
            return redirect(url_for('admin.blog_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'שגיאה ביצירת הפוסט: {str(e)}', 'error')
            return render_template('admin/blog_form.html', post=None)
    
    return render_template('admin/blog_form.html', post=None)


@bp.route('/blog/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def blog_edit(post_id):
    """Edit existing blog post"""
    post = db.session.query(BlogPost).filter_by(id=post_id).first_or_404()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        slug = request.form.get('slug', '').strip()
        author = request.form.get('author', '').strip()
        hero_image_url = request.form.get('hero_image', '').strip()
        hero_image_file = request.files.get('hero_image_file')
        content = request.form.get('content', '')
        seo_title = request.form.get('seo_title', '').strip()
        seo_description = request.form.get('seo_description', '').strip()
        tags = request.form.get('tags', '').strip()
        is_published = request.form.get('is_published') == 'on'
        
        # Validate required fields
        if not title:
            flash('כותרת היא שדה חובה', 'error')
            return render_template('admin/blog_form.html', post=post)
        
        # Generate slug if not provided
        if not slug:
            slug = generate_slug_from_title(title)
        
        # Check if slug changed and ensure uniqueness
        if slug != post.slug:
            base_slug = slug
            counter = 1
            while db.session.query(BlogPost).filter_by(slug=slug).filter(BlogPost.id != post_id).first():
                slug = f"{base_slug}-{counter}"
                counter += 1
        
        # Validate slug format
        if not re.match(r'^[a-zA-Z0-9-]+$', slug):
            flash('שגיאה: ה-slug חייב להכיל רק אותיות באנגלית, מספרים ומקפים', 'error')
            return render_template('admin/blog_form.html', post=post)
        
        # Handle image upload (file takes priority over URL)
        if hero_image_file and hero_image_file.filename:
            uploaded_url = save_uploaded_blog_image(hero_image_file, post_id)
            if uploaded_url:
                hero_image = uploaded_url
            else:
                flash('שגיאה בהעלאת התמונה. אנא ודא שהקובץ הוא תמונה תקינה (png, jpg, jpeg, gif, webp, svg)', 'error')
                hero_image = post.hero_image  # Keep existing image
        elif hero_image_url:
            hero_image = hero_image_url
        else:
            hero_image = post.hero_image  # Keep existing image if nothing provided
        
        # Sanitize content for security
        from app.utils.security import sanitize_html_content
        sanitized_content = sanitize_html_content(content) if content else ''
        
        # Update blog post
        post.title = title
        post.slug = slug
        post.author = author if author else None
        post.hero_image = hero_image
        post.content = sanitized_content
        post.seo_title = seo_title if seo_title else None
        post.seo_description = seo_description if seo_description else None
        post.tags = tags if tags else None
        post.is_published = is_published
        post.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash('הפוסט עודכן בהצלחה', 'success')
            return redirect(url_for('admin.blog_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'שגיאה בעדכון הפוסט: {str(e)}', 'error')
            return render_template('admin/blog_form.html', post=post)
    
    return render_template('admin/blog_form.html', post=post)


@bp.route('/blog/<int:post_id>/delete', methods=['POST'])
@login_required
def blog_delete(post_id):
    """Delete blog post"""
    post = db.session.query(BlogPost).filter_by(id=post_id).first_or_404()
    
    try:
        db.session.delete(post)
        db.session.commit()
        flash('הפוסט נמחק בהצלחה', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'שגיאה במחיקת הפוסט: {str(e)}', 'error')
    
    return redirect(url_for('admin.blog_list'))


@bp.route('/blog/<int:post_id>/duplicate', methods=['POST'])
@login_required
def blog_duplicate(post_id):
    """Duplicate blog post"""
    original = db.session.query(BlogPost).filter_by(id=post_id).first_or_404()
    
    # Create new post with "(Copy)" in title
    new_title = f"{original.title} (Copy)"
    new_slug = generate_slug_from_title(new_title)
    
    # Ensure slug is unique
    base_slug = new_slug
    counter = 1
    while db.session.query(BlogPost).filter_by(slug=new_slug).first():
        new_slug = f"{base_slug}-{counter}"
        counter += 1
    
    new_post = BlogPost(
        title=new_title,
        slug=new_slug,
        author=original.author,
        hero_image=original.hero_image,
        content=original.content,
        seo_title=original.seo_title,
        seo_description=original.seo_description,
        tags=original.tags,
        is_published=False  # Duplicates start as drafts
    )
    
    try:
        db.session.add(new_post)
        db.session.commit()
        flash('הפוסט שוכפל בהצלחה', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'שגיאה בשכפול הפוסט: {str(e)}', 'error')
    
    return redirect(url_for('admin.blog_list'))


@bp.route('/blog/<int:post_id>/preview')
@login_required
def blog_preview(post_id):
    """Preview blog post (admin only)"""
    post = db.session.query(BlogPost).filter_by(id=post_id).first_or_404()
    
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
    
    return render_template('blog_post.html', post=post_data, is_preview=True)


@bp.route('/blog/<int:post_id>/toggle-publish', methods=['POST'])
@login_required
def blog_toggle_publish(post_id):
    """Toggle publish status of blog post"""
    post = db.session.query(BlogPost).filter_by(id=post_id).first_or_404()
    
    try:
        post.is_published = not post.is_published
        post.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = "פורסם" if post.is_published else "הוסר מפרסום"
        flash(f'הפוסט {status} בהצלחה', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'שגיאה בשינוי סטטוס הפרסום: {str(e)}', 'error')
    
    return redirect(url_for('admin.blog_list'))


@bp.route('/blog/upload-image', methods=['POST'])
@login_required
def blog_upload_content_image():
    """Upload image for blog post content (used by TinyMCE)"""
    from flask import jsonify
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename, 'image'):
        return jsonify({'error': 'Invalid file type. Only images are allowed.'}), 400
    
    # Validate file size (max 5MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 5 * 1024 * 1024:  # 5MB
        return jsonify({'error': 'File too large. Maximum size is 5MB.'}), 400
    
    # Save to content subfolder
    uploaded_url = save_uploaded_blog_image(file, subfolder='blog/content')
    
    if uploaded_url:
        # Return in TinyMCE expected format
        return jsonify({
            'location': uploaded_url
        })
    else:
        return jsonify({'error': 'Failed to upload image'}), 500


@bp.route('/blog/upload-docx', methods=['POST'])
@login_required
def blog_upload_docx():
    """Upload DOCX file and convert to HTML for TinyMCE editor"""
    from flask import jsonify
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename, 'document'):
        return jsonify({'error': 'Invalid file type. Only DOCX and DOC files are allowed.'}), 400
    
    # Validate file size (max 10MB for documents)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 10 * 1024 * 1024:  # 10MB
        return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 400
    
    try:
        import mammoth
        
        # Convert DOCX to HTML
        result = mammoth.convert_to_html(file)
        html_content = result.value
        
        # Get any warnings
        warnings = result.messages
        
        # Sanitize the HTML content
        from app.utils.security import sanitize_html_content
        sanitized_html = sanitize_html_content(html_content)
        
        return jsonify({
            'success': True,
            'html': sanitized_html,
            'warnings': warnings if warnings else []
        })
    except ImportError:
        return jsonify({'error': 'Document conversion library not installed. Please install mammoth: pip install mammoth'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to convert document: {str(e)}'}), 500
