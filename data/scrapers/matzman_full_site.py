# -*- coding: utf-8 -*-
import time
import re
import json
import os
from pathlib import Path
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Constants ---
BASE_URL = "https://www.matzman-merutz.co.il"

HEBREW_TO_ENGLISH_KEYS = {
    "שנתון:": "year", "סוג אופניים:": "bike_type", "סדרות אופניים:": "bike_series",
    "שלדה:": "frame", "מזלג-בולם קדמי:": "fork", "בולם אחורי:": "rear_shock",
    "מוט כידון:": "stem", "כידון:": "handlebar", "מעצור קדמי:": "front_brake",
    "מעצור אחורי:": "rear_brake", "ידיות מעצורים:": "brake_levers",
    "מספר הילוכים:": "number_of_gears", "מעביר אחורי:": "rear_derailleur",
    "קסטה:": "cassette", "שרשרת:": "chain", "קראנק:": "crankset",
    "ציר מרכזי:": "bottom_bracket", "חישוקים:": "rims", "ציר קדמי:": "front_hub",
    "ציר אחורי:": "rear_hub", "צמיג קדמי:": "front_tire", "צמיג אחורי:": "rear_tire",
    "אוכף:": "saddle", "חבק מוט כיסא:": "seatpost_clamp", "מנוע חשמלי:": "motor",
    "סוללה:": "battery", "מטען:": "charger", "גודל גלגל:": "wheel_size",
    "ידיות הילוכים:": "shifters", "פנימיות:": "tubes", "מוט כיסא:": "seatpost",
    "תצוגת בקרה:": "display", "גלגל קדמי:": "front_wheel", "תוספות:": "additionals",
    "גלגל אחורי:": "rear_wheel", "דוושות": "pedals", "דוושות:": "pedals"
}

MATZMAN_TARGET_URLS = [
    {"url": f"{BASE_URL}/electric-mountain-bikes", "category": "electric", "sub_category": "electric_mtb"},
    {"url": f"{BASE_URL}/electric-bicycle", "category": "electric", "sub_category": "electric_city"},
    {"url": f"{BASE_URL}/hardtail", "category": "mtb", "sub_category": "hardtail"},
    {"url": f"{BASE_URL}/full-suspension", "category": "mtb", "sub_category": "full_suspension"},
    {"url": f"{BASE_URL}/city-bike", "category": "city", "sub_category": "city"},
    {"url": f"{BASE_URL}/folding-bicycle", "category": "city", "sub_category": "folding_city"},
    {"url": f"{BASE_URL}/gravel", "category": "gravel", "sub_category": "gravel"},
    {"url": f"{BASE_URL}/electric-gravel", "category": "electric", "sub_category": "electric_gravel"},
    {"url": f"{BASE_URL}/road-bike", "category": "road", "sub_category": "road"},
    {"url": f"{BASE_URL}/kids-bike-bmx","category": "kids", "sub_category": "kids"},
    {"url": f"{BASE_URL}/triathlon-bike", "category": "road", "sub_category": "time_trial"},
    {"url": f"{BASE_URL}/kids-mtb-bikes", "category": "kids", "sub_category": "kids_mtb"},
    {"url": f"{BASE_URL}/balance-bike", "category": "kids", "sub_category": "pushbike"},
    {"url": f"{BASE_URL}/אופני-פעלולים", "category": "bmx&dirt", "sub_category": "bmx&dirt", "style": "Bmx & Dirt"},
]

CHATGPT_API_KEY = os.getenv('SCRAPER_OPENAI_API_KEY', '')

# --- Hebrew phrases to filter out ---
HEBREW_FILTER_PHRASES = [
    "אופני עיר",
    "אופני הרים חשמליים",
    "אופני הרים שיכוך מלא",
    "אופני הרים זנב קשיח",
    "אופני עיר חשמליים",
    "שילדת אופני הרים חשמליים",
    "שילדת אופני הרים שיכוך מלא",
]

# --- Helper Functions ---
def parse_price(text):
    if not text:
        return None
    match = re.search(r'\d+', text.replace(',', '').replace('₪',''))
    return int(match.group()) if match else None

