import time
import re
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc
from openai import OpenAI
from dotenv import load_dotenv

# -------------------------------
# Setup
# -------------------------------
BASE_URL = "https://www.rosen-meents.co.il"
TARGET_URL = f"{BASE_URL}/אופני-הרים-חשמליים-E-MTB"

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Hebrew to English key mapping
HEBREW_TO_ENGLISH_KEYS = {
    "צבע": "color",
    "שלדה": "frame",
    "מידות": "sizes",
    "גימור / צבע": "finish_color",
    "בולם זעזועים קדמי": "fork",
    "בולם זעזועים אחורי": "rear_shock",
    "מערכת הינע": "drive_system",
    "הילוכים": "gears",
    "מעביר קדמי": "front_derailleur",
    "מעביר אחורי": "rear_derailleur",
    "מעבירי הילוכים (שיפטר)": "shifters",
    "קראנק": "crankset",
    "מעצורים": "brakes",
    "חישוקים": "rims",
    "צירי גלגל": "hubs",
    "סטם": "stem",
    "כידון": "handlebar",
    "מוט אוכף": "seatpost",
    "אוכף": "saddle",
    "דוושות (פדלים)": "pedals",
    "צמיגים": "tires",
    "סוללה": "battery",
    "מטען": "charger",
    "משקל": "weight",
    "טווח": "range",
    "מהירות": "speed",
    "כוח": "power"
}

scraped_data = []

# -------------------------------
# Helpers
# -------------------------------
def translate_hebrew_keys(specs_dict):
    translated_specs = {}
    for key, value in specs_dict.items():
        if key in HEBREW_TO_ENGLISH_KEYS:
            translated_specs[HEBREW_TO_ENGLISH_KEYS[key]] = value
        else:
            translated_specs[key] = value
    return translated_specs

def clean_product_data(product_data):
    """
    Clean product data by removing unwanted keys and flattening nested objects
    
    Removes:
    - _raw_specs_text: Raw text from GPT parsing (for debugging only)
    - system_weight_limit: System weight limit information
    
    Flattens nested objects by joining values with commas:
    - hubs: front/rear hub information
    - tires/tyre: front/rear tire information  
    - shifters: front/rear shifter information
    - derailleur: derailleur information
    - light: front/rear light information
    - handlebar: handlebar specifications
    - stem: stem specifications
    - seatpost: seatpost specifications
    - saddle: saddle specifications
    - sizes: size information (flatten complex geometry objects)
    
    Removes geometry-related keys that contain detailed measurements
    
    Returns cleaned product data dictionary
    """
    # Keys to remove completely
    keys_to_remove = ["_raw_specs_text", "system_weight_limit"]
    
    # Geometry-related keys to remove (detailed measurements)
    geometry_keys_to_remove = [
        "seat_tube", "top_tube", "chain_stay_length", "head_tube_angle", 
        "seat_tube_angle", "bottom_bracket_drop", "head_tube", "fork_length",
        "reach", "stack", "wheel_base", "stand_over_height", "tyre_sizes"
    ]
    
    # Remove unwanted keys
    cleaned_data = {}
    for key, value in product_data.items():
        if key not in keys_to_remove and key not in geometry_keys_to_remove:
            cleaned_data[key] = value
    
    # Flatten nested objects by joining values with commas
    keys_to_flatten = [
        "hubs", "tires", "tyre", "shifters", "derailleur", "light",
        "handlebar", "stem", "seatpost", "saddle"
    ]
    
    for key in keys_to_flatten:
        if key in cleaned_data and isinstance(cleaned_data[key], dict):
            # Join all values with commas
            values = []
            for sub_key, sub_value in cleaned_data[key].items():
                if isinstance(sub_value, str):
                    values.append(f"{sub_key}: {sub_value}")
                else:
                    values.append(f"{sub_key}: {str(sub_value)}")
            cleaned_data[key] = ", ".join(values)
    
    # Special handling for sizes - if it's a complex object with geometry, simplify it
    if "sizes" in cleaned_data and isinstance(cleaned_data["sizes"], dict):
        # Check if it's a complex geometry object (has nested objects with measurements)
        size_values = []
        for size_key, size_data in cleaned_data["sizes"].items():
            if isinstance(size_data, dict):
                # This is a complex geometry object, just keep the size name
                size_values.append(size_key)
            else:
                # This is a simple size value
                size_values.append(f"{size_key}: {size_data}")
        cleaned_data["sizes"] = ", ".join(size_values)
    
    return cleaned_data


