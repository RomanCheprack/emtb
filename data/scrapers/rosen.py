import time
import re
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc

BASE_URL = "https://www.rosen-meents.co.il"
TARGET_URL = f"{BASE_URL}/אופני-הרים-חשמליים-E-MTB"

# Hebrew to English key mapping for specifications
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
    "מרכיבים נוספים\nסטם": "stem",
    "כידון": "handlebar",
    "מוט אוכף": "seatpost",
    "אוכף": "saddle",
    "דוושות (פדלים)": "pedals",
    "דוא\"ל": "email",
    "חישוקים": "rims",
    "צמיגים": "tires",
    "סוללה": "battery",
    "מטען": "charger",
    "מצפן": "compass",
    "תאורה": "lighting",
    "מנעול": "lock",
    "תיק": "bag",
    "משקל": "weight",
    "גובה": "height",
    "רוחב": "width",
    "אורך": "length",
    "נפח": "volume",
    "קיבולת": "capacity",
    "טווח": "range",
    "מהירות": "speed",
    "כוח": "power",
    "מתח": "voltage",
    "זרם": "current",
    "הספק": "power_output",
    "טמפרטורה": "temperature",
    "לחות": "humidity",
    "לחץ": "pressure",
    "זמן": "time",
    "תאריך": "date",
    "שנה": "year",
    "חודש": "month",
    "יום": "day",
    "שעה": "hour",
    "דקה": "minute",
    "שנייה": "second"
}

scraped_data = []

def extract_number(price_str):
    """Extract numeric value from price string"""
    if not price_str:
        return None
    return re.sub(r'[^\d,]', '', str(price_str))

def translate_hebrew_keys(specs_dict):
    """Translate Hebrew keys to English using the mapping dictionary"""
    translated_specs = {}
    for key, value in specs_dict.items():
        # Check if the key is in Hebrew and has a translation
        if key in HEBREW_TO_ENGLISH_KEYS:
            translated_key = HEBREW_TO_ENGLISH_KEYS[key]
            translated_specs[translated_key] = value
        else:
            # Keep the original key if no translation found
            translated_specs[key] = value
    return translated_specs

def safe_to_int(text):
    """Safely convert text to integer, handling Hebrew 'צור קשר'"""
    if not text or text == "צור קשר":
        return "צור קשר"
    try:
        return int(text.replace(',', '').replace('₪', '').strip())
    except (ValueError, AttributeError):
        return "צור קשר"

def extract_specs_table(soup):
    """Extract specifications from table format"""
    specs = {}
    spec_table = soup.find("table", class_="table")
    if spec_table:
        tbody = spec_table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) == 4:
                    key1 = cells[0].get_text(strip=True)
                    val1 = cells[1].get_text(strip=True)
                    key2 = cells[2].get_text(strip=True)
                    val2 = cells[3].get_text(strip=True)
                    if key1 and val1:
                        specs[key1] = val1
                    if key2 and val2:
                        specs[key2] = val2
                elif len(cells) == 2:
                    key = cells[0].get_text(strip=True)
                    val = cells[1].get_text(strip=True)
                    if key and val:
                        specs[key] = val
    return specs

