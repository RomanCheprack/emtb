#!/usr/bin/env python3
"""
Utility script to clear undetected_chromedriver cache.
This forces undetected_chromedriver to re-download the correct ChromeDriver version.
"""
import os
import sys
import shutil
from pathlib import Path

def clear_chromedriver_cache():
    """Clear the undetected_chromedriver cache directory"""
    if os.name == 'nt':  # Windows
        cache_dir = Path(os.path.expanduser("~/appdata/roaming/undetected_chromedriver"))
    elif os.getenv("LAMBDA_TASK_ROOT"):
        cache_dir = Path("/tmp/undetected_chromedriver")
    elif os.name == 'posix':
        if sys.platform == 'darwin':
            cache_dir = Path(os.path.expanduser("~/Library/Application Support/undetected_chromedriver"))
        else:
            cache_dir = Path(os.path.expanduser("~/.local/share/undetected_chromedriver"))
    else:
        cache_dir = Path(os.path.expanduser("~/.undetected_chromedriver"))
    
    if cache_dir.exists():
        print(f"Found cache directory: {cache_dir}")
        try:
            # List files before deletion
            files = list(cache_dir.glob("*"))
            if files:
                print(f"Found {len(files)} file(s) to delete:")
                for f in files:
                    print(f"  - {f.name} ({f.stat().st_size / 1024 / 1024:.2f} MB)")
                
                # Delete all files
                for f in files:
                    try:
                        if f.is_file():
                            f.unlink()
                        elif f.is_dir():
                            shutil.rmtree(f)
                        print(f"  ✓ Deleted: {f.name}")
                    except Exception as e:
                        print(f"  ✗ Failed to delete {f.name}: {e}")
                
                print(f"\n✅ Cache cleared successfully!")
            else:
                print("Cache directory is already empty.")
        except Exception as e:
            print(f"❌ Error clearing cache: {e}")
    else:
        print(f"Cache directory does not exist: {cache_dir}")

if __name__ == "__main__":
    import sys
    clear_chromedriver_cache()