def extract_fork_length(fork_text):
    if not fork_text:
        return None
    
    fork_text_lower = fork_text.lower()
    
    # First, try to find travel-specific patterns (most reliable)
    # Patterns: "160mm of travel", "travel 160mm", "160mm travel", etc.
    travel_patterns = [
        r'(\d+)\s*mm\s+of\s+travel',  # "160mm of travel"
        r'travel\s+of\s+(\d+)\s*mm',   # "travel of 160mm"
        r'travel[:\s]+(\d+)\s*mm',     # "travel: 160mm" or "travel 160mm"
        r'(\d+)\s*mm\s+travel',        # "160mm travel"
    ]
    
    for pattern in travel_patterns:
        match = re.search(pattern, fork_text_lower)
        if match:
            value = int(match.group(1))
            # Validate it's a reasonable fork travel value
            if value in [40, 60, 80, 100, 110, 120, 130, 140, 150, 160, 170, 180]:
                return value
    
    # If no travel-specific pattern found, look for common fork travel values
    # Exclude 110 (common hub size) and other non-fork values
    common_fork_lengths = [40, 60, 80, 100, 120, 130, 140, 150, 160, 170, 180]
    all_matches = re.findall(r'(\d+)\s*mm', fork_text_lower)
    fork_lengths = []
    for match in all_matches:
        value = int(match)
        if value in common_fork_lengths:
            fork_lengths.append(value)
    
    # Return the maximum value if multiple found (usually the travel is the largest)
    if fork_lengths:
        return max(fork_lengths)
    
    return None

def determine_bike_style(fork_length):
    if not fork_length:
        return None
    if fork_length in [40,60,80,100,110,120]:
        return "cross-country"
    elif fork_length in [130,140,150]:
        return "trail"
    elif fork_length in [160,170,180]:
        return "enduro"
    return None

def clean_hebrew_phrases(text):
    """
    Remove Hebrew filter phrases from text.
    
    Args:
        text: The text to clean (string)
    
    Returns:
        str: The cleaned text with Hebrew phrases removed
    """
    if not text or not isinstance(text, str):
        return text
    
    cleaned_text = text
    for phrase in HEBREW_FILTER_PHRASES:
        # Remove the phrase and any surrounding whitespace
        cleaned_text = cleaned_text.replace(phrase, "")
    
    # Clean up multiple spaces and trim
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    return cleaned_text

def rewrite_description_with_chatgpt(original_text, api_key):
    if not original_text or not api_key:
        return original_text
    try:
        import requests
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "אתה מומחה לכתיבת תוכן שיווקי לאופניים..."},
                {"role": "user", "content": f"להלן תיאור האופניים:\n\n{original_text}\n\nאנא כתוב גרסה שיווקית חדשה..."}
            ],
            "temperature": 0.6,
            "max_tokens": 500
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except:
        return original_text

# --- Selenium driver for JS-only pages ---
def create_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-logging')
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    )
    driver = uc.Chrome(options=options, version_main=144)
    driver.set_page_load_timeout(60)
    return driver

def is_driver_alive(driver):
    try:
        driver.current_url
        return True
    except:
        return False

# --- Scraping Functions ---
def scrape_listing_page(url):
    """Fast Requests + BS4 for listing page"""
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("div", class_="col-xs-12 col-sm-6 col-md-4 col-lg-4")
        return cards
    except:
        return []