# -------------------------------
# Old Extractors (fallbacks)
# -------------------------------
def extract_specs_p_br(soup):
    specs = {}
    paragraphs = soup.find_all("p")
    for p in paragraphs:
        parts = [line.strip() for line in p.decode_contents().split("<br>") if line.strip()]
        for part in parts:
            clean = BeautifulSoup(part, "html.parser").get_text().strip()
            if ":" in clean:
                key, value = clean.split(":", 1)
                specs[key.strip()] = value.strip()
            elif specs:
                last_key = list(specs.keys())[-1]
                specs[last_key] += " " + clean
    return specs

def extract_specs_table(soup):
    specs = {}
    spec_table = soup.find("table", class_="table")
    if spec_table:
        tbody = spec_table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) == 2:
                    key = cells[0].get_text(strip=True)
                    val = cells[1].get_text(strip=True)
                    if key and val:
                        specs[key] = val
    return specs

# -------------------------------
# GPT-powered extractor
# -------------------------------
def extract_product_specifications(driver, product_url):
    if not product_url:
        return {}

    try:
        print(f"🔍 Extracting specs from: {product_url}")
        driver.get(product_url)
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # STEP 1: Find the main specs container
        spec_container = soup.find("div", class_="tab-content tab-content-product-item")
        if not spec_container:
            print("⚠️ No spec container found")
            return {}

        # ✅ Preserve inner HTML instead of flattening
        raw_specs_html = spec_container.decode_contents()


        # STEP 2: Ask GPT to parse
        prompt = f"""
        You are given raw HTML product specification text from a bike webpage.

        Rules:
        1. Treat each <p>, <h4>, or <a> element as a possible key (e.g., "FRAME", "FORK").
        2. If the next sibling is a <ul> with <li> items, treat those <li> values as part of the same key.
        - Join them with " | " if multiple.
        - Example: 
            <p>FORK SR Suntour</p><ul><li>100mm</li><li>Tapered</li></ul>
            → "fork": "SR Suntour | 100mm | Tapered"
        3. Keep values exactly as they appear (don’t translate or guess).
        4. Output valid JSON with key-value pairs only.
        5. If the key is in Hebrew, try to map it to one of these English keys when possible:
        frame, sizes, finish_color, fork, rear_shock, drive_system, battery, assist_modes, 
        gears, front_derailleur, rear_derailleur, shifters, crankset, brakes, rims, hubs, 
        stem, handlebar, seatpost, saddle, pedals, tires, charger, weight, range, speed, power.
        6. If no mapping fits, keep the original key.

        HTML:
        {raw_specs_html}
        """


        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a JSON extractor for bike specifications."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )

        gpt_json = response.choices[0].message.content
        specs = json.loads(gpt_json)

        # STEP 3: Add raw specs for debugging
        specs["_raw_specs_text"] = raw_specs_html

        # STEP 4: Translate Hebrew keys
        translated_specs = translate_hebrew_keys(specs)

        # STEP 5: Clean the data
        cleaned_specs = clean_product_data(translated_specs)

        print(f"✅ GPT parsed {len(cleaned_specs)} specs")
        return cleaned_specs

    except Exception as e:
        print(f"❌ Error extracting specifications: {e}")
        return {}