def extract_specs_list(soup):
    """Extract specifications from list format"""
    specs = {}
    
    # First, try to find ul elements within col-md-12 col-xs-12 divs (specific structure)
    col_divs = soup.find_all("div", class_="col-md-12 col-xs-12")
    for col_div in col_divs:
        spec_lists = col_div.find_all("ul")
        for spec_list in spec_lists:
            # Skip the product-complex-ul which contains size/color variants, not specs
            if spec_list.get('class') and 'product-complex-ul' in spec_list.get('class'):
                continue
                
            items = spec_list.find_all("li")
            for item in items:
                # Look for two <p> elements in each <li>
                p_elements = item.find_all("p")
                if len(p_elements) >= 2:
                    # First <p> is the key, second <p> is the value
                    key = p_elements[0].get_text(strip=True)
                    val = p_elements[1].get_text(strip=True)
                    if key and val:
                        specs[key] = val
                else:
                    # Fallback: try to split by colon if no <p> elements found
                    text = item.get_text(strip=True)
                    if ":" in text:
                        key, val = text.split(":", 1)
                        specs[key.strip()] = val.strip()
                    else:
                        # For simple li elements without colons, use the text as value
                        # and try to infer a key from context or use a generic key
                        text = item.get_text(strip=True)
                        if text and len(text) > 3:  # Only add if meaningful content
                            # Try to create a key based on the content
                            if "material:" in text.lower():
                                specs["Material"] = text.split(":", 1)[1].strip() if ":" in text else text
                            elif "mm" in text or "inch" in text:
                                specs["Size"] = text
                            elif any(word in text.lower() for word in ["teeth", "speed", "gear"]):
                                specs["Gearing"] = text
                            elif any(word in text.lower() for word in ["hub", "wheel", "rim"]):
                                specs["Wheels"] = text
                            elif any(word in text.lower() for word in ["tire", "tyre"]):
                                specs["Tires"] = text
                            elif any(word in text.lower() for word in ["brake", "rotor"]):
                                specs["Brakes"] = text
                            elif any(word in text.lower() for word in ["stem", "handlebar", "bar"]):
                                specs["Cockpit"] = text
                            elif any(word in text.lower() for word in ["seat", "saddle", "post"]):
                                specs["Seat"] = text
                            elif any(word in text.lower() for word in ["battery", "wh", "voltage"]):
                                specs["Battery"] = text
                            else:
                                specs[f"Spec_{len(specs)+1}"] = text
    
    # If no specs found in col-md-12 divs, try generic ul/ol search
    if not specs:
        spec_lists = soup.find_all(["ul", "ol"])
        for spec_list in spec_lists:
            # Skip the product-complex-ul which contains size/color variants, not specs
            if spec_list.get('class') and 'product-complex-ul' in spec_list.get('class'):
                continue
                
            items = spec_list.find_all("li")
            for item in items:
                # Look for two <p> elements in each <li>
                p_elements = item.find_all("p")
                if len(p_elements) >= 2:
                    # First <p> is the key, second <p> is the value
                    key = p_elements[0].get_text(strip=True)
                    val = p_elements[1].get_text(strip=True)
                    if key and val:
                        specs[key] = val
                else:
                    # Fallback: try to split by colon if no <p> elements found
                    text = item.get_text(strip=True)
                    if ":" in text:
                        key, val = text.split(":", 1)
                        specs[key.strip()] = val.strip()
    
    return specs

def extract_specs_divs(soup):
    """Extract specifications from div format"""
    specs = {}
    spec_divs = soup.find_all("div", class_=lambda x: x and "spec" in x.lower())
    for div in spec_divs:
        # Look for key-value pairs in divs
        key_elements = div.find_all(["strong", "b", "span"], class_=lambda x: x and "key" in x.lower())
        for key_elem in key_elements:
            key = key_elem.get_text(strip=True)
            # Find the corresponding value (next sibling or parent's next sibling)
            value_elem = key_elem.find_next_sibling()
            if value_elem:
                val = value_elem.get_text(strip=True)
                if key and val:
                    specs[key] = val
    return specs

def extract_specs_paragraphs(soup):
    """Extract specifications from paragraph format with &nbsp; separator"""
    specs = {}
    
    # Look for <p> elements that contain specifications
    p_elements = soup.find_all("p", dir="ltr")
    
    for p_elem in p_elements:
        text = p_elem.get_text(strip=True)
        
        # Check if the text contains &nbsp; (non-breaking space)
        if "&nbsp;" in text or "\xa0" in text:
            # Split by &nbsp; or \xa0 (non-breaking space)
            if "&nbsp;" in text:
                parts = text.split("&nbsp;")
            else:
                parts = text.split("\xa0")
            
            if len(parts) >= 2:
                key = parts[0].strip()
                value = " ".join(parts[1:]).strip()  # Join remaining parts as value
                
                if key and value:
                    specs[key] = value
                    
                    # Look for additional details in the next <ul> element
                    next_ul = p_elem.find_next_sibling("ul")
                    if next_ul:
                        ul_items = next_ul.find_all("li")
                        if ul_items:
                            details = []
                            for item in ul_items:
                                detail_text = item.get_text(strip=True)
                                if detail_text:
                                    details.append(detail_text)
                            
                            if details:
                                # Add details to the specification
                                specs[f"{key}_details"] = details
    
    return specs

