# -*- coding: utf-8 -*-
import time
import os
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc
import requests
from selenium.webdriver.common.by import By


BASE_URL = "https://rl-bikes.co.il"
CHATGPT_API_KEY = os.getenv('SCRAPER_OPENAI_API_KEY', '')

RL_TARGET_URLS = [
    {"url": f"{BASE_URL}/product-category/אופניים/אופני-ילדים/", "category": "kids", "sub_category": "kids"},
    {"url": f"{BASE_URL}/product-category/אופניים/אופני-נשים/", "category": "city", "sub_category": "woman"},
    {"url": f"{BASE_URL}/product-category/אופניים/אופני-עיר/", "category": "city", "sub_category": "city"},
    {"url": f"{BASE_URL}/product-category/אופניים/אופני-שטח/", "category": "mtb", "sub_category": "hardtail"},
]

HEBREW_TO_ENGLISH_KEYS = {
    "שלדה": "frame",
    "מזלג": "fork",
    "בולם זעזועים": "fork",
    "כידון": "handlebar",
    "אוכף": "saddle",
    "מושב": "saddle",
    "מוט אוכף": "seatpost",
    "מוט מושב": "seatpost",
    "בולם אחורי": "rear_shock",
    "מוט כידון": "stem",
    "סטם": "stem",
    "ידיות הילוכים": "shifters",
    "שיפטרים": "shifters",
    "ידיות ברקס": "brake_levers",
    "מעביר אחורי": "rear_derailleur",
    "מעביר קדמי": "front_derailleur",
    "בלמים": "brakes",
    "מעצורים": "brakes",
    "קסטה": "cassette",
    "גלגל הינע": "crankset",
    "קראנק": "crankset",
    "חישוקים": "rims",
    "גלגלים": "wheels",
    "צמיגים": "tires",
    "שרשרת": "chain",
    "פדלים": "pedals",
    "גריפים": "grips",
    "משקל": "weight",
    "דגם": "model_spec",
     "בולם זעזועים קדמי": "fork",
     "בולם זעזועים אחורי": "rear_shock",
}


# Kids bike wheel sizes (inches)
KIDS_WHEEL_SIZE_PATTERN = re.compile(
    r'\b(12|14|16|18|20|24|26)\b|'
    r'(12|14|16|18|20|24|26)(?:x|\"| inch| אינץ)'
)

def extract_wheel_size_from_text(text):
    """Extract kids bike wheel sizes (12, 14, 16, 18, 20, 24, 26) from text. Returns list of ints."""
    if not text:
        return []
    matches = KIDS_WHEEL_SIZE_PATTERN.findall(str(text))
    result = []
    for m in matches:
        val = m if isinstance(m, str) else next((x for x in m if x), None)
        if val and int(val) not in result:
            result.append(int(val))
    return result

def extract_wheel_size_for_kids_bike(model, specs):
    """
    Extract wheel size for kids bikes. Returns int or None.
    - First try model name for single match
    - If multiple matches in model or no match, check specs (wheels, rims, front_tire, rear_tire, tires)
    """
    model_matches = extract_wheel_size_from_text(model or "")

    if len(model_matches) == 1:
        return model_matches[0]

    wheel_related_keys = ["wheels", "rims", "front_tire", "rear_tire", "tires"]
    for key in wheel_related_keys:
        val = specs.get(key) if specs else None
        if val:
            matches = extract_wheel_size_from_text(val)
            if matches:
                return matches[0]

    if model_matches:
        return model_matches[0]

    return None