# -------------------------------
# Phase 1: Scrape product cards
# -------------------------------
def scrape_rosen_emtb(driver):
    basic_products = []
    """Scrape E-MTB bikes from Rosen Meents"""
    print(f"\n🌐 Scraping: {TARGET_URL}")
    driver.get(TARGET_URL)
    time.sleep(5)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Look for product cards - Rosen Meents uses wrap-product-box-2023 class
    cards = soup.find_all("div", class_="wrap-product-box-2023")
    print(f"✅ Found {len(cards)} products using wrap-product-box-2023 selector")
    
    # First pass: Extract basic info from all product cards
    basic_products = []
    
    for i, product_card in enumerate(cards):
        print(f"--- Processing Product {i+1} ---")
        
        firm_text = None
        model_text = None
        year_text = None
        price_text = None
        img_url = None
        product_url = None
        
        # Extract model name from product-box-top__title
        model_tag = product_card.find("div", class_="product-box-top__title")
        if model_tag:
            model_text = model_tag.get_text(strip=True)
            if model_text:
                # Extract firm name from model name (case-insensitive)
                firm_names = ["Rocky Mountain", "BMC", "Merida"]
                for firm in firm_names:
                    if firm.lower() in model_text.lower():
                        firm_text = firm  # Use the original case for the firm name
                        # Remove the firm name from model text (case-insensitive)
                        model_text = re.sub(re.escape(firm), "", model_text, flags=re.IGNORECASE).strip()
                        break
                
                # If no firm found but "scor" is in the model name, set firm to BMC
                if not firm_text and "scor" in model_text.lower():
                    firm_text = "BMC"
                
                # Remove Hebrew words and other specified terms
                words_to_remove = [
                    "אופני הרים חשמליים",
                    "אופני",
                    "New",
                    "קרבון מלא",
                    "אנדורו"
                ]
                
                for word in words_to_remove:
                    model_text = model_text.replace(word, "").strip()
                
                # Extract year from model name
                valid_years = set(str(y) for y in range(2020, 2028))
                matches = re.findall(r'\b\d{4}\b', model_text)
                year_text = next((year for year in matches if year in valid_years), None)
                if year_text:
                    model_text = re.sub(r'\b' + re.escape(year_text) + r'\b', '', model_text).strip()
        
        # Extract original price from product-item-price__price-changer
        original_price_tag = product_card.find("span", class_="product-item-price__price-changer")
        original_price = None
        if original_price_tag:
            original_price_text = original_price_tag.get_text(strip=True)
            if original_price_text:
                # Try to convert to integer
                price_match = re.search(r'[\d,]+', original_price_text.replace('₪', '').replace(',', ''))
                if price_match:
                    try:
                        original_price = int(price_match.group().replace(',', ''))
                    except ValueError:
                        pass
        
        # Extract discounted price from product-box_price-extra-change (club price)
        discounted_price_tag = product_card.find("span", class_="product-box_price-extra-change")
        discounted_price = None
        if discounted_price_tag:
            discounted_price_text = discounted_price_tag.get_text(strip=True)
            if discounted_price_text:
                # Try to convert to integer
                price_match = re.search(r'[\d,]+', discounted_price_text.replace('₪', '').replace(',', ''))
                if price_match:
                    try:
                        discounted_price = int(price_match.group().replace(',', ''))
                    except ValueError:
                        pass
        
        # Set the main price (use discounted if available, otherwise original)
        if discounted_price:
            price_text = discounted_price
        elif original_price:
            price_text = original_price
        else:
            price_text = "צור קשר"
        
        # Extract image URL from product-box-top__image-item
        img_url = None
        img_tag = product_card.find("img", class_="product-box-top__image-item")
        if img_tag:
            # Try data-src first (lazy loaded images), then src
            img_url = img_tag.get('data-src') or img_tag.get('src')
            if img_url:
                # Remove query parameters if present
                if '?' in img_url:
                    img_url = img_url.split('?')[0]
                if not img_url.startswith('http'):
                    img_url = urljoin(BASE_URL, img_url)
                
                # Check if this is a placeholder image and skip it
                if img_url and ('anim.gif' in img_url or 'placeholder' in img_url.lower()):
                    print(f"⚠️ Skipping placeholder image: {img_url}")
                    img_url = None
                elif img_url and 'files/catalog/item' in img_url:
                    print(f"✅ Found valid product image: {img_url}")
                else:
                    print(f"⚠️ Found image but not from catalog: {img_url}")
                    # Still keep it as it might be valid
        
        # If no valid image found, try alternative selectors
        if not img_url:
            # Try other common image selectors
            alternative_selectors = [
                ".product-box-top__image img",  # Direct child of image container
                "img[data-src*='files/catalog']",  # Lazy loaded catalog images
                "img[src*='files/catalog']",  # Direct catalog images
                ".product-image img",  # Generic product image
                ".product-box img"  # Product box images
            ]
            
            for selector in alternative_selectors:
                try:
                    alt_img_tag = product_card.select_one(selector)
                    if alt_img_tag:
                        alt_img_url = alt_img_tag.get('data-src') or alt_img_tag.get('src')
                        if alt_img_url and 'anim.gif' not in alt_img_url and 'placeholder' not in alt_img_url.lower():
                            if '?' in alt_img_url:
                                alt_img_url = alt_img_url.split('?')[0]
                            if not alt_img_url.startswith('http'):
                                alt_img_url = urljoin(BASE_URL, alt_img_url)
                            img_url = alt_img_url
                            print(f"✅ Found alternative image: {img_url}")
                            break
                except Exception as e:
                    continue
        
        # Extract product URL from the main link
        link_tag = product_card.find('a', class_="product-box-2023")
        if link_tag:
            relative_href = link_tag.get('href')
            if relative_href:
                product_url = urljoin(BASE_URL, relative_href)
        
        product_data = {
            "firm": firm_text,
            "model": model_text,
            "year": year_text,
            "original_price": original_price,
            "disc_price": discounted_price,
            "image_URL": img_url,
            "product_URL": product_url
        }
        
        # Check if this is a bike (exclude accessories and courses)
        exclude_words = [
            "סוללת",
            "תפס",
            "כבל",
            "קורס",
            "סוללה מגדילת טווח"
        ]
        
        is_bike = True
        if model_text:
            for word in exclude_words:
                if word in model_text:
                    is_bike = False
                    print(f"⚠️ Skipped (not a bike): {model_text} - contains '{word}'")
                    break
        
        # Only add if it's a bike and we have at least a model or image
        if is_bike and (model_text or img_url):
            # Clean the product data before adding
            cleaned_product_data = clean_product_data(product_data)
            basic_products.append(cleaned_product_data)
            print(f"✅ Added basic info: {model_text} - Original: {original_price}, Discounted: {discounted_price}")
        elif not is_bike:
            pass  # Already printed skip message above
        else:
            print(f"⚠️ Skipped: No model or image found")

    # Phase 2: Extract specs and gallery images
    print(f"\n🔍 Extracting specs and gallery images for {len(basic_products)} bikes...")
    for i, product in enumerate(basic_products):
        print(f"\n--- Extracting specs for bike {i+1}/{len(basic_products)}: {product.get('model')} ---")
        if product.get("product_URL"):
            specs = extract_product_specifications(driver, product["product_URL"])
            product.update(specs)
            
            # Extract gallery images from the product page
            gallery_images_urls = extract_gallery_images(driver, product["product_URL"])
            # Add gallery_images_urls after product_URL field
            product["gallery_images_urls"] = gallery_images_urls
            
            # If no valid main image was found, use the first gallery image as main image
            if (not product.get("image_URL") or 
                'anim.gif' in product.get("image_URL", "") or 
                'placeholder' in product.get("image_URL", "").lower() or
                'files/catalog/item' not in product.get("image_URL", "")) and gallery_images_urls:
                # Find the best gallery image (prefer source images, then thumb images)
                best_gallery_image = None
                for gallery_img in gallery_images_urls:
                    if '/source/' in gallery_img:
                        best_gallery_image = gallery_img
                        break
                    elif '/thumb/' in gallery_img:
                        best_gallery_image = gallery_img
                
                # If no source or thumb found, use the first one
                if not best_gallery_image and gallery_images_urls:
                    best_gallery_image = gallery_images_urls[0]
                
                if best_gallery_image:
                    product["image_URL"] = best_gallery_image
                    print(f"🖼️ Using gallery image as main image: {best_gallery_image}")
        
        # Extract WH from battery field
        battery_value = product.get("battery", "")
        if battery_value:
            wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)
            if wh_match:
                wh_value = int(wh_match.group(1))
                product["wh"] = wh_value
                print(f"🔋 Found Wh in battery field: {wh_value}Wh")
            else:
                # If no 'Wh' found, try to find a 3-digit number in battery field
                fallback_match = re.search(r"\b(\d{3})\b", battery_value)
                if fallback_match:
                    product["wh"] = int(fallback_match.group(1))
                    print(f"🔋 Found 3-digit number in battery field: {fallback_match.group(1)}Wh")
        
        # Extract fork length from fork field
        fork_text = product.get("fork", "")
        if fork_text:
            print(f"DEBUG: fork_text = '{fork_text}'")
            
            # Try multiple patterns for fork travel
            patterns = [
                r'(\d{3})\s*mm\s*(?:travel|suspension)',  # Pattern with "travel" or "suspension"
                r'(\d{3})\s*mm\s*[^0-9]*$',  # Pattern at end of string
                r'(\d{3})\s*mm',  # Simple mm pattern
                r'(?<!\d)(100|120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?',  # Original pattern
            ]
            
            found = False
            for pattern in patterns:
                match = re.search(pattern, fork_text.lower())
                if match:
                    fork_length = int(match.group(1))
                    product["fork length"] = fork_length
                    print(f"🔧 Found fork length: {fork_length}mm (pattern: {pattern})")
                    
                    # Determine sub-category based on fork length
                    if fork_length in [100, 120]:
                        product["sub-category"] = "cross-country"
                    elif fork_length in [130, 140, 150, 160]:
                        product["sub-category"] = "trail"
                    elif fork_length in [160, 170, 180]:
                        product["sub-category"] = "enduro"
                    else:
                        product["sub-category"] = "unknown"
                    print(f"🏷️ Assigned sub-category: {product['sub-category']}")
                    found = True
                    break
            
            if not found:
                print(f"⚠️ Could not extract fork length from: '{fork_text}'")
                product["fork length"] = None
                product["sub-category"] = "unknown"
        
        # Clean the final product data but preserve gallery_images_urls
        final_cleaned_product = clean_product_data(product)
        
        # Ensure gallery_images_urls is preserved and placed after product_URL
        if "gallery_images_urls" in product:
            # Create a new dictionary with the correct order
            ordered_product = {}
            
            # Add all fields from final_cleaned_product except gallery_images_urls
            for key, value in final_cleaned_product.items():
                if key != "gallery_images_urls":
                    ordered_product[key] = value
                    # If we just added product_URL, add gallery_images_urls right after it
                    if key == "product_URL":
                        ordered_product["gallery_images_urls"] = product["gallery_images_urls"]
            
            # If product_URL wasn't found, add gallery_images_urls at the end
            if "product_URL" not in ordered_product:
                ordered_product["gallery_images_urls"] = product["gallery_images_urls"]
            
            final_cleaned_product = ordered_product
            print(f"🔍 DEBUG: Added gallery_images_urls with {len(product['gallery_images_urls'])} images")
        else:
            print(f"🔍 DEBUG: No gallery_images_urls found in product data")
        
        # Debug: Check if the field is in the final cleaned product
        if "gallery_images_urls" in final_cleaned_product:
            print(f"🔍 DEBUG: gallery_images_urls is in final_cleaned_product with {len(final_cleaned_product['gallery_images_urls'])} images")
        else:
            print(f"🔍 DEBUG: gallery_images_urls is NOT in final_cleaned_product")
        
        scraped_data.append(final_cleaned_product)

    return scraped_data

