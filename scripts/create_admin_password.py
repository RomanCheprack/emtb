#!/usr/bin/env python3
"""
Script to generate a secure password hash for admin authentication.

Usage:
    python scripts/create_admin_password.py

This will prompt you for a password and generate a hash that you can
set as ADMIN_PASSWORD_HASH in your .env file.
"""

from werkzeug.security import generate_password_hash
import getpass

def main():
    print("=" * 60)
    print("Admin Password Hash Generator")
    print("=" * 60)
    print()
    
    password = getpass.getpass("Enter admin password: ")
    password_confirm = getpass.getpass("Confirm admin password: ")
    
    if password != password_confirm:
        print("\n❌ Passwords do not match!")
        return
    
    if len(password) < 8:
        print("\n⚠️  Warning: Password is less than 8 characters. Consider using a stronger password.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    password_hash = generate_password_hash(password)
    
    print("\n" + "=" * 60)
    print("✅ Password hash generated successfully!")
    print("=" * 60)
    print()
    print("Add this to your .env file:")
    print()
    print(f"ADMIN_PASSWORD_HASH={password_hash}")
    print()
    print("Also set ADMIN_USERNAME (default is 'admin'):")
    print("ADMIN_USERNAME=your_username")
    print()
    print("⚠️  IMPORTANT: Keep your .env file secure and never commit it to version control!")
    print("=" * 60)

if __name__ == "__main__":
    main()
