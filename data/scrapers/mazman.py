from cgi import print_exception
import time
import re
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc


HEBREW_TO_ENGLISH_KEYS = {
    "שנתון:": "year",
    "סוג אופניים:": "bike_type",
    "סדרות אופניים:": "bike_series",
    "שלדה:": "frame",
    "מזלג-בולם קדמי:": "fork",
    "בולם אחורי:": "rear_shock",
    "מוט כידון:": "stem",
    "כידון:": "handlebar",
    "מעצור קדמי:": "front_brake",
    "מעצור אחורי:": "rear_brake",
    "ידיות מעצורים:": "brake_levers",
    "מספר הילוכים:": "number_of_gears",
    "מעביר אחורי:": "rear_derailleur",
    "קסטה:": "cassette",
    "שרשרת:": "chain",
    "קראנק:": "crankset",
    "ציר מרכזי:": "bottom_bracket",
    "חישוקים:": "rims",
    "ציר קדמי:": "front_hub",
    "ציר אחורי:": "rear_hub",
    "צמיג קדמי:": "front_tire",
    "צמיג אחורי:": "rear_tire",
    "אוכף:": "saddle",
    "חבק מוט כיסא:": "seatpost_clamp",
    "מנוע חשמלי:": "motor",
    "סוללה:": "battery",
    "מטען:": "charger",
    "גודל גלגל:": "wheel_size",
    "ידיות הילוכים:": "shifters",
    "פנימיות:": "tubes",
    "מוט כיסא:": "seatpost",
    "תצוגת בקרה:": "display",
    "גלגל קדמי:": "front_wheel",
    "תוספות:": "additionals",
    "גלגל אחורי:": "rear_wheel"
}


# ----- Setup -----
BASE_URL = "https://www.matzman-merutz.co.il/"
TARGET_URL = BASE_URL + "electric-mountain-bikes"

scraped_data = []

def safe_to_int(text):
    price = text.replace(',', '').replace('₪', '').strip()
    match = re.search(r'\d+', price)
    if match:
        return int(match.group())
    else:
        return "צור קשר"

