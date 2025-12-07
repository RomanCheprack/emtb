# -*- coding: utf-8 -*-
"""
Script to check that all target URLs for scrapers are valid and not leading to 404 errors
or irrelevant content.
"""
import ast
import re
import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Tuple
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Configuration
TIMEOUT = 15  # seconds
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'he,en-US;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'DNT': '1'
}

# Keywords that suggest relevant bike content (Hebrew and English)
RELEVANT_KEYWORDS = [
    'אופני', 'אופניים', 'bike', 'bicycle', 'cycle',
    'mtb', 'mountain', 'שטח', 'הרים',
    'electric', 'חשמלי', 'e-bike',
    'road', 'כביש', 'city', 'עיר',
    'kids', 'ילדים'
]

ERROR_KEYWORDS = [
    '404', 'not found', 'page not found', 'error',
    'הדף לא נמצא', 'שגיאה', 'לא נמצא'
]


def extract_target_urls_from_file(file_path: Path) -> Tuple[str, List[Dict]]:
    """
    Extract TARGET_URLS list from a Python scraper file by importing the module.
    Returns (scraper_name, list_of_url_dicts)
    """
    import importlib.util
    import sys
    import io
    import contextlib
    
    # Get module name from file path
    module_name = file_path.stem
    
    # Suppress stdout/stderr during import to avoid noise from scraper execution
    @contextlib.contextmanager
    def suppress_stdout_stderr():
        with open(os.devnull, 'w') as devnull:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            try:
                sys.stdout = devnull
                sys.stderr = devnull
                yield
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
    
    try:
        # Load the module from file path
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            print(f"⚠️ Could not create spec for {file_path.name}")
            return None, []
        
        # Import the module while suppressing output (some scrapers print/run code at import time)
        module = None
        try:
            with suppress_stdout_stderr():
                module = importlib.util.module_from_spec(spec)
                # Temporarily add to sys.modules to allow imports within the module
                sys.modules[module_name] = module
                # Set up a mock environment to prevent actual execution
                # Some scrapers try to initialize drivers, we'll catch those errors
                try:
                    spec.loader.exec_module(module)
                except (SystemExit, KeyboardInterrupt):
                    # Some scrapers call exit() at module level, ignore it
                    pass
                except Exception as import_error:
                    # If import fails (e.g., driver init, missing deps), try to still get TARGET_URLS
                    # The variable might already be set before the error
                    pass
        except Exception as e:
            # If we can't even create the module, fail gracefully
            if module_name in sys.modules:
                del sys.modules[module_name]
            print(f"⚠️ Could not import {file_path.name}: {type(e).__name__}")
            return None, []
        
        if module is None:
            if module_name in sys.modules:
                del sys.modules[module_name]
            return None, []
        
        # Find the TARGET_URLS variable (it might be named differently)
        target_urls = None
        var_name = None
        
        # Look for variables ending in _TARGET_URLS
        try:
            for attr_name in dir(module):
                if attr_name.endswith('_TARGET_URLS') and not attr_name.startswith('_'):
                    attr_value = getattr(module, attr_name, None)
                    if attr_value is not None:
                        target_urls = attr_value
                        var_name = attr_name
                        break
        except Exception:
            pass
        
        # Clean up
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        if target_urls is None:
            return None, []
        
        if not isinstance(target_urls, list):
            print(f"⚠️ {var_name} in {file_path.name} is not a list")
            return None, []
        
        scraper_name = var_name.replace('_TARGET_URLS', '').lower()
        
        return scraper_name, target_urls
        
    except Exception as e:
        # Clean up on any error
        if module_name in sys.modules:
            try:
                del sys.modules[module_name]
            except:
                pass
        print(f"⚠️ Error processing {file_path.name}: {type(e).__name__}: {e}")
        return None, []