def scrape_product_page(driver, url, product_num=None):
    """Selenium for JS-heavy product pages
    Returns: (data_dict, driver_needs_recreation_bool, page_was_small_bool)
    """
    product_info = f"[Product #{product_num}]" if product_num else ""
    driver_broken = False
    try:
        # Check if driver is alive before starting
        if not is_driver_alive(driver):
            print(f"  ❌ {product_info} Driver not alive at start for {url}")
            return {}, True, False
        
        # Set shorter timeout for page load to prevent hanging
        driver.set_page_load_timeout(15)  # 15 second max per page
        try:
            driver.get(url)
        except Exception as e:
            print(f"  ⚠️ {product_info} Page load error: {type(e).__name__}: {str(e)}")
            # Page load timed out - try to stop and continue
            try:
                driver.execute_script("window.stop();")
                print(f"  ✓ {product_info} Stopped page load")
            except Exception as stop_e:
                print(f"  ❌ {product_info} Cannot execute stop script: {type(stop_e).__name__}: {str(stop_e)}")
                driver_broken = True  # Driver might be broken if we can't execute script
            # Check if driver is still alive after error
            if not is_driver_alive(driver):
                print(f"  ❌ {product_info} Driver died after page load error")
                return {}, True, False
        
        # Wait for page ready state
        try:
            WebDriverWait(driver, 5).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception as e:
            print(f"  ⚠️ {product_info} Page ready state wait failed: {type(e).__name__}: {str(e)}")
            # Check if driver is still alive
            if not is_driver_alive(driver):
                print(f"  ❌ {product_info} Driver died after ready state wait")
                return {}, True, False
        
        # Wait for specs element to appear (it's loaded dynamically)
        try:
            WebDriverWait(driver, 8).until(
                lambda d: (
                    len(d.find_elements(By.CSS_SELECTOR, "ul.list-unstyled.properties-product")) > 0 or
                    len(d.find_elements(By.CSS_SELECTOR, "ul.properties-product")) > 0 or
                    len(d.find_elements(By.CSS_SELECTOR, "div.properties-product")) > 0
                )
            )
        except Exception as e:
            print(f"  ⚠️ {product_info} Specs element wait failed: {type(e).__name__}: {str(e)}")
            # If specs element doesn't appear, wait a bit more for lazy loading
            print(f"  ⏳ {product_info} Waiting additional 2 seconds for lazy loading...")
            time.sleep(2)
            # Check if driver is still alive
            if not is_driver_alive(driver):
                print(f"  ❌ {product_info} Driver died after specs wait")
                return {}, True, False
        
        # Additional delay for any remaining lazy-loaded content
        time.sleep(1)
        
        # Check current URL - might have redirected
        try:
            current_url = driver.current_url
            if current_url != url:
                pass  # URL changed, but no need to log it
        except:
            pass
        
        # Try to get page source - this can fail if driver is broken
        page_was_small = False
        try:
            page_source = driver.page_source
            
            # Check if page source is suspiciously small (might be error page or blocked)
            page_was_small = len(page_source) < 5000
            if page_was_small:
                print(f"  ⚠️ {product_info} Page source is very small ({len(page_source)} chars), might be error/blocked page")
                # Check if it's an error page
                if "error" in page_source.lower() or "blocked" in page_source.lower() or "access denied" in page_source.lower():
                    print(f"  ❌ {product_info} Page appears to be blocked or error page")
                    return {}, False, True  # Don't recreate driver, but mark as small page
                # Show first 500 chars for debugging
                preview = page_source[:500].replace('\n', ' ').replace('\r', '')
                print(f"  📋 {product_info} Page preview: {preview}...")
        except Exception as e:
            print(f"  ❌ {product_info} Cannot get page source: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"  📋 {product_info} Traceback:\n{traceback.format_exc()}")
            return {}, True, False
        
        soup = BeautifulSoup(page_source, "html.parser")
        data = {}

        # --- Description ---
        desc_el = soup.find("div", id="text_for_list")
        original_desc = desc_el.get_text(strip=True) if desc_el else ""
        data["rewritten_description"] = rewrite_description_with_chatgpt(original_desc, CHATGPT_API_KEY) if CHATGPT_API_KEY else original_desc

        # --- Images ---
        img_tags = soup.select('.sp-thumbnails img')
        gallery_images = [urljoin(BASE_URL, img.get('src')) for img in img_tags if img.get('src')]
        
        # Use first gallery image as image_url if available
        image_url = gallery_images[0] if gallery_images else None
        
        data["images"] = {
            "image_url": image_url,
            "gallery_images_urls": gallery_images
        }

        # --- Specs ---
        spec_list = soup.find("ul", class_="list-unstyled properties-product")
        specs = {}
        if spec_list:
            for li in spec_list.find_all("li"):
                # Try multiple ways to find the key and value
                key_tag = li.find("span", class_="titleKey") or li.find("span", class_="title")
                val_tag = li.find("span", class_="valueKey") or li.find("span", class_="value")
                # If still not found, try finding by text pattern
                if not key_tag or not val_tag:
                    spans = li.find_all("span")
                    if len(spans) >= 2:
                        key_tag = spans[0]
                        val_tag = spans[1]
                
                if key_tag and val_tag:
                    key_text = key_tag.get_text(strip=True)
                    val_text = val_tag.get_text(strip=True)
                    if key_text and val_text:
                        key_en = HEBREW_TO_ENGLISH_KEYS.get(key_text, key_text)
                        specs[key_en.lower()] = val_text
        
        # If no specs found, try alternative selector
        if not specs:
            alt_spec_list = soup.find("ul", class_="properties-product") or soup.find("div", class_="properties-product")
            if alt_spec_list:
                for li in alt_spec_list.find_all("li"):
                    # Try finding spans with title/key classes
                    spans = li.find_all("span")
                    key_tag = None
                    val_tag = None
                    for span in spans:
                        span_class = span.get("class", [])
                        span_class_str = " ".join(span_class).lower()
                        if "title" in span_class_str or "key" in span_class_str:
                            key_tag = span
                        elif "value" in span_class_str:
                            val_tag = span
                    
                    # Fallback: try finding by position or text pattern
                    if not key_tag:
                        key_tag = li.find("strong") or (spans[0] if spans else None)
                    if not val_tag and spans:
                        val_tag = spans[1] if len(spans) > 1 else None
                    
                    # Try splitting by colon if we have text but no tags
                    if key_tag and not val_tag:
                        li_text = li.get_text(strip=True)
                        if ":" in li_text:
                            parts = li_text.split(":", 1)
                            key_text = parts[0].strip()
                            val_text = parts[1].strip()
                            if key_text and val_text:
                                key_en = HEBREW_TO_ENGLISH_KEYS.get(key_text, key_text)
                                specs[key_en.lower()] = val_text
                            continue
                    
                    if key_tag:
                        key_text = key_tag.get_text(strip=True).rstrip(":")
                        val_text = val_tag.get_text(strip=True) if val_tag else ""
                        if key_text and val_text:
                            key_en = HEBREW_TO_ENGLISH_KEYS.get(key_text, key_text)
                            specs[key_en.lower()] = val_text
        
        data["specs"] = specs

        # --- Fork & Style ---
        fork_length = extract_fork_length(specs.get("fork",""))
        data["fork length"] = fork_length
        data["style"] = determine_bike_style(fork_length)

        # --- Battery Wh ---
        battery_val = specs.get("battery","")
        wh_match = re.search(r"(\d+)\s*Wh", battery_val, re.IGNORECASE)
        if wh_match:
            data["wh"] = int(wh_match.group(1))
        else:
            fallback_match = re.search(r"\b(\d{3})\b", battery_val)
            if fallback_match:
                data["wh"] = int(fallback_match.group(1))
        
        # Final check - verify driver is still alive before returning
        if not is_driver_alive(driver):
            print(f"  ❌ {product_info} Driver died before returning data")
            return data, True, page_was_small
        
        return data, False, page_was_small
    except Exception as e:
        print(f"  ❌ {product_info} EXCEPTION in scrape_product_page for {url}")
        print(f"  📋 {product_info} Exception type: {type(e).__name__}")
        print(f"  📋 {product_info} Exception message: {str(e)}")
        import traceback
        print(f"  📋 {product_info} Full traceback:\n{traceback.format_exc()}")
        # Check if driver is broken after exception
        if not is_driver_alive(driver):
            print(f"  ❌ {product_info} Driver is broken after exception")
            return {}, True, False
        return {}, False, False

def scrape_matzman(output_file):
    driver = create_driver()
    scraped_data = []
    
    # Clear the output file at the start
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=4)
    print(f"🗑️ Cleared output file: {output_file}")

    for entry in MATZMAN_TARGET_URLS:
        category = entry["category"]
        sub_category = entry.get("sub_category")
        print(f"🌐 Scraping category: {category} | URL: {entry['url']}")
        cards = scrape_listing_page(entry["url"])
        print(f"✅ Found {len(cards)} products")

        product_counter = 0
        success_count = 0
        fail_count = 0
        consecutive_small_pages = 0  # Track consecutive small page sources
        failed_products = []  # Track failed products with details for this category
        for card in cards:
            product_counter += 1
            
            # Check if driver is still alive before each product
            if not is_driver_alive(driver):
                print(f"⚠️ [Product #{product_counter}] WebDriver is not responding, recreating...")
                try:
                    driver.quit()
                except Exception as e:
                    print(f"  ⚠️ Error quitting old driver: {e}")
                driver = create_driver()
                if not driver:
                    print("❌ Cannot continue without a working WebDriver")
                    break
            
            link_tag = card.find("a")
            product_url = urljoin(BASE_URL, link_tag.get("href")) if link_tag else None
            if not product_url:
                model_tag = card.find("h2")
                model_text = model_tag.get_text(strip=True) if model_tag else "N/A"
                print(f"  ⚠️ [Product #{product_counter}] No product URL found, skipping")
                fail_count += 1
                failed_products.append({
                    "product_num": product_counter,
                    "firm": "N/A",
                    "model": model_text,
                    "url": None,
                    "reason": "No product URL found"
                })
                continue

            model_tag = card.find("h2")
            model_text = model_tag.get_text(strip=True) if model_tag else "N/A"

            price_el = card.find("span", "saleprice") or card.find("span", "oldprice")
            original_price = parse_price(price_el.get_text(strip=True)) if price_el else None
            if not original_price:
                print(f"  ⚠️ [Product #{product_counter}] {model_text}: No price found, skipping")
                fail_count += 1
                firm_tag = card.find("div", "firm")
                firm_text = firm_tag.get_text(strip=True).capitalize() if firm_tag else "N/A"
                failed_products.append({
                    "product_num": product_counter,
                    "firm": firm_text,
                    "model": model_text,
                    "url": product_url,
                    "reason": "No price found"
                })
                continue

            firm_tag = card.find("div", "firm")
            firm_text = firm_tag.get_text(strip=True).capitalize() if firm_tag else "N/A"

            year_tag = card.find('div', 'newOnSite')
            year_val = int(year_tag.get_text(strip=True)) if year_tag and year_tag.get_text(strip=True).isdigit() else None

            # Extract main image from listing card
            card_img_tag = card.find("img")
            card_image_url = None
            if card_img_tag:
                img_src = card_img_tag.get('src') or card_img_tag.get('data-src') or card_img_tag.get('data-lazy-src')
                if img_src:
                    card_image_url = urljoin(BASE_URL, img_src)

            print(f"  📦 [Product #{product_counter}] {firm_text} {model_text} ({year_val if year_val else 'N/A'})")

            # Add delay between requests to avoid rate limiting (except for first product)
            if product_counter > 1:
                delay = 2  # 2 second delay between requests
                time.sleep(delay)

            # Scrape product page if necessary
            product_details, driver_needs_recreation, page_was_small = scrape_product_page(driver, product_url, product_counter)
            
            # Track consecutive small pages (might indicate rate limiting or driver issues)
            if page_was_small:
                consecutive_small_pages += 1
                print(f"  ⚠️ [Product #{product_counter}] Consecutive small pages: {consecutive_small_pages}")
                # If we get 3 consecutive small pages, recreate driver
                if consecutive_small_pages >= 3:
                    print(f"  🔄 [Product #{product_counter}] Got {consecutive_small_pages} consecutive small pages, recreating driver...")
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = create_driver()
                    consecutive_small_pages = 0
            else:
                consecutive_small_pages = 0  # Reset counter on success
            
            # If driver needs recreation, recreate it and retry once
            if driver_needs_recreation:
                print(f"  🔄 [Product #{product_counter}] Driver broken, recreating for {model_text}...")
                try:
                    driver.quit()
                except Exception as e:
                    print(f"  ⚠️ [Product #{product_counter}] Error quitting old driver: {e}")
                driver = create_driver()
                if not driver:
                    print(f"  ❌ [Product #{product_counter}] Cannot continue without a working WebDriver")
                    break
                # Retry once with new driver
                product_details, driver_needs_recreation, page_was_small = scrape_product_page(driver, product_url, product_counter)
                if page_was_small:
                    consecutive_small_pages += 1
                else:
                    consecutive_small_pages = 0
                if driver_needs_recreation:
                    print(f"  ❌ [Product #{product_counter}] Still failing after driver recreation for {model_text}, skipping...")
                    product_details = {}  # Use empty dict if still failing
            
            # Debug output for specs extraction
            if product_details and product_details.get("specs"):
                specs_count = len(product_details.get("specs", {}))
                if specs_count > 0:
                    print(f"  ✅ [Product #{product_counter}] {model_text}: Found {specs_count} specs")
                    success_count += 1
                else:
                    print(f"  ⚠️ [Product #{product_counter}] {model_text}: No specs found (empty dict)")
                    fail_count += 1
                    failed_products.append({
                        "product_num": product_counter,
                        "firm": firm_text,
                        "model": model_text,
                        "url": product_url,
                        "reason": "No specs found (empty dict)"
                    })
            else:
                print(f"  ⚠️ [Product #{product_counter}] {model_text}: Failed to scrape product page (no data returned)")
                fail_count += 1
                failed_products.append({
                    "product_num": product_counter,
                    "firm": firm_text,
                    "model": model_text,
                    "url": product_url,
                    "reason": "Failed to scrape product page (no data returned)"
                })

            # Prepare images data - use card image as image_url, or fallback to first gallery image
            images_data = product_details.get("images", {}) if product_details else {}
            if not images_data.get("image_url"):
                # If no image_url from product page, use card image or first gallery image
                if card_image_url:
                    images_data["image_url"] = card_image_url
                elif images_data.get("gallery_images_urls") and len(images_data["gallery_images_urls"]) > 0:
                    images_data["image_url"] = images_data["gallery_images_urls"][0]
            # Ensure gallery_images_urls exists
            if "gallery_images_urls" not in images_data:
                images_data["gallery_images_urls"] = []

            product_data = {
                "source": {"importer": "Matzman-Merutz","domain": BASE_URL,"product_url": product_url},
                "firm": firm_text, "model": model_text, "year": year_val,
                "category": category, "sub_category": sub_category,
                "original_price": original_price,
                "disc_price": None,
                "images": images_data,
                "specs": product_details.get("specs", {}) if product_details else {},
                "fork length": product_details.get("fork length") if product_details else None,
                "style": product_details.get("style") if product_details else None,
                "rewritten_description": product_details.get("rewritten_description") if product_details else None,
                "wh": product_details.get("wh") if product_details else None
            }
            
            # Normalize keys to lowercase (as per memory)
            product_data = {k.lower(): v for k, v in product_data.items()}
            if isinstance(product_data.get("specs"), dict):
                product_data["specs"] = {k.lower(): v for k, v in product_data["specs"].items()}
            
            # Clean Hebrew phrases from model name
            original_model = product_data.get("model", "")
            cleaned_model = clean_hebrew_phrases(original_model)
            if original_model != cleaned_model:
                print(f"  🧹 [Product #{product_counter}] Cleaned model: '{original_model}' -> '{cleaned_model}'")
                product_data["model"] = cleaned_model
            
            # Clean Hebrew phrases from bike_type in specs
            if product_data.get("specs") and isinstance(product_data["specs"], dict):
                original_bike_type = product_data["specs"].get("bike_type", "")
                if original_bike_type:
                    cleaned_bike_type = clean_hebrew_phrases(original_bike_type)
                    if original_bike_type != cleaned_bike_type:
                        print(f"  🧹 [Product #{product_counter}] Cleaned bike_type: '{original_bike_type}' -> '{cleaned_bike_type}'")
                        product_data["specs"]["bike_type"] = cleaned_bike_type
            
            scraped_data.append(product_data)

        # Summary for this category
        print(f"\n{'='*60}")
        print(f"Category '{category}' Summary:")
        print(f"  Total products: {len(cards)}")
        print(f"  Successfully scraped (with specs): {success_count}")
        print(f"  Failed/No specs: {fail_count}")
        print(f"  Success rate: {(success_count/len(cards)*100):.1f}%" if len(cards) > 0 else "  Success rate: N/A")
        
        # Display failed products if any
        if failed_products:
            print(f"\n  ❌ Failed Products ({len(failed_products)}):")
            for failed in failed_products:
                print(f"    • Product #{failed['product_num']}: {failed['firm']} {failed['model']}")
                print(f"      URL: {failed['url']}")
                print(f"      Reason: {failed['reason']}")
        
        print(f"{'='*60}\n")

        # Save after each category
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, ensure_ascii=False, indent=4)
        print(f"💾 Saved {len(scraped_data)} products so far\n")

    driver.quit()
    return scraped_data

# --- Setup Output ---
if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "data" / "scraped_raw_data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = output_dir / "matzman_data.json"

    # --- Run Scraper ---
    products = scrape_matzman(output_file)
    print(f"\n✅ Scraping completed. Total products scraped: {len(products)}")
    print(f"💾 Final data saved to: {output_file}")