def extract_specs_strong_br(soup):
    """Extract specifications from <p> elements with <strong> keys and <br> separated values"""
    specs = {}
    
    # Look for <p> elements that contain <strong> tags
    p_elements = soup.find_all("p", style="text-align:left")
    
    for p_elem in p_elements:
        # Find <strong> element within the <p>
        strong_elem = p_elem.find("strong")
        if strong_elem:
            key = strong_elem.get_text(strip=True)
            if key:
                # Remove the colon from the key if present
                key = key.rstrip(':')
                
                # Get the text content after the <br> tag
                # First, get all text content of the <p> element
                full_text = p_elem.get_text(strip=True)
                
                # Remove the key part from the beginning
                if key in full_text:
                    value = full_text.replace(key, '').strip()
                    # Remove leading colon and whitespace if present
                    if value.startswith(':'):
                        value = value[1:].strip()
                    
                    if value:
                        specs[key] = value
    
    return specs

def extract_specs_rosen_merida(soup):
    """Extract specifications from Rosen Meents Merida bike structure"""
    specs = {}
    
    # Find the specific div structure used by Rosen Meents for Merida bikes
    col_divs = soup.find_all("div", class_="col-md-12 col-xs-12")
    
    for col_div in col_divs:
        # Get all direct children (p and ul elements) in order
        children = col_div.find_all(["p", "ul"], recursive=False)
        
        i = 0
        while i < len(children):
            current_elem = children[i]
            
            if current_elem.name == "p":
                p_text = current_elem.get_text(strip=True)
                
                if not p_text:
                    i += 1
                    continue
                
                # Check if the next element is a ul (specification details)
                if i + 1 < len(children) and children[i + 1].name == "ul":
                    # Get the ul element and extract all li items
                    ul_elem = children[i + 1]
                    li_elements = ul_elem.find_all("li")
                    spec_details = []
                    
                    for li_elem in li_elements:
                        detail_text = li_elem.get_text(strip=True)
                        if detail_text:
                            spec_details.append(detail_text)
                    
                    # Join all details with comma separator (instead of semicolon to avoid JSON issues)
                    if spec_details:
                        specs[p_text] = ", ".join(spec_details)
                    
                    i += 2  # Skip both p and ul elements
                else:
                    # This is a simple key-value pair (no ul follows)
                    # Handle cases where the text contains &nbsp; or other separators
                    if "&nbsp;" in p_text:
                        # Split by &nbsp; and take the first part as key, rest as value
                        parts = p_text.split("&nbsp;")
                        if len(parts) >= 2:
                            key = parts[0].strip()
                            value = " ".join(parts[1:]).strip()
                            if key and value:
                                specs[key] = value
                    else:
                        # Special handling for known patterns
                        if "FRAME SIZE" in p_text:
                            # Handle "FRAME SIZE S, M, L, XL" pattern
                            key = "FRAME SIZE"
                            value = p_text.replace("FRAME SIZE", "").strip()
                            if value:
                                specs[key] = value
                        elif "SEAT CLAMP" in p_text:
                            # Handle "SEAT CLAMP MERIDA EXPERT" pattern
                            key = "SEAT CLAMP"
                            value = p_text.replace("SEAT CLAMP", "").strip()
                            if value:
                                specs[key] = value
                        elif "BATTERY LOCK" in p_text:
                            # Handle "BATTERY LOCK Abus key" pattern
                            key = "BATTERY LOCK"
                            value = p_text.replace("BATTERY LOCK", "").strip()
                            if value:
                                specs[key] = value
                        elif "MAX. WEIGHT" in p_text:
                            # Handle "MAX. WEIGHT 140 kg" pattern
                            key = "MAX. WEIGHT"
                            value = p_text.replace("MAX. WEIGHT", "").strip()
                            if value:
                                specs[key] = value
                        elif "SHIFTERS" in p_text:
                            # Handle "SHIFTERS Shimano Deore M4100" pattern
                            key = "SHIFTERS"
                            value = p_text.replace("SHIFTERS", "").strip()
                            if value:
                                specs[key] = value
                        elif "DISPLAY" in p_text:
                            # Handle "DISPLAY Shimano SC-E5003A" pattern
                            key = "DISPLAY"
                            value = p_text.replace("DISPLAY", "").strip()
                            if value:
                                specs[key] = value
                        elif "KICKSTAND" in p_text:
                            # Handle "KICKSTAND Massload CL-KA98" pattern
                            key = "KICKSTAND"
                            value = p_text.replace("KICKSTAND", "").strip()
                            if value:
                                specs[key] = value
                        else:
                            # Try to find a natural separator
                            # Look for patterns like "KEY VALUE" where VALUE might be in caps or contain numbers
                            import re
                            # Pattern to match: word(s) followed by space and then value (often in caps or with numbers, commas, etc.)
                            # Use a more specific pattern that looks for the last word in the key
                            match = re.match(r'^(.+?)\s+([A-Z0-9\s\-\.\/\(\)\,]+)$', p_text)
                            if match:
                                key = match.group(1).strip()
                                value = match.group(2).strip()
                                if key and value:
                                    specs[key] = value
                            else:
                                # If no clear separator, store as is
                                specs[p_text] = ""
                    
                    i += 1
            else:
                # Skip ul elements that don't follow a p element
                i += 1
    
    return specs

