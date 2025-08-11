#!/usr/bin/env python3
"""
Script to run all scrapers and save their output to data/scraped_raw_data/
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_scraper(scraper_path, output_dir):
    """Run a single scraper and save output to the specified directory"""
    scraper_name = Path(scraper_path).stem
    print(f"\n{'='*50}")
    print(f"Running scraper: {scraper_name}")
    print(f"{'='*50}")
    
    # Change to the scrapers directory so relative imports work
    original_dir = os.getcwd()
    scrapers_dir = Path(scraper_path).parent
    os.chdir(scrapers_dir)
    
    try:
        # Run the scraper
        result = subprocess.run([sys.executable, Path(scraper_path).name], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ {scraper_name} completed successfully")
            
            # Move the output file to the correct directory
            output_file = f"{scraper_name}.json"
            if os.path.exists(output_file):
                # Create output directory if it doesn't exist
                os.makedirs(output_dir, exist_ok=True)
                
                # Move the file
                import shutil
                shutil.move(output_file, os.path.join(output_dir, output_file))
                print(f"📁 Moved {output_file} to {output_dir}")
            else:
                print(f"⚠️ No output file {output_file} found")
        else:
            print(f"❌ {scraper_name} failed with return code {result.returncode}")
            print(f"Error output: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {scraper_name} timed out after 5 minutes")
    except Exception as e:
        print(f"❌ Error running {scraper_name}: {e}")
    finally:
        # Change back to original directory
        os.chdir(original_dir)

def main():
    """Run all scrapers"""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    scrapers_dir = project_root / "data" / "scrapers"
    output_dir = project_root / "data" / "scraped_raw_data"
    
    print(f"🔍 Looking for scrapers in: {scrapers_dir}")
    print(f"📁 Output directory: {output_dir}")
    
    # Find all Python files in the scrapers directory
    scraper_files = list(scrapers_dir.glob("*.py"))
    
    if not scraper_files:
        print("❌ No scraper files found!")
        return
    
    print(f"\n📋 Found {len(scraper_files)} scrapers:")
    for scraper in scraper_files:
        print(f"  - {scraper.name}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Run each scraper
    for scraper_file in scraper_files:
        run_scraper(scraper_file, output_dir)
        time.sleep(2)  # Small delay between scrapers
    
    print(f"\n{'='*50}")
    print("🎉 All scrapers completed!")
    print(f"📁 Check {output_dir} for output files")
    print(f"{'='*50}")

if __name__ == "__main__":
    main() 