def matzman_bikes(driver):
    print(f"\n🌐 Scraping: {TARGET_URL}")
    try:
        driver.get(TARGET_URL)
        time.sleep(5)  # wait for page to load
    except Exception as e:
        print(f"❌ Error loading page: {e}")
        return []

    print("🔍 Searching for product cards...")
    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.find_all("div", class_="col-xs-12 col-sm-6 col-md-4 col-lg-4")
    print(f"✅ Found {len(cards)} products.\n")
    
    if len(cards) == 0:
        print("❌ No product cards found! Check if the CSS selector is correct.")
        print("🔍 Available div classes on page:")
        all_divs = soup.find_all("div", class_=True)
        classes = set()
        for div in all_divs[:20]:  # Show first 20 divs
            classes.update(div.get("class", []))
        print(f"Found classes: {list(classes)[:10]}")  # Show first 10 classes
        return []

    for idx, card in enumerate(cards, start=1):
        print(f"\n➡️ Scraping product {idx}/{len(cards)}...")
        
        # ---- Basic Info from product card ----
        firm_tag = card.find('div', 'firm')
        firm_text = firm_tag.get_text(strip=True).capitalize() if firm_tag and hasattr(firm_tag, 'get_text') else "N/A"

        model_tag = card.find("h2")
        model_text = model_tag.get_text(strip=True) if model_tag and hasattr(model_tag, 'get_text') else "N/A"
        # After model_text is assigned
        if model_text:
            # Remove unwanted Hebrew words
            model_text = re.sub(r"(אופני(?:ים)?|הרים|חשמליים)", "", model_text).strip()
            
            # Skip products that contain "שילדת" (frame only)
            if "שילדת" in model_text:
                print(f"⚠️ Skipping product {idx} - contains 'שילדת' (frame only): {model_text}")
                continue

        year_tag = card.find('div', 'newOnSite')
        year_text = year_tag.get_text(strip=True) if year_tag and hasattr(year_tag, 'get_text') else None
        # Convert year to integer if present, otherwise set to None
        year = None
        if year_text and year_text != "N/A":
            try:
                year = int(year_text)
            except (ValueError, TypeError):
                year = None

        # Extract text and clean it
        sale_price = card.find("span", "saleprice")
        old_price = card.find("span", "oldprice")

        # Handle different price scenarios
        original_price = None
        discounted_price = None

        # Check if there's a sale price (discounted scenario)
        if sale_price:
            original_price = safe_to_int(sale_price.get_text(strip=True))
            print(f"Found sale price: {original_price}")
            
            # If there's also an old price, use it as original
            if old_price:
                discounted_price = safe_to_int(old_price.get_text(strip=True))
                print(f"Found original price: {discounted_price}")
            else:
                # If no old price, use sale price as both original and discounted
                discounted_price = None
                print(f"No discounted price found, using discounted price as both: {None}")
        
        # If no sale price, check for regular price
        elif old_price and hasattr(old_price, 'get_text'):
            original_price = safe_to_int(old_price.get_text(strip=True))
            discounted_price = original_price  # Same price
            print(f"Found regular price (no discount): {original_price}")
        
        # If no prices found at all
        else:
            print(f"⚠️ No prices found for product {idx}, skipping...")
            continue

        img_tag = card.find("img", "img-responsive center-block vertical-center")
        img_src = img_tag.get("src") if img_tag else ""
        img_url = BASE_URL + img_src if img_src else "N/A"

        link_tag = card.find("a")
        if link_tag and link_tag.get("href"):
            href = link_tag.get("href")
            product_url = urljoin(BASE_URL, href)
        else:
            product_url = None

        products_data = {
            "firm": firm_text,
            "model": model_text,
            "year": year,
            "original_price": original_price,
            "disc_price": discounted_price,
            "image_URL": img_url,
            "product_URL": product_url
        }

        # ---- Scrape Specs from Product Page ----
        if product_url:
            try:
                driver.get(product_url)
                time.sleep(4)  # wait for product page to load
                product_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                #-----  Gallery images ---
                gallery_images_urls = []
                image_tags = product_soup.select('.sp-thumbnails img')

                image_urls = [urljoin(BASE_URL, img.get('src')) for img in image_tags if img.get('src')]
                products_data["gallery_images_urls"] = image_urls


                spec_list = product_soup.find("ul", class_="list-unstyled properties-product")
                time.sleep(4)  
                if spec_list:
                    items = spec_list.find_all("li")
                    for item in items:
                        key_tag = item.find("span", "titleKey")
                        val_tag = item.find("span", "valueKey")
                        if key_tag and val_tag:
                            key_he = key_tag.get_text(strip=True)
                            val = val_tag.get_text(strip=True)  
                            # Skip unwanted keys
                            if key_he in ['שנתון:', 'סוג אופניים:', 'סדרות אופניים:']:
                                continue 

                            key_en = HEBREW_TO_ENGLISH_KEYS.get(key_he, key_he)
                        
                            products_data[key_en] = val

                            print(f"✅ Specs scraped from product page.")
                            print("🔧 Product specs found:")
                            print(f"{key_en} | {val}")
            except Exception as e:
                print(f"⚠️ Error scraping product page: {e}")
        else:
            print("⚠️ No product URL found.")

        translated_row = products_data.copy()
        battery_value = translated_row.get("battery", "")
        wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)

        #extract Wh from battery value
        if wh_match:
            wh_value = int(wh_match.group(1))  # Convert to int if needed
            translated_row["wh"] = wh_value
        else:
        # If no 'Wh' found, try to find a 3-digit number
            fallback_match = re.search(r"\b(\d{3})\b", battery_value)
            if fallback_match:
                translated_row["wh"] = int(fallback_match.group(1))

        #---fork length----
        fork_text = translated_row.get("fork", "")
        print(f"DEBUG: fork_text = '{fork_text}'")
        match = re.search(r'(?<!\d)(120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?', fork_text.lower())
        if match:
            fork_length = match.group(1)
            translated_row["fork length"] = int(fork_length)
        else:
            print(f"⚠️ Could not extract fork length from: '{fork_text}'")
            translated_row["fork length"] = None

        #----sub-category----
        fork_length_str = translated_row.get("fork length")
        if fork_length_str:
            try:
                fork_length = int(fork_length_str)
                if fork_length == 120:
                    translated_row["sub-category"] = "cross-country"
                elif fork_length in [130, 140, 150]:
                    translated_row["sub-category"] = "trail"
                elif fork_length in [160, 170, 180]:
                    translated_row["sub-category"] = "enduro"
                else:
                    print(f"Unexpected fork length value: {fork_length}")
            except ValueError as e:
                print(f"Invalid fork length '{fork_length_str}': {e}")

        # Check if the entry has complete data before adding it
        if (translated_row.get("firm") and translated_row.get("firm") != "N/A" and
            translated_row.get("model") and translated_row.get("model") != "N/A" and
            translated_row.get("original_price") and translated_row.get("original_price") != "צור קשר" and
            translated_row.get("product_URL") and
            len(translated_row.get("gallery_images_urls", [])) > 0):
            
            scraped_data.append(translated_row)
            print(f"✅ Added product with complete data: {translated_row.get('firm')} {translated_row.get('model')}")
        else:
            print(f"⚠️ Skipping product {idx} - incomplete data:")
            print(f"   Firm: {translated_row.get('firm')}")
            print(f"   Model: {translated_row.get('model')}")
            print(f"   Price: {translated_row.get('original_price')}")
            print(f"   Product URL: {translated_row.get('product_URL')}")
            print(f"   Gallery images: {len(translated_row.get('gallery_images_urls', []))}")
            continue

    print(f"\n📊 Scraping completed. Total products scraped: {len(scraped_data)}")
    if len(scraped_data) == 0:
        print("❌ No products were scraped successfully!")
        print("🔍 Possible issues:")
        print("   - Website structure may have changed")
        print("   - CSS selectors may be outdated")
        print("   - Website may be blocking automated access")
        print("   - Network connectivity issues")
    return scraped_data                        

driver = uc.Chrome()
products = matzman_bikes(driver)
driver.quit()

# Save to JSON

output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scraped_raw_data')
# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "mazman.json")

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=4)

print(f"\n✅ All data saved to {output_file}")