def extract_specs_generic(soup):
    """Generic specification extraction - fallback method"""
    specs = {}
    # Look for common specification patterns
    spec_patterns = [
        r"([^:]+):\s*([^\n]+)",  # Key: Value pattern
        r"([^=]+)=\s*([^\n]+)",  # Key=Value pattern
    ]
    
    # Search in all text content
    text_content = soup.get_text()
    for pattern in spec_patterns:
        matches = re.findall(pattern, text_content)
        for key, val in matches:
            key = key.strip()
            val = val.strip()
            if key and val and len(key) < 50:  # Avoid very long keys
                specs[key] = val
    
    return specs

def extract_product_specifications(driver, product_url):
    """Main function to extract specifications from product page"""
    if not product_url:
        return {}
    
    try:
        print(f"🔍 Extracting specs from: {product_url}")
        driver.get(product_url)
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        specs = {}
        
        # Try different extraction methods in order of preference
        methods = [
            ("rosen_merida", extract_specs_rosen_merida),
            ("strong_br", extract_specs_strong_br),
            ("table", extract_specs_table),
            ("list", extract_specs_list),
            ("divs", extract_specs_divs),
            ("paragraphs", extract_specs_paragraphs),
            ("generic", extract_specs_generic)
        ]
        
        for method_name, method_func in methods:
            try:
                method_specs = method_func(soup)
                if method_specs:
                    print(f"✅ Found specs using {method_name} method: {len(method_specs)} items")
                    specs.update(method_specs)
                    break  # Use the first successful method
            except Exception as e:
                print(f"⚠️ Error with {method_name} method: {e}")
                continue
        
        if not specs:
            print("⚠️ No specifications found")
        
        # Translate Hebrew keys to English
        translated_specs = translate_hebrew_keys(specs)
        if translated_specs != specs:
            print(f"🔄 Translated {len(specs)} Hebrew keys to English")
        
        return translated_specs
        
    except Exception as e:
        print(f"❌ Error extracting specifications: {e}")
        return {}

def scrape_rosen_emtb(driver):
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
        img_tag = product_card.find("img", class_="product-box-top__image-item")
        if img_tag:
            img_url = img_tag.get('src') or img_tag.get('data-src')
            if img_url:
                # Remove query parameters if present
                if '?' in img_url:
                    img_url = img_url.split('?')[0]
                if not img_url.startswith('http'):
                    img_url = urljoin(BASE_URL, img_url)
        
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
            basic_products.append(product_data)
            print(f"✅ Added basic info: {model_text} - Original: {original_price}, Discounted: {discounted_price}")
        elif not is_bike:
            pass  # Already printed skip message above
        else:
            print(f"⚠️ Skipped: No model or image found")
    
    # Second pass: Extract specifications for each bike
    print(f"\n🔍 Extracting specifications for {len(basic_products)} bikes...")
    
    for i, product_data in enumerate(basic_products):
        print(f"\n--- Extracting specs for bike {i+1}/{len(basic_products)}: {product_data.get('model', 'Unknown')} ---")
        
        if product_data.get('product_URL'):
            try:
                specifications = extract_product_specifications(driver, product_data['product_URL'])
                product_data.update(specifications)
                print(f"✅ Specs extracted: {len(specifications)} items")
            except Exception as e:
                print(f"❌ Error extracting specs: {e}")
                # Continue with other bikes even if one fails
        else:
            print("⚠️ No product URL available for specs extraction")
        
        # Add to final scraped data
        scraped_data.append(product_data)
    
    return scraped_data

# --- Main ---
if __name__ == "__main__":
    driver = uc.Chrome()
    try:
        scrape_rosen_emtb(driver)
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scraped_raw_data')
        output_file = os.path.join(output_dir, "rosen.json")
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, ensure_ascii=False, indent=4)
        print(f"\n✅ All data saved to {output_file}")
        print(f"📊 Total products scraped: {len(scraped_data)}")
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
    finally:
        driver.quit()
