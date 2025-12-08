from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from app.extensions import db
from app.models import AvailabilityLead, ContactLead
from datetime import datetime
import os

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
    availability_leads = db.session.query(AvailabilityLead).order_by(
        AvailabilityLead.created_at.desc()
    ).all()
    
    # Get contact leads
    contact_leads = db.session.query(ContactLead).order_by(
        ContactLead.created_at.desc()
    ).all()
    
    return render_template('admin/dashboard.html', 
                         availability_leads=availability_leads,
                         contact_leads=contact_leads)


@bp.route('/availability-leads')
@login_required
def availability_leads():
    """View all availability leads"""
    leads = db.session.query(AvailabilityLead).order_by(
        AvailabilityLead.created_at.desc()
    ).all()
    
    return render_template('admin/availability_leads.html', leads=leads)


@bp.route('/contact-leads')
@login_required
def contact_leads():
    """View all contact leads"""
    leads = db.session.query(ContactLead).order_by(
        ContactLead.created_at.desc()
    ).all()
    
    return render_template('admin/contact_leads.html', leads=leads)