def check_url(url: str, scraper_name: str, session: requests.Session, url_info: Dict = None) -> Dict:
    """
    Check if a URL is valid and returns relevant content.
    Returns a dict with status information.
    """
    result = {
        'url': url,
        'scraper': scraper_name,
        'status_code': None,
        'is_valid': False,
        'has_relevant_content': False,
        'error': None,
        'redirect_to': None,
        'page_size': 0,
        'content_type': None
    }
    
    try:
        # Make request with session (maintains cookies and connection pooling)
        # Add Referer header based on the base URL to make it look more like browser navigation
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        headers_with_referer = HEADERS.copy()
        headers_with_referer['Referer'] = base_url
        
        response = session.get(url, headers=headers_with_referer, timeout=TIMEOUT, allow_redirects=True)
        result['status_code'] = response.status_code
        result['content_type'] = response.headers.get('Content-Type', '')
        result['page_size'] = len(response.content)
        
        # Check if redirected
        if response.history:
            result['redirect_to'] = response.url
        
        # Check status code
        if response.status_code == 404:
            result['error'] = '404 Not Found'
            return result
        
        if response.status_code >= 400:
            result['error'] = f'HTTP {response.status_code}'
            return result
        
        # If not HTML, might not be relevant
        if 'text/html' not in result['content_type']:
            result['error'] = f'Not HTML content: {result["content_type"]}'
            return result
        
        # Parse HTML to check for relevant content
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text().lower()
            title = soup.find('title')
            title_text = title.get_text().lower() if title else ''
            
            # Check for error indicators in page
            if any(keyword in page_text or keyword in title_text for keyword in ERROR_KEYWORDS):
                result['error'] = 'Page contains error indicators'
                return result
            
            # Check for relevant bike-related keywords
            has_keywords = any(keyword.lower() in page_text or keyword.lower() in title_text 
                             for keyword in RELEVANT_KEYWORDS)
            
            result['is_valid'] = True
            result['has_relevant_content'] = has_keywords
            
            # If page is suspiciously small, it might be an error page
            if result['page_size'] < 1000:
                result['error'] = f'Page too small ({result["page_size"]} bytes), might be error page'
                result['is_valid'] = False
            
        except Exception as e:
            result['error'] = f'Error parsing HTML: {e}'
            result['is_valid'] = True  # Assume valid if we can't parse (might be JS-only)
        
    except requests.exceptions.Timeout:
        result['error'] = 'Request timeout'
    except requests.exceptions.ConnectionError:
        result['error'] = 'Connection error'
    except requests.exceptions.RequestException as e:
        result['error'] = f'Request error: {e}'
    except Exception as e:
        result['error'] = f'Unexpected error: {e}'
    
    return result


def main():
    """Main function to check all scraper URLs."""
    scrapers_dir = Path(__file__).parent
    scraper_files = list(scrapers_dir.glob('*_full_site.py'))
    
    if not scraper_files:
        print("❌ No scraper files found!")
        return
    
    print(f"🔍 Found {len(scraper_files)} scraper files\n")
    
    # Create a session to maintain cookies and connection pooling
    session = requests.Session()
    session.headers.update(HEADERS)
    
    all_results = []
    total_urls = 0
    valid_urls = 0
    invalid_urls = 0
    
    for scraper_file in sorted(scraper_files):
        scraper_name, urls = extract_target_urls_from_file(scraper_file)
        
        if not scraper_name or not urls:
            print(f"⚠️ Skipping {scraper_file.name}: No TARGET_URLS found")
            continue
        
        print(f"\n{'='*70}")
        print(f"📋 Checking {scraper_name.upper()} ({scraper_file.name})")
        print(f"{'='*70}")
        print(f"Found {len(urls)} target URLs\n")
        
        for idx, url_entry in enumerate(urls, 1):
            # Handle both dict format {"url": "...", ...} and direct string format
            if isinstance(url_entry, dict):
                url = url_entry.get('url', '')
                category = url_entry.get('category', 'N/A')
                sub_category = url_entry.get('sub_category', 'N/A')
            elif isinstance(url_entry, str):
                url = url_entry
                category = 'N/A'
                sub_category = 'N/A'
            else:
                print(f"  ⚠️ Entry {idx}: Invalid format")
                continue
            
            if not url:
                print(f"  ⚠️ Entry {idx}: Empty URL")
                invalid_urls += 1
                continue
            
            print(f"  [{idx}/{len(urls)}] {url}")
            if isinstance(url_entry, dict):
                print(f"      Category: {category} | Sub-category: {sub_category}")
            
            result = check_url(url, scraper_name, session, url_entry)
            all_results.append(result)
            
            # Small delay between requests to avoid rate limiting
            time.sleep(0.5)
            total_urls += 1
            
            if result['is_valid'] and result['has_relevant_content']:
                print(f"      ✅ Valid - Status {result['status_code']}, {result['page_size']} bytes")
                valid_urls += 1
            elif result['is_valid']:
                print(f"      ⚠️  Valid but no relevant keywords - Status {result['status_code']}, {result['page_size']} bytes")
                valid_urls += 1
            else:
                print(f"      ❌ Invalid - {result['error'] or 'Unknown error'}")
                if result['status_code']:
                    print(f"         Status: {result['status_code']}")
                invalid_urls += 1
            
            if result.get('redirect_to') and result['redirect_to'] != url:
                print(f"      🔄 Redirected to: {result['redirect_to']}")
        
        print()
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 SUMMARY")
    print(f"{'='*70}")
    print(f"Total URLs checked: {total_urls}")
    print(f"✅ Valid URLs: {valid_urls}")
    print(f"❌ Invalid URLs: {invalid_urls}")
    
    if invalid_urls > 0:
        print(f"\n❌ INVALID URLs DETAILS:")
        print(f"{'='*70}")
        for result in all_results:
            if not result['is_valid'] or not result['has_relevant_content']:
                print(f"\nScraper: {result['scraper'].upper()}")
                print(f"URL: {result['url']}")
                if result['status_code']:
                    print(f"Status: {result['status_code']}")
                if result['error']:
                    print(f"Error: {result['error']}")
                if result['redirect_to']:
                    print(f"Redirect: {result['redirect_to']}")
        
        print(f"\n{'='*70}")
        session.close()
        return 1  # Exit with error code
    else:
        print("\n✅ All URLs are valid!")
        session.close()
        return 0


if __name__ == '__main__':
    sys.exit(main())