def rewrite_description_with_chatgpt(original_text, api_key):
    """Rewrite product description using ChatGPT API"""
    if not original_text:
        print("⚠️ Warning: No text provided for ChatGPT rewriting")
        return original_text
    
    if not api_key:
        print("⚠️ Warning: No API key provided for ChatGPT rewriting")
        return original_text
    
    try:
        # Prepare the API request
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "אתה מומחה לכתיבת תוכן שיווקי לאופניים בחנויות אינטרנטיות. המטרה שלך היא לקחת תיאור אופניים קיים וליצור גרסה חדשה, מושכת ומקצועית, כך שהקורא לא יזהה את המקור. יש להתמקד בחוויית רכיבה, נוחות, בטיחות, עיצוב ויתרונות שימושיים לעיר, לטיולים או לרכיבה יומיומית. אפשר להוסיף הרחבות, פרטים ושפה שיווקית, אך אין לשנות את מהות האופניים."
                },
                {
                    "role": "user",
                    "content": f"להלן תיאור האופניים: \n\n{original_text}\n\nאנא כתוב גרסה שיווקית חדשה, מושכת, שמתאימה לפרסום בחנות אינטרנטית, עם דגש על חוויית רכיבה, יתרונות המוצר, עיצוב ונוחות, תוך שמירה על מהות האופניים. הרחב ותאר את האופניים בצורה שתגרום לקוראים לרצות לרכוש אותם אך לא בצורה מוגזמת, לוחצת וגסה ודוחפת, כולל קריאה לפעולה בסוף."
                }
            ],
            "temperature": 0.6,
            "max_tokens": 500
        }
        
        # Make the API request
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        # Extract the rewritten text
        result = response.json()
        rewritten_text = result['choices'][0]['message']['content'].strip()
        
        return rewritten_text
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error calling ChatGPT API: {e}")
        return original_text
    except KeyError as e:
        print(f"❌ Error parsing ChatGPT response: {e}")
        return original_text
    except Exception as e:
        print(f"❌ Unexpected error in ChatGPT rewriting: {e}")
        return original_text

def extract_price(price_text):
    """Extract numeric price from text"""
    if not price_text:
        return None
    try:
        # Remove currency symbols and commas, extract numbers
        cleaned = re.sub(r'[^\d.]', '', price_text)
        return int(float(cleaned)) if cleaned else None
    except (ValueError, AttributeError):
        return None

def extract_fork_length(fork_text):
    """Extract fork length in mm from text"""
    if not fork_text:
        return None
    try:
        # Look for common fork length patterns: 40, 60, 80, 100, 120, 130, 140, 150, 160, 170, 180
        match = re.search(r'\b(40|60|80|100|120|130|140|150|160|170|180)\s*(?:מ["\']מ|mm)', fork_text)
        if match:
            return int(match.group(1))
        # Try without units
        match = re.search(r'\b(40|60|80|100|120|130|140|150|160|170|180)\b', fork_text)
        if match:
            return int(match.group(1))
    except (ValueError, AttributeError):
        pass
    return None

def determine_style_from_fork(fork_length):
    """Determine bike style based on fork length"""
    if not fork_length:
        return None
    if fork_length in [40, 60, 80, 100, 120]:
        return "cross-country"
    elif fork_length in [130, 140, 150]:
        return "trail"
    elif fork_length in [160, 170, 180]:
        return "enduro"
    return None

def parse_specifications(product_soup):
    """Parse specifications from WooCommerce product attributes table.
    Table structure: <table class="woocommerce-product-attributes shop_attributes">
      <tbody><tr class="woocommerce-product-attributes-item">...</tr></tbody>
    </table>
    """
    specs = {}
    
    # Find the product attributes table (WooCommerce uses woocommerce-product-attributes or shop_attributes)
    spec_table = product_soup.find("table", class_="woocommerce-product-attributes")
    if not spec_table:
        spec_table = product_soup.find("table", class_="shop_attributes")
    
    # Fallback: find table containing spec rows (some themes use different table classes)
    if not spec_table:
        for table in product_soup.find_all("table"):
            rows = table.find_all("tr", class_=lambda c: c and "woocommerce-product-attributes-item" in str(c))
            if rows:
                spec_table = table
                break
    
    if spec_table:
        rows = spec_table.find_all("tr", class_=lambda c: c and "woocommerce-product-attributes-item" in str(c))
    else:
        # Last resort: find all spec rows anywhere on the page
        rows = product_soup.find_all("tr", class_=lambda c: c and "woocommerce-product-attributes-item" in str(c))
    
    for row in rows:
        th = row.find("th", class_="woocommerce-product-attributes-item__label")
        td = row.find("td", class_="woocommerce-product-attributes-item__value")
        
        if th and td:
            key = th.get_text(strip=True)
            value = td.get_text(strip=True)
            
            # Skip certain keys
            if key in ['מק"ט', 'מידה', 'צבע']:
                continue
            
            # Map Hebrew to English
            english_key = HEBREW_TO_ENGLISH_KEYS.get(key, key)
            specs[english_key] = value
    
    return specs

