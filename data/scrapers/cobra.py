import time
import os
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc

HEBREW_TO_ENGLISH_KEYS = {
    "שלדה": "frame",
    "מהלך בולמים": "travel",
    "בולם קדמי": "fork",
    "בולם אחורי": "rear_shock",
    "מערכת שליטה": "control_system",
    "מערכת הנעה": "motor",
    "בטריה": "battery",
    "מסך תצוגה": "display",
    "מטען": "charger",
    "מעביר אחורי": "rear_derailleur",
    "ידיות הילוכים": "shifters",
    "קראנק": "crankset",
    "מוביל שרשרת": "chain_guide",
    "שרשרת": "chain",
    "שרשראות": "chainring",
    "קסטה": "cassette",
    "ברקסים": "brakes",
    "דיסקים": "rotors",
    "כידון": "handlebar",
    "מוט אוכף": "seatpost",
    "אוכף": "saddle",
    "סטם": "stem",
    "צמיג קדמי": "front_tire",
    "צמיג אחורי": "rear_tire",
    "תאורה": "lighting",
    "נאבה קדמית": "front_hub",
    "נאבה אחורית": "rear_hub",
    "גלגלים": "wheels",
    "מיסבי היגוי": "headset",
    "מייסבי היגוי": "headset",
    "תוספות": "accessories",
    "אביזרים": "accessories",
    "חישוקים": "rims",
    "חשוקים": "rims",
    "שפיצים": "spokes",
    "משקל משוער": "weight",
    "מק\"ט": "catalog_number"
}


BASE_URL = "https://www.cobra-bordo.co.il"
TARGET_URL = f"{BASE_URL}/158456-אופני-הרים-חשמליים"

scraped_data = []

def extract_price(price_str):
    """Extracts the first number from a string and converts it to int, or returns 'Not listed'."""
    match = re.search(r'\d+', price_str.replace(",", ""))
    if match:
        return int(match.group())
    else:
        return "צור קשר"

