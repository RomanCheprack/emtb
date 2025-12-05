#!/usr/bin/env python3
"""
Email notification utility for pipeline execution.

Sends summary emails using the app's SMTP configuration.
"""

import os
import sys
import smtplib
from email.message import EmailMessage
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)


def send_email(to_email, subject, body, html_body=None):
    """
    Send email using SMTP configuration from environment variables.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Plain text email body
        html_body: Optional HTML email body
    
    Returns:
        True if successful, False otherwise
    """
    email_user = os.getenv('EMAIL_USER')
    email_pass = os.getenv('EMAIL_PASS')
    
    if not email_user or not email_pass:
        print("⚠️  EMAIL_USER or EMAIL_PASS not configured, skipping email notification")
        return False
    
    try:
        msg = EmailMessage()
        msg["From"] = email_user
        msg["To"] = to_email
        msg["Subject"] = subject
        
        # Set plain text body
        msg.set_content(body)
        
        # Set HTML body if provided
        if html_body:
            msg.add_alternative(html_body, subtype='html')
        
        # Send via Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(email_user, email_pass)
            smtp.send_message(msg)
        
        print(f"✅ Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


def format_pipeline_summary(stats, duration_seconds, status, error_message=None):
    """
    Format pipeline execution summary as plain text.
    
    Args:
        stats: Dictionary with pipeline statistics
        duration_seconds: Total execution time in seconds
        status: 'success' or 'failed'
        error_message: Error message if status is 'failed'
    
    Returns:
        Formatted email body (plain text)
    """
    duration_min = int(duration_seconds / 60)
    duration_sec = int(duration_seconds % 60)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    status_icon = "✅" if status == "success" else "❌"
    status_text = "SUCCESS" if status == "success" else "FAILED"
    
    body = f"""
Pipeline Execution Summary
==========================
Date: {timestamp}
Duration: {duration_min}m {duration_sec}s
Status: {status_icon} {status_text}

"""
    
    # Step 1: Scraping
    if 'scraping' in stats:
        scraping = stats['scraping']
        body += f"Step 1: Scraping\n"
        if scraping.get('status') == 'success':
            body += f"  ✅ Completed: {scraping.get('scrapers_run', 0)} scrapers\n"
            body += f"  📊 Total entries: {scraping.get('total_entries', 0)} bikes\n"
        else:
            body += f"  ❌ Failed: {scraping.get('error', 'Unknown error')}\n"
        body += "\n"
    
    # Step 2: Duplicate Check
    if 'duplicate_check' in stats:
        dup = stats['duplicate_check']
        body += f"Step 2: Duplicate Check (Raw JSON)\n"
        if dup.get('status') == 'success':
            body += f"  ✅ Processed: {dup.get('files_processed', 0)} files\n"
            body += f"  📊 Total entries: {dup.get('total_entries', 0)}\n"
            body += f"  🔍 Duplicates removed: {dup.get('duplicates_removed', 0)}\n"
        else:
            body += f"  ❌ Failed: {dup.get('error', 'Unknown error')}\n"
        body += "\n"
    
    # Step 3: Standardization
    if 'standardization' in stats:
        std = stats['standardization']
        body += f"Step 3: Standardization\n"
        if std.get('status') == 'success':
            body += f"  ✅ Processed: {std.get('files_processed', 0)} files\n"
        else:
            body += f"  ❌ Failed: {std.get('error', 'Unknown error')}\n"
        body += "\n"
    
    # Step 4: Deduplication
    if 'deduplication' in stats:
        dedup = stats['deduplication']
        body += f"Step 4: Deduplication (Standardized)\n"
        if dedup.get('status') == 'success':
            body += f"  ✅ Removed: {dedup.get('duplicates_removed', 0)} duplicates\n"
        else:
            body += f"  ❌ Failed: {dedup.get('error', 'Unknown error')}\n"
        body += "\n"
    
    # Step 5: Drop Data
    if 'drop_data' in stats:
        drop = stats['drop_data']
        body += f"Step 5: Drop Bike Data\n"
        if drop.get('status') == 'success':
            body += f"  ✅ Deleted: {drop.get('bikes_deleted', 0)} bikes\n"
            body += f"  ✅ Deleted: {drop.get('listings_deleted', 0)} listings\n"
        else:
            body += f"  ❌ Failed: {drop.get('error', 'Unknown error')}\n"
        body += "\n"
    
    # Step 6: Migration
    if 'migration' in stats:
        mig = stats['migration']
        body += f"Step 6: Database Migration\n"
        if mig.get('status') == 'success':
            body += f"  ✅ Migrated: {mig.get('bikes_added', 0)} bikes\n"
            body += f"  ✅ Brands: {mig.get('brands_count', 0)}\n"
            body += f"  ✅ Sources: {mig.get('sources_count', 0)}\n"
            body += f"  📊 Skipped (duplicates): {mig.get('bikes_skipped', 0)}\n"
        else:
            body += f"  ❌ Failed: {mig.get('error', 'Unknown error')}\n"
        body += "\n"
    
    # Error message if failed
    if status == "failed" and error_message:
        body += f"\nError Details:\n{error_message}\n"
    
    body += f"\n{'=' * 60}\n"
    
    return body


def send_pipeline_notification(stats, duration_seconds, status, error_message=None, to_email=None):
    """
    Send pipeline execution notification email.
    
    Args:
        stats: Dictionary with pipeline statistics
        duration_seconds: Total execution time in seconds
        status: 'success' or 'failed'
        error_message: Error message if status is 'failed'
        to_email: Recipient email (defaults to EMAIL_USER or romancheprack@gmail.com)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if to_email is None:
        # Default to configured email or fallback
        to_email = os.getenv('EMAIL_USER') or 'romancheprack@gmail.com'
    
    status_text = "SUCCESS" if status == "success" else "FAILED"
    subject = f"[eMTB Pipeline] Migration {status_text}"
    
    body = format_pipeline_summary(stats, duration_seconds, status, error_message)
    
    return send_email(to_email, subject, body)


def test_email_configuration():
    """
    Test email configuration by sending a test email.
    
    Returns:
        True if successful, False otherwise
    """
    email_user = os.getenv('EMAIL_USER')
    email_pass = os.getenv('EMAIL_PASS')
    
    if not email_user or not email_pass:
        print("❌ EMAIL_USER or EMAIL_PASS not configured")
        print("   Set these environment variables to enable email notifications")
        return False
    
    to_email = email_user  # Send test to self
    
    subject = "[eMTB Pipeline] Test Email"
    body = f"""
This is a test email from the eMTB Pipeline system.

If you receive this email, your SMTP configuration is working correctly.

Configuration:
- SMTP Server: smtp.gmail.com:465
- From: {email_user}
- To: {to_email}

Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    print("Sending test email...")
    success = send_email(to_email, subject, body)
    
    if success:
        print(f"✅ Test email sent to {to_email}")
        print("   Please check your inbox to confirm delivery")
    else:
        print("❌ Failed to send test email")
        print("   Please check your EMAIL_USER and EMAIL_PASS configuration")
    
    return success


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Email notification utility')
    parser.add_argument('--test', action='store_true', help='Send test email')
    
    args = parser.parse_args()
    
    if args.test:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        test_email_configuration()
    else:
        print("Email notification utility")
        print("\nUsage:")
        print("  python scripts/utils/email_notifier.py --test  # Test email configuration")
        print("\nThis module is typically used by the pipeline orchestrator.")