def rl_bikes(driver, output_file, scraped_data):
    for entry in RL_TARGET_URLS:
        target_url = entry["url"]
        category_text = entry["category"]
        sub_category_text = entry.get("sub_category", None)
        
        print(f"\n🌐 Scraping: {target_url}")
        driver.get(target_url)
        time.sleep(3)

        # Parse the page source with BeautifulSoup and find product cards
        print("🔍 Searching for product cards...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.find_all("li", class_="product")
        print(f"✅ Found {len(cards)} products")

        for idx, card in enumerate(cards, 1):
            print(f"\n📦 Processing product {idx}/{len(cards)}...")
            
            # Extract product URL
            link_tag = card.find("a", class_="woocommerce-LoopProduct-link")
            product_url = link_tag.get("href", "").strip() if link_tag else None
            
            if not product_url:
                print("⚠️ No product URL found, skipping...")
                continue
            
            print(f"🔗 URL: {product_url}")
            
            # Extract image URL
            img_tag = card.find("img")
            image_url = img_tag.get("src", "") if img_tag else None
            
            # Extract title/model
            title_tag = card.find("h2", class_="woocommerce-loop-product__title")
            title_text = title_tag.get_text(strip=True) if title_tag else ""
            
            print(f"📝 Title: {title_text}")
            
            # Extract price
            price_span = card.find("span", class_="price")
            price_text = price_span.get_text(strip=True) if price_span else ""
            original_price = extract_price(price_text)
            
            print(f"💰 Price: {original_price}")
            
            # Extract firm and model from title
            # RL sells their own brand bikes, so firm is "RL"
            firm = "RL"
            model = title_text
            
            # Clean up model name - remove common terms
            terms_to_remove = [
                "אופני גראבל",
                "אופני הרים",
                "אופני שטח",
                "אופני ילדים",
                "אופני נשים",
                "אופני עיר",
                "הילוכים",
                "RL",
            ]
            
            for term in terms_to_remove:
                model = model.replace(term, "").strip()
            
            # Clean up extra whitespace and hyphens
            model = re.sub(r'\s+', ' ', model).strip()
            model = re.sub(r'^[-–]\s*', '', model).strip()
            
            # Extract year if present in title
            year_match = re.search(r'\b(2023|2024|2025|2026)\b', title_text)
            year = year_match.group(1) if year_match else "לא צויין"
            
            print(f"🏷️ Firm: {firm}, Model: {model}, Year: {year}")
            
            # For MTB (אופני-שטח): sub_category based on "שיכוך מלא" in model name
            if category_text == "mtb":
                sub_category_text = "full_suspension" if "שיכוך מלא" in title_text else "hardtail"
            
            # Create product data skeleton
            product_data = {
                "source": {
                    "importer": "RL Bikes",
                    "domain": BASE_URL,
                    "product_url": product_url
                },
                "firm": firm,
                "model": model,
                "year": year,
                "category": category_text,
                "sub_category": sub_category_text,
                "original_price": original_price,
                "disc_price": "",
                "images": {
                    "image_url": image_url,
                    "gallery_images_urls": []
                },
                "specs": {},
                "rewritten_description": "",
                "fork_length": None,
                "style": None
            }
            
            # Visit product page for detailed information
            try:
                print(f"🔍 Visiting product page: {product_url}")
                driver.get(product_url)
                time.sleep(3)
                
                # Click "Additional Information" tab if specs are in a tab (WooCommerce default)
                try:
                    tab = driver.find_element(By.CSS_SELECTOR, "a[href='#tab-additional_information']")
                    tab.click()
                    time.sleep(2)
                except Exception:
                    pass  # Tab not found or specs visible by default
                
                product_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # Extract gallery images
                gallery_images = []
                gallery_ol = product_soup.find("ol", class_="flex-control-nav flex-control-thumbs")
                if gallery_ol:
                    img_tags = gallery_ol.find_all("img")
                    for img in img_tags:
                        # Get the src, but use srcset to find higher quality versions
                        srcset = img.get("srcset", "")
                        if srcset:
                            # Parse srcset to get the largest image
                            srcset_parts = srcset.split(",")
                            largest_url = None
                            largest_width = 0
                            for part in srcset_parts:
                                parts = part.strip().split()
                                if len(parts) >= 2:
                                    url = parts[0]
                                    width_str = parts[1].replace('w', '')
                                    try:
                                        width = int(width_str)
                                        if width > largest_width:
                                            largest_width = width
                                            largest_url = url
                                    except ValueError:
                                        pass
                            if largest_url:
                                gallery_images.append(largest_url)
                        else:
                            # Fallback to src
                            src = img.get("src", "")
                            if src:
                                gallery_images.append(src)
                
                product_data["images"]["gallery_images_urls"] = gallery_images
                print(f"📸 Found {len(gallery_images)} gallery images")
                
                # Extract specifications from product attributes table
                specs = parse_specifications(product_soup)
                if specs:
                    product_data["specs"] = specs
                    print(f"📋 Extracted {len(specs)} specifications")
                    
                    # Extract fork length and determine style
                    fork_text = specs.get("fork", "")
                    if fork_text:
                        fork_length = extract_fork_length(fork_text)
                        if fork_length:
                            product_data["fork_length"] = fork_length
                            style = determine_style_from_fork(fork_length)
                            if style:
                                product_data["style"] = style
                            print(f"🔧 Fork length: {fork_length}mm, Style: {style}")
                else:
                    print("⚠️ No specifications table found")
                
                # Extract description for rewriting
                # Product description is in elementor-widget-text-editor (data-widget_type="text-editor.default")
                # inside its child elementor-widget-container
                original_description = ""
                text_editors = product_soup.find_all("div", class_="elementor-widget-text-editor")
                for text_editor in text_editors:
                    container = text_editor.find("div", class_="elementor-widget-container")
                    if container:
                        text = container.get_text(strip=True)
                        # Product description is typically 100+ chars and contains bike terms
                        if text and len(text) > 80 and any(kw in text for kw in ("שלדה", "גלגל", "בולם", "הילוכים", "אופני זנב", "אופניים RL")):
                            original_description = text
                            break
                
                if original_description:
                    print(f"📝 Found description ({len(original_description)} chars)")
                    # Rewrite with ChatGPT
                    if CHATGPT_API_KEY:
                        print("🤖 Rewriting description with ChatGPT...")
                        rewritten_desc = rewrite_description_with_chatgpt(original_description, CHATGPT_API_KEY)
                        product_data["rewritten_description"] = rewritten_desc
                    else:
                        print("⚠️ No ChatGPT API key, using original description")
                        product_data["rewritten_description"] = original_description
                else:
                    print("⚠️ No description found")
                
            except Exception as e:
                print(f"⚠️ Error scraping product page: {e}")

            # Kids bike wheel size (only when category is kids)
            if category_text == "kids":
                wheel_size = extract_wheel_size_for_kids_bike(
                    product_data.get("model"),
                    product_data.get("specs"),
                )
                if wheel_size is not None:
                    product_data["wheel_size"] = wheel_size

            scraped_data.append(product_data)
            print(f"✅ Added product to scraped data")
            
            # Save after each product
            save_json(scraped_data, output_file)

    return scraped_data

def save_json(data, output_file):
    """Save data to JSON file"""
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved {len(data)} products to {output_file}")
    except Exception as e:
        print(f"⚠️ Failed to save JSON: {e}")

# ----------------------------
# MAIN EXECUTION
# ----------------------------
if __name__ == '__main__':
    try:
        # Setup output directory
        project_root = Path(__file__).resolve().parents[2]
        output_dir = project_root / "data" / "scraped_raw_data"
        os.makedirs(output_dir, exist_ok=True)
        output_file = output_dir / "rl_data.json"
        
        # Initialize empty JSON file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        print(f"📁 Output file ready: {output_file}")
        
    except Exception as e:
        print(f"❌ Error setting up output directory: {e}")
        exit(1)

    # Initialize Chrome driver
    scraped_data = []
    driver = None
    
    try:
        print("\n🚀 Starting Chrome driver...")
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        
        driver = uc.Chrome(options=options, version_main=144)
        print("✅ Chrome driver started successfully!")
        
        # Run the scraper
        scraped_data = rl_bikes(driver, output_file, scraped_data)
        
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        
    finally:
        # Cleanup
        if driver:
            try:
                driver.quit()
                print("🔒 Chrome driver closed")
            except:
                pass
        
        # Save final results
        if scraped_data:
            save_json(scraped_data, output_file)
            print(f"\n✅ Scraping completed: {len(scraped_data)} products extracted!")
        else:
            print("\n⚠️ No products were scraped")