def scrape_cobra_bikes(driver):
    print(f"\n🌐 Scraping: {TARGET_URL}")
    driver.get(TARGET_URL)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.find_all("div", class_="layout_list_item")
    cards = cards[5:]  # Skip the first 5 cards
    print(f"✅ Found {len(cards)} products.\n")


    for i, card in enumerate(cards):
        print(f"--- Processing Product {i+1} ---")

        firm_text = "Scott" # Cleaned up leading space
        model_text = None
        year_text = None # You might want to extract this dynamically if available
        price_text = None
        img_url = None
        product_url = None
        specifications = {} 

        model_tag = card.find('h3', class_="title")
        if not model_tag:
            print("Warning: No model title found, skipping this product")
            continue
        model_text = model_tag.get_text(strip=True)
        print(model_text)
        hebrew_prefix_pattern = r"(אופני|סקוט|חשמליים|חשמליים-|סקוט-|אופני סקוט|אופני סקוט חשמליים|–|-)"

        # Step 1: Extract year if exists (2023–2026)
        year_match = re.search(r'\b(2023|2024|2025|2026)\b', model_text)
        year_text = int(year_match.group(1)) if year_match else None
        #print(year_text)

        # Clean the model name
        # Remove Hebrew junk and year, keep the rest
        cleaned_model = re.sub(hebrew_prefix_pattern, "", model_text).strip()
        cleaned_model = re.sub(r'\b(2023|2024|2025|2026)\b', '', cleaned_model).strip()

        # Optional: collapse double spaces if there are any
        cleaned_model = re.sub(r'\s+', ' ', cleaned_model)

        # Now assign the clean values
        model_text = cleaned_model
        model_text = model_text.replace("SCOTT", "").strip()

        print(model_text)

        # Extract prices - handle both discount and non-discount scenarios
        original_price = None
        discounted_price = None
        
        # First check if there's an origin_price div (discount scenario)
        origin_price_tag = card.find('p', class_="origin_price")
        if origin_price_tag:
            # Remove hidden spans
            for span in origin_price_tag.find_all("span", style=lambda value: value and "display: none" in value):
                span.decompose()
            # Clean and extract number
            origin_price_text = origin_price_tag.get_text(strip=True).replace("₪", "").replace(" ", "")
            original_price = extract_price(origin_price_text)
            print(f"Original price (discount scenario): {original_price}")
            
            # Get the discounted price from the price div
            price_tag = card.find('span', class_='price')
            if price_tag:
                # Remove hidden spans
                for span in price_tag.find_all("span", style=lambda value: value and "display: none" in value):
                    span.decompose()
                # Clean and extract number
                price_text = price_tag.get_text(strip=True).replace("₪", "").replace(" ", "")
                discounted_price = extract_price(price_text)
                print(f"Discounted price: {discounted_price}")
            else:
                print("Warning: Found origin_price but no discounted price")
                discounted_price = original_price
        else:
            # No discount scenario - price is in the price div
            price_tag = card.find('span', class_='price')
            if price_tag:
                # Remove hidden spans
                for span in price_tag.find_all("span", style=lambda value: value and "display: none" in value):
                    span.decompose()
                # Clean and extract number
                price_text = price_tag.get_text(strip=True).replace("₪", "").replace(" ", "")
                original_price = extract_price(price_text)
                
                # Handle "צור קשר" case - set discounted_price to None
                if original_price == "צור קשר":
                    discounted_price = None
                    print(f"Price (no discount, contact us): {original_price}, discounted_price: None")
                else:
                    discounted_price = original_price  # Same price when no discount
                    print(f"Price (no discount): {original_price}")
            else:
                print("Warning: No price found")
                continue

        

        image_tag = card.find('img', class_="img-responsive")
        if image_tag:
            img_url = image_tag.get('src')
            #print(img_url)
        else:
            print("  Warning: Image tag not found.")


        product_link_tag = card.select_one("a")
        if product_link_tag:
            raw_href = product_link_tag.get('href', '')
            clean_href = raw_href.strip()  # removes spaces, tabs, and newlines
            product_url = urljoin(BASE_URL, clean_href)
            #print(f"Product URL: {product_url}")
        else:
            product_url = None
            print("didnt found product URL")

        product_data = {
            "firm": firm_text,
            "model": model_text,
            "year": year_text,
            "original_price": original_price,
            "disc_price": discounted_price,
            "image_url": img_url,
            "product_url": product_url
        }

        # Visit product page and extract specs
        if product_url:
            try:
                driver.get(product_url)
                time.sleep(4)
                prod_soup = BeautifulSoup(driver.page_source, "html.parser")

                #images Gallery
                ul = prod_soup.find('ul', class_='lSPager lSGallery')
                #print(ul)
                # Extract all image srcs from <li> elements inside this <ul>
                gallery_images_urls = [img['src'] for img in ul.find_all('img') if img.get('src')]
                product_data["gallery_images_urls"] = gallery_images_urls


                spec_rows = prod_soup.find("div", class_="specifications row")
                if spec_rows:
                    all_lis = spec_rows.find_all("li")
                    for li in all_lis:
                        key_tag = li.find("b")
                        val_tag = li.find("span")
                        if key_tag and val_tag:
                            key = key_tag.get_text(strip=True)
                            #print(key)
                            val = val_tag.get_text(strip=True)
                            #print(val)
                            
                            # Skip SKU entry but continue scraping the rest
                            if key == 'מק"ט':
                                continue

                            product_data[key] = val
                else:
                    print("⚠️ No specifications section found.")


            except Exception as e:
                print(f"⚠️ Error scraping product page ({product_url}): {e}")

        translated_row = {}
        for key, value in product_data.items():
            translated_key = HEBREW_TO_ENGLISH_KEYS.get(key, key)  # default to original key if no translation
            translated_row[translated_key] = value

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
            raise ValueError(f"❌ Could not extract fork length from: '{fork_text}'")


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
                    raise ValueError(f"Unexpected fork length value: {fork_length}")
            except ValueError as e:
                raise ValueError(f"Invalid fork length '{fork_length_str}': {e}")

        scraped_data.append(translated_row)

    return scraped_data

# --- Run the Scraper ---

driver = uc.Chrome()
products = scrape_cobra_bikes(driver)
driver.quit()



# Save to JSON
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scraped_raw_data')
output_file = os.path.join(output_dir, "cobra.json")

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=4)

print(f"\n✅ All data saved to {output_file}")