# -------------------------------
# Gallery Images Extractor
# -------------------------------
def extract_gallery_images(driver, product_url):
    """Extract gallery images from the slick-track element on product page"""
    if not product_url:
        return []
    
    try:
        print(f"🖼️ Extracting gallery images from: {product_url}")
        driver.get(product_url)
        time.sleep(5)  # Increased wait time for JavaScript to load
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Try multiple selectors to find gallery images
        gallery_images_urls = []
        
        # Method 1: Look for slick-track element
        slick_track = soup.find("div", class_="slick-track")
        if slick_track:
            print("✅ Found slick-track element")
            
            # Find all product-item-slider-small-wrap elements
            slider_wraps = slick_track.find_all("div", class_="product-item-slider-small-wrap")
            print(f"Found {len(slider_wraps)} slider wraps")
            
            for wrap in slider_wraps:
                # Find the image div with background-image
                img_div = wrap.find("div", class_="product-item-slider-small__image-small")
                if img_div:
                    # Extract background-image URL from style attribute
                    style_attr = img_div.get("style", "")
                    print(f"Style attribute: {style_attr}")
                    if "background-image:url(" in style_attr:
                        # Extract URL from background-image:url('...')
                        url_match = re.search(r"background-image:url\('([^']+)'\)", style_attr)
                        if url_match:
                            img_url = url_match.group(1)
                            # Convert relative URL to absolute URL
                            if not img_url.startswith('http'):
                                img_url = urljoin(BASE_URL, img_url)
                            gallery_images_urls.append(img_url)
                            print(f"🖼️ Found gallery image: {img_url}")
        else:
            print("⚠️ No slick-track element found")
        
        # Method 2: Look for any elements with background-image containing image URLs
        if not gallery_images_urls:
            print("🔍 Trying alternative method: searching for background-image styles")
            all_divs = soup.find_all("div")
            for div in all_divs:
                style_attr = div.get("style", "")
                if "background-image:url(" in style_attr and ("files/catalog" in style_attr or ".png" in style_attr or ".jpg" in style_attr):
                    url_match = re.search(r"background-image:url\('([^']+)'\)", style_attr)
                    if url_match:
                        img_url = url_match.group(1)
                        if not img_url.startswith('http'):
                            img_url = urljoin(BASE_URL, img_url)
                        # Filter out menu images and only include product-specific images
                        if ("files/catalog/item" in img_url and 
                            "menu" not in img_url.lower() and 
                            "banner" not in img_url.lower() and
                            img_url not in gallery_images_urls):
                            gallery_images_urls.append(img_url)
                            print(f"🖼️ Found alternative gallery image: {img_url}")
        
        # Method 3: Look for img tags in any gallery-like containers
        if not gallery_images_urls:
            print("🔍 Trying method 3: searching for img tags in gallery containers")
            gallery_containers = soup.find_all(["div", "ul"], class_=lambda x: x and any(word in x.lower() for word in ["gallery", "slider", "thumb", "image"]))
            for container in gallery_containers:
                img_tags = container.find_all("img")
                for img in img_tags:
                    src = img.get("src") or img.get("data-src")
                    if src and ("files/catalog" in src or ".png" in src or ".jpg" in src):
                        if not src.startswith('http'):
                            src = urljoin(BASE_URL, src)
                        # Filter out menu images and only include product-specific images
                        if ("files/catalog/item" in src and 
                            "menu" not in src.lower() and 
                            "banner" not in src.lower() and
                            src not in gallery_images_urls):
                            gallery_images_urls.append(src)
                            print(f"🖼️ Found img tag gallery image: {src}")
        
        # Remove duplicates and filter out menu/banner images
        filtered_gallery_images = []
        for img_url in gallery_images_urls:
            # Only include images that are product-specific (not menu or banner images)
            if ("files/catalog/item" in img_url and 
                "menu" not in img_url.lower() and 
                "banner" not in img_url.lower() and
                "hermidabanner" not in img_url.lower() and
                "anim.gif" not in img_url and
                "placeholder" not in img_url.lower() and
                img_url not in filtered_gallery_images):
                filtered_gallery_images.append(img_url)
        
        print(f"✅ Extracted {len(filtered_gallery_images)} gallery images (filtered from {len(gallery_images_urls)} total)")
        
        # Prioritize larger/higher quality images by sorting them
        # Look for images with 'source' in the URL (usually larger) first
        sorted_gallery_images = []
        
        # First add source images (usually highest quality)
        for img_url in filtered_gallery_images:
            if '/source/' in img_url:
                sorted_gallery_images.append(img_url)
        
        # Then add other images
        for img_url in filtered_gallery_images:
            if '/source/' not in img_url:
                sorted_gallery_images.append(img_url)
        
        # Debug: Print the first few lines of the HTML to see the structure
        if not filtered_gallery_images:
            print("🔍 Debug: First 500 characters of HTML:")
            print(driver.page_source[:500])
        
        return sorted_gallery_images
        
    except Exception as e:
        print(f"❌ Error extracting gallery images: {e}")
        return []

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    driver = uc.Chrome()
    try:
        data = scrape_rosen_emtb(driver)
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scraped_raw_data")
        output_file = os.path.join(output_dir, "rosen.json")

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"\n✅ All final cleaned data saved to {output_file}")
        print(f"📊 Total products scraped: {len(data)}")
    finally:
        driver.quit()
