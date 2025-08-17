#!/usr/bin/env python3
"""
WSGI entry point for production deployment
"""
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

# Create the Flask application
application = create_app()

if __name__ == "__main__":
    application.run()
