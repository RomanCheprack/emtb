#!/usr/bin/env python3
"""
Shared utilities for EMTB scripts
Contains common functions used across multiple scripts
"""

import json
import os
import re
import urllib.parse


def clean_bike_field_value(value):
    """
    Clean bike field values to ensure they're safe for database storage and JSON serialization.
    This function is used across multiple scripts to maintain consistency.
    """
    if value is None:
        return None
    
    # Convert to string and clean any problematic characters
    cleaned_value = str(value)
    
    # Remove all control characters except basic whitespace
    cleaned_value = ''.join(char for char in cleaned_value if ord(char) >= 32 or char in ' \t\n\r')
    
    # Replace problematic characters that could break JSON
    cleaned_value = cleaned_value.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    cleaned_value = cleaned_value.replace('"', "'")   # Replace double quotes with single quotes
    cleaned_value = cleaned_value.replace('\\', '/')  # Replace backslashes with forward slashes
    cleaned_value = cleaned_value.replace(';', ', ')  # Replace semicolons with commas
    
    # Remove any remaining control characters
    cleaned_value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned_value)
    
    # Remove duplicate spaces
    cleaned_value = re.sub(r'\s+', ' ', cleaned_value)
    
    # Trim whitespace
    cleaned_value = cleaned_value.strip()
    
    return cleaned_value if cleaned_value else None


def clean_bike_data_for_json(bike_dict):
    """
    Clean bike data to ensure it's safe for JSON serialization.
    This is the same function as in app.py, moved here for consistency.
    """
    cleaned_dict = {}
    for key, value in bike_dict.items():
        if value is not None:
            # Convert to string and clean any problematic characters
            cleaned_value = str(value)
            
            # Remove all control characters except basic whitespace
            cleaned_value = ''.join(char for char in cleaned_value if ord(char) >= 32 or char in ' \t\n\r')
            
            # Replace problematic characters that could break JSON
            cleaned_value = cleaned_value.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            cleaned_value = cleaned_value.replace('"', "'")   # Replace double quotes with single quotes
            cleaned_value = cleaned_value.replace('\\', '/')  # Replace backslashes with forward slashes
            cleaned_value = cleaned_value.replace(';', ', ')  # Replace semicolons with commas
            
            # Remove any remaining control characters
            cleaned_value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned_value)
            
            # Remove duplicate spaces
            cleaned_value = re.sub(r'\s+', ' ', cleaned_value)
            
            # Trim whitespace
            cleaned_value = cleaned_value.strip()
            
            if cleaned_value:  # Only add non-empty values
                cleaned_dict[key] = cleaned_value
        else:
            cleaned_dict[key] = None
    return cleaned_dict


def load_bikes_from_json():
    """
    Load all bikes from standardized JSON files for migration purposes.
    
    NOTE: This function is only needed for:
    - Initial database setup
    - Re-migrating data after re-scraping
    - Database recreation scenarios
    
    For normal operation, the app reads from the SQLite database.
    """
    # Get the path to the standardized data directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    standardized_data_dir = os.path.join(current_dir, '..', 'data', 'standardized_data')
    
    if not os.path.exists(standardized_data_dir):
        print(f"Warning: Standardized data directory not found: {standardized_data_dir}")
        return []
    
    # Try to load from combined standardized file first
    combined_file = os.path.join(standardized_data_dir, "all_bikes_standardized.json")
    if os.path.exists(combined_file):
        print(f"Loading from combined file: {combined_file}")
        with open(combined_file, 'r', encoding='utf-8') as f:
            bikes = json.load(f)
        return bikes
    
    # If no combined file, load from individual standardized files
    standardized_files = [f for f in os.listdir(standardized_data_dir) if f.startswith('standardized_') and f.endswith('.json')]
    
    if not standardized_files:
        print(f"Warning: No standardized JSON files found in {standardized_data_dir}")
        return []
    
    all_bikes = []
    for filename in standardized_files:
        filepath = os.path.join(standardized_data_dir, filename)
        print(f"Loading from {filename}...")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            bikes = json.load(f)
        
        all_bikes.extend(bikes)
        print(f"  Loaded {len(bikes)} bikes from {filename}")
    
    return all_bikes


def clean_bike_id(bike_id):
    """
    Clean bike ID by removing URL-encoded characters and replacing with clean text.
    This function is used in maintenance scripts.
    """
    if not bike_id:
        return bike_id
    
    # Try to decode URL-encoded characters
    try:
        decoded = urllib.parse.unquote(bike_id)
        # Replace Hebrew characters with English equivalents or remove them
        cleaned = re.sub(r'[א-ת]', '', decoded)  # Remove Hebrew characters
        cleaned = re.sub(r'[^\w\-_.]', '_', cleaned)  # Replace special chars with underscore
        cleaned = re.sub(r'_+', '_', cleaned)  # Replace multiple underscores with single
        cleaned = cleaned.strip('_')  # Remove leading/trailing underscores
        return cleaned
    except:
        return bike_id


def get_database_path():
    """
    Get the path to the main database file.
    This ensures consistency across scripts.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, '..', 'emtb.db')
