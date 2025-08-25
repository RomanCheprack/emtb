#!/usr/bin/env python3
"""
Debug script to test Rosen data processing
"""

import os
import json

# Check if rosen.json exists
current_dir = os.path.dirname(os.path.abspath(__file__))
raw_data_dir = os.path.join(current_dir, '..', 'data', 'scraped_raw_data')
rosen_file = os.path.join(raw_data_dir, "rosen.json")

print(f"Current directory: {current_dir}")
print(f"Raw data directory: {raw_data_dir}")
print(f"Rosen file path: {rosen_file}")
print(f"Rosen file exists: {os.path.exists(rosen_file)}")

if os.path.exists(rosen_file):
    print("✅ Rosen file found!")
    
    # Try to read the file
    try:
        with open(rosen_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Successfully loaded Rosen data: {len(data)} bikes")
        
        # Show first bike
        if data:
            print(f"First bike: {data[0].get('model', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Error reading Rosen file: {e}")
else:
    print("❌ Rosen file not found!")